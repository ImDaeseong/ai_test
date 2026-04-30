import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class Subscriber:
    platform: str
    target_id: str
    display_name: str


@dataclass
class DeliveryJob:
    id: int
    platform: str
    target_id: str
    message_type: str
    message_text: str
    attempts: int


class NotificationStore:
    def __init__(self, db_path: str = "weather_alarm.db"):
        self.db_path = db_path
        parent = Path(db_path).parent
        if str(parent) and str(parent) != ".":
            parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    platform TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (platform, target_id)
                );

                CREATE TABLE IF NOT EXISTS delivery_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at REAL NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    idempotency_key TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_delivery_queue_idempotency
                    ON delivery_queue(idempotency_key);
                CREATE INDEX IF NOT EXISTS idx_delivery_queue_due
                    ON delivery_queue(status, next_attempt_at, id);
                CREATE INDEX IF NOT EXISTS idx_subscribers_active
                    ON subscribers(platform, active);
                """
            )

    def add_subscriber(self, platform: str, target_id: str, display_name: str = "") -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO subscribers (platform, target_id, display_name, active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(platform, target_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (platform, str(target_id), display_name, now, now),
            )

    def remove_subscriber(self, platform: str, target_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE subscribers
                SET active = 0, updated_at = ?
                WHERE platform = ? AND target_id = ?
                """,
                (time.time(), platform, str(target_id)),
            )

    def list_subscribers(self, platform: Optional[str] = None) -> List[Subscriber]:
        query = """
            SELECT platform, target_id, display_name
            FROM subscribers
            WHERE active = 1
        """
        params = []
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        query += " ORDER BY platform, target_id"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            Subscriber(row["platform"], row["target_id"], row["display_name"])
            for row in rows
        ]

    def enqueue_broadcast(
        self,
        message_text: str,
        message_type: str,
        dedupe_key: str,
        platforms: Optional[Iterable[str]] = None,
    ) -> int:
        platform_set = set(platforms) if platforms else None
        subscribers = [
            sub for sub in self.list_subscribers()
            if platform_set is None or sub.platform in platform_set
        ]
        return self.enqueue_targets(subscribers, message_text, message_type, dedupe_key)

    def enqueue_targets(
        self,
        targets: Iterable[Subscriber],
        message_text: str,
        message_type: str,
        dedupe_key: str,
    ) -> int:
        now = time.time()
        rows = []
        for target in targets:
            idempotency_key = (
                f"{message_type}:{dedupe_key}:{target.platform}:{target.target_id}"
            )
            rows.append(
                (
                    target.platform,
                    target.target_id,
                    message_type,
                    message_text,
                    idempotency_key,
                    now,
                    now,
                )
            )
        if not rows:
            return 0
        with self._connect() as conn:
            before = conn.total_changes
            conn.executemany(
                """
                INSERT OR IGNORE INTO delivery_queue (
                    platform, target_id, message_type, message_text,
                    idempotency_key, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return conn.total_changes - before

    def claim_due_jobs(self, limit: int = 100) -> List[DeliveryJob]:
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """
                SELECT id, platform, target_id, message_type, message_text, attempts
                FROM delivery_queue
                WHERE status = 'pending' AND next_attempt_at <= ?
                ORDER BY id
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"""
                    UPDATE delivery_queue
                    SET status = 'sending', attempts = attempts + 1, updated_at = ?
                    WHERE id IN ({placeholders})
                    """,
                    [now] + ids,
                )
            conn.commit()
        return [
            DeliveryJob(
                id=row["id"],
                platform=row["platform"],
                target_id=row["target_id"],
                message_type=row["message_type"],
                message_text=row["message_text"],
                attempts=row["attempts"] + 1,
            )
            for row in rows
        ]

    def mark_sent(self, job_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE delivery_queue
                SET status = 'sent', last_error = '', updated_at = ?
                WHERE id = ?
                """,
                (time.time(), job_id),
            )

    def mark_retry(
        self,
        job_id: int,
        error: str,
        delay_seconds: float,
        attempts: int,
        max_attempts: int,
    ) -> None:
        now = time.time()
        status = "failed" if attempts >= max_attempts else "pending"
        next_attempt_at = now + max(0.0, delay_seconds)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE delivery_queue
                SET status = ?, next_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, next_attempt_at, error[:1000], now, job_id),
            )

    def pending_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM delivery_queue
                WHERE status = 'pending'
                """
            ).fetchone()
        return int(row["count"])

    def status_counts(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM delivery_queue
                GROUP BY status
                """
            ).fetchall()
        return {row["status"]: int(row["count"]) for row in rows}
