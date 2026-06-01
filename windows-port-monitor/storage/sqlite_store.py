from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Iterable

from config_loader import StorageConfig
from models import CollectorStats, PortRecord

logger = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS port_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    local_ip TEXT,
    local_port INTEGER,
    remote_ip TEXT,
    remote_port INTEGER,
    state TEXT NOT NULL,
    pid INTEGER,
    process_name TEXT,
    process_exe TEXT,
    username TEXT,
    process_create_time REAL,
    service_names TEXT NOT NULL DEFAULT '[]',
    collection_time TEXT NOT NULL,
    update_time TEXT NOT NULL,
    identity_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_port_records_collection_time ON port_records(collection_time);
CREATE INDEX IF NOT EXISTS idx_port_records_protocol_port ON port_records(protocol, local_port);
CREATE INDEX IF NOT EXISTS idx_port_records_pid ON port_records(pid);
CREATE INDEX IF NOT EXISTS idx_port_records_identity ON port_records(identity_hash);

CREATE TABLE IF NOT EXISTS collector_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_time TEXT NOT NULL,
    total_records INTEGER NOT NULL,
    tcp_records INTEGER NOT NULL,
    udp_records INTEGER NOT NULL,
    access_denied INTEGER NOT NULL,
    no_such_process INTEGER NOT NULL,
    zombie_process INTEGER NOT NULL,
    other_errors INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_collector_stats_collection_time ON collector_stats(collection_time);
"""


class SQLiteStore:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self.path: Path = config.database_path
        self._lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None

    def open(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                self.path,
                timeout=max(1.0, self.config.sqlite_busy_timeout_ms / 1000),
                check_same_thread=False,
            )
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute(f"PRAGMA busy_timeout={self.config.sqlite_busy_timeout_ms}")
            self._connection.executescript(SCHEMA_SQL)
            self._connection.commit()
            logger.info("sqlite_store_opened", extra={"database_path": str(self.path)})

    def close(self) -> None:
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
                logger.info("sqlite_store_closed")

    def write_records(self, records: Iterable[PortRecord], stats: CollectorStats | None = None) -> None:
        batch = list(records)
        if not batch and stats is None:
            return
        with self._lock:
            conn = self._require_connection()
            try:
                if batch:
                    conn.executemany(
                        """
                        INSERT INTO port_records (
                            protocol, local_ip, local_port, remote_ip, remote_port, state,
                            pid, process_name, process_exe, username, process_create_time,
                            service_names, collection_time, update_time, identity_hash
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [self._record_row(record) for record in batch],
                    )
                if stats:
                    conn.execute(
                        """
                        INSERT INTO collector_stats (
                            collection_time, total_records, tcp_records, udp_records,
                            access_denied, no_such_process, zombie_process, other_errors
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            stats.collection_time,
                            stats.total_records,
                            stats.tcp_records,
                            stats.udp_records,
                            stats.access_denied,
                            stats.no_such_process,
                            stats.zombie_process,
                            stats.other_errors,
                        ),
                    )
                conn.commit()
                logger.debug("sqlite_write_complete", extra={"records": len(batch)})
            except sqlite3.OperationalError:
                conn.rollback()
                logger.exception("sqlite_operational_error", extra={"records": len(batch)})
            except Exception:
                conn.rollback()
                logger.exception("sqlite_write_failed", extra={"records": len(batch)})

    def purge_older_than(self, cutoff_iso: str) -> None:
        with self._lock:
            conn = self._require_connection()
            try:
                conn.execute("DELETE FROM port_records WHERE collection_time < ?", (cutoff_iso,))
                conn.execute("DELETE FROM collector_stats WHERE collection_time < ?", (cutoff_iso,))
                conn.commit()
                logger.info("sqlite_retention_purged", extra={"cutoff": cutoff_iso})
            except Exception:
                conn.rollback()
                logger.exception("sqlite_retention_failed", extra={"cutoff": cutoff_iso})

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self.open()
        assert self._connection is not None
        return self._connection

    @staticmethod
    def _record_row(record: PortRecord) -> tuple:
        return (
            record.protocol,
            record.local_ip,
            record.local_port,
            record.remote_ip,
            record.remote_port,
            record.state,
            record.pid,
            record.process_name,
            record.process_exe,
            record.username,
            record.process_create_time,
            json.dumps(list(record.service_names), ensure_ascii=False),
            record.collection_time,
            record.update_time,
            SQLiteStore._identity_hash(record),
        )

    @staticmethod
    def _identity_hash(record: PortRecord) -> str:
        return "|".join("" if item is None else str(item) for item in record.identity_key())
