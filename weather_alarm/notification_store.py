import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional

try:
    import psycopg2  # type: ignore[import]
    import psycopg2.extras  # type: ignore[import]
except ImportError:
    psycopg2 = None  # type: ignore[assignment]


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
    """SQLite(로컬) / PostgreSQL(Docker) 자동 전환 스토어.

    dsn이 postgresql:// 또는 postgres:// 로 시작하면 PostgreSQL,
    그 외(파일 경로 or 빈 문자열)이면 SQLite를 사용합니다.
    """

    def __init__(self, dsn: str = ""):
        self._is_pg = bool(dsn) and (
            dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        )
        if self._is_pg:
            self._dsn = dsn
        else:
            self._path = dsn if dsn else os.getenv("BROADCAST_DB_PATH", "weather_alarm.db")
            _parent = os.path.dirname(self._path)
            if _parent and _parent != ".":
                os.makedirs(_parent, exist_ok=True)
        self.initialize()

    # ──────────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────────

    @contextmanager
    def _connect(self):
        if self._is_pg:
            conn = psycopg2.connect(self._dsn)
            conn.cursor_factory = psycopg2.extras.DictCursor
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self._path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _q(self, sql: str) -> str:
        """PostgreSQL %s 플레이스홀더를 SQLite ? 로 변환."""
        return sql if self._is_pg else sql.replace("%s", "?")

    def _fetchall(self, conn, sql: str, params=()):
        if self._is_pg:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        else:
            return conn.execute(sql, params).fetchall()

    def _fetchone(self, conn, sql: str, params=()):
        if self._is_pg:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        else:
            return conn.execute(sql, params).fetchone()

    def _execute(self, conn, sql: str, params=()):
        if self._is_pg:
            with conn.cursor() as cur:
                cur.execute(sql, params)
        else:
            conn.execute(sql, params)

    # ──────────────────────────────────────────────
    # 초기화
    # ──────────────────────────────────────────────

    def initialize(self) -> None:
        if self._is_pg:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS subscribers (
                            platform     TEXT             NOT NULL,
                            target_id    TEXT             NOT NULL,
                            display_name TEXT             NOT NULL DEFAULT '',
                            active       BOOLEAN          NOT NULL DEFAULT TRUE,
                            created_at   DOUBLE PRECISION NOT NULL,
                            updated_at   DOUBLE PRECISION NOT NULL,
                            PRIMARY KEY (platform, target_id)
                        );
                        CREATE TABLE IF NOT EXISTS delivery_queue (
                            id              BIGSERIAL        PRIMARY KEY,
                            platform        TEXT             NOT NULL,
                            target_id       TEXT             NOT NULL,
                            message_type    TEXT             NOT NULL,
                            message_text    TEXT             NOT NULL,
                            status          TEXT             NOT NULL DEFAULT 'pending',
                            attempts        INT              NOT NULL DEFAULT 0,
                            next_attempt_at DOUBLE PRECISION NOT NULL DEFAULT 0,
                            last_error      TEXT             NOT NULL DEFAULT '',
                            idempotency_key TEXT             NOT NULL,
                            created_at      DOUBLE PRECISION NOT NULL,
                            updated_at      DOUBLE PRECISION NOT NULL,
                            CONSTRAINT uq_delivery_idempotency UNIQUE (idempotency_key)
                        );
                        CREATE INDEX IF NOT EXISTS idx_delivery_queue_due
                            ON delivery_queue(status, next_attempt_at, id);
                        CREATE INDEX IF NOT EXISTS idx_subscribers_active
                            ON subscribers(platform, active);
                    """)
        else:
            with self._connect() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS subscribers (
                        platform     TEXT NOT NULL,
                        target_id    TEXT NOT NULL,
                        display_name TEXT NOT NULL DEFAULT '',
                        active       INTEGER NOT NULL DEFAULT 1,
                        created_at   REAL NOT NULL,
                        updated_at   REAL NOT NULL,
                        PRIMARY KEY (platform, target_id)
                    );
                    CREATE TABLE IF NOT EXISTS delivery_queue (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform        TEXT    NOT NULL,
                        target_id       TEXT    NOT NULL,
                        message_type    TEXT    NOT NULL,
                        message_text    TEXT    NOT NULL,
                        status          TEXT    NOT NULL DEFAULT 'pending',
                        attempts        INTEGER NOT NULL DEFAULT 0,
                        next_attempt_at REAL    NOT NULL DEFAULT 0,
                        last_error      TEXT    NOT NULL DEFAULT '',
                        idempotency_key TEXT    NOT NULL,
                        created_at      REAL    NOT NULL,
                        updated_at      REAL    NOT NULL
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_delivery_idempotency
                        ON delivery_queue(idempotency_key);
                    CREATE INDEX IF NOT EXISTS idx_delivery_queue_due
                        ON delivery_queue(status, next_attempt_at, id);
                    CREATE INDEX IF NOT EXISTS idx_subscribers_active
                        ON subscribers(platform, active);
                """)

    # ──────────────────────────────────────────────
    # 구독자 관리
    # ──────────────────────────────────────────────

    def add_subscriber(self, platform: str, target_id: str, display_name: str = "") -> None:
        now = time.time()
        active_val = "TRUE" if self._is_pg else "1"
        sql = self._q(f"""
            INSERT INTO subscribers (platform, target_id, display_name, active, created_at, updated_at)
            VALUES (%s, %s, %s, {active_val}, %s, %s)
            ON CONFLICT(platform, target_id) DO UPDATE SET
                display_name = excluded.display_name,
                active = {active_val},
                updated_at = excluded.updated_at
        """)
        with self._connect() as conn:
            self._execute(conn, sql, (platform, str(target_id), display_name, now, now))

    def remove_subscriber(self, platform: str, target_id: str) -> None:
        sql = self._q("""
            UPDATE subscribers
            SET active = 0, updated_at = %s
            WHERE platform = %s AND target_id = %s
        """)
        with self._connect() as conn:
            self._execute(conn, sql, (time.time(), platform, str(target_id)))

    def list_subscribers(self, platform: Optional[str] = None) -> List[Subscriber]:
        sql = "SELECT platform, target_id, display_name FROM subscribers WHERE active = 1"
        params: list = []
        if platform:
            sql += self._q(" AND platform = %s")
            params.append(platform)
        sql += " ORDER BY platform, target_id"
        with self._connect() as conn:
            rows = self._fetchall(conn, sql, params)
        return [Subscriber(row["platform"], row["target_id"], row["display_name"]) for row in rows]

    # ──────────────────────────────────────────────
    # 발송 큐 관리
    # ──────────────────────────────────────────────

    def enqueue_broadcast(
        self,
        message_text: str,
        message_type: str,
        dedupe_key: str,
        platforms: Optional[Iterable[str]] = None,
    ) -> int:
        platform_set = set(platforms) if platforms else None
        subscribers = [
            s for s in self.list_subscribers()
            if platform_set is None or s.platform in platform_set
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
        for t in targets:
            idempotency_key = f"{message_type}:{dedupe_key}:{t.platform}:{t.target_id}"
            rows.append((t.platform, t.target_id, message_type, message_text, idempotency_key, now, now))
        if not rows:
            return 0
        sql = self._q("""
            INSERT INTO delivery_queue
                (platform, target_id, message_type, message_text, idempotency_key, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(idempotency_key) DO NOTHING
        """)
        with self._connect() as conn:
            if self._is_pg:
                inserted = 0
                with conn.cursor() as cur:
                    for row in rows:
                        cur.execute(sql, row)
                        inserted += cur.rowcount
                return inserted
            else:
                before = conn.total_changes
                conn.executemany(sql, rows)
                return conn.total_changes - before

    def enqueue_single(
        self,
        subscriber: Subscriber,
        message_text: str,
        message_type: str,
        idempotency_key: str,
    ) -> Optional[int]:
        """신규 job 삽입. 새 job_id 반환, 중복이면 None."""
        now = time.time()
        sql = self._q("""
            INSERT INTO delivery_queue
                (platform, target_id, message_type, message_text, idempotency_key, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(idempotency_key) DO NOTHING
            RETURNING id
        """)
        params = (subscriber.platform, subscriber.target_id, message_type, message_text, idempotency_key, now, now)
        with self._connect() as conn:
            row = self._fetchone(conn, sql, params)
        return row["id"] if row else None

    def claim_due_jobs(self, limit: int = 100) -> List[DeliveryJob]:
        now = time.time()
        if self._is_pg:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, platform, target_id, message_type, message_text, attempts
                        FROM delivery_queue
                        WHERE status = 'pending' AND next_attempt_at <= %s
                        ORDER BY id LIMIT %s
                        FOR UPDATE SKIP LOCKED
                    """, (now, limit))
                    rows = cur.fetchall()
                    ids = [r["id"] for r in rows]
                    if ids:
                        cur.execute("""
                            UPDATE delivery_queue
                            SET status = 'sending', attempts = attempts + 1, updated_at = %s
                            WHERE id = ANY(%s)
                        """, (now, ids))
        else:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute("""
                    SELECT id, platform, target_id, message_type, message_text, attempts
                    FROM delivery_queue
                    WHERE status = 'pending' AND next_attempt_at <= ?
                    ORDER BY id LIMIT ?
                """, (now, limit)).fetchall()
                ids = [r["id"] for r in rows]
                if ids:
                    placeholders = ",".join("?" for _ in ids)
                    conn.execute(
                        f"UPDATE delivery_queue SET status='sending', attempts=attempts+1, updated_at=? WHERE id IN ({placeholders})",
                        [now] + ids,
                    )
        return [
            DeliveryJob(
                id=r["id"],
                platform=r["platform"],
                target_id=r["target_id"],
                message_type=r["message_type"],
                message_text=r["message_text"],
                attempts=r["attempts"] + 1,
            )
            for r in rows
        ]

    def mark_sent(self, job_id: int) -> None:
        sql = self._q("UPDATE delivery_queue SET status='sent', last_error='', updated_at=%s WHERE id=%s")
        with self._connect() as conn:
            self._execute(conn, sql, (time.time(), job_id))

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
        sql = self._q("""
            UPDATE delivery_queue
            SET status=%s, next_attempt_at=%s, last_error=%s, updated_at=%s
            WHERE id=%s
        """)
        with self._connect() as conn:
            self._execute(conn, sql, (status, next_attempt_at, error[:1000], now, job_id))

    def pending_count(self) -> int:
        sql = "SELECT COUNT(*) FROM delivery_queue WHERE status='pending'"
        with self._connect() as conn:
            row = self._fetchone(conn, sql)
        return int(row[0]) if row else 0

    def status_counts(self) -> dict:
        sql = "SELECT status, COUNT(*) FROM delivery_queue GROUP BY status"
        with self._connect() as conn:
            rows = self._fetchall(conn, sql)
        return {r[0]: int(r[1]) for r in rows}
