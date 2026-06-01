from __future__ import annotations

import time

from config_loader import AppConfig, CollectorConfig, LoggingConfig, ServiceConfig, StorageConfig
from models import CollectorStats
from service.background_runner import BackgroundRunner


class FakeCollector:
    def __init__(self) -> None:
        self.calls = 0

    def collect(self):
        self.calls += 1
        return [], CollectorStats(
            collection_time="2026-05-19T00:00:00.000+00:00",
            total_records=0,
            tcp_records=0,
            udp_records=0,
        )


class FakeStore:
    def __init__(self) -> None:
        self.writes = 0
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True

    def close(self):
        self.closed = True

    def write_records(self, records, stats=None):
        self.writes += 1

    def purge_older_than(self, cutoff_iso):
        self.last_cutoff = cutoff_iso


def _config(tmp_path):
    return AppConfig(
        collector=CollectorConfig(polling_interval_seconds=1.0),
        storage=StorageConfig(database_path=tmp_path / "db.sqlite3", json_export_path=tmp_path / "records.jsonl"),
        logging=LoggingConfig(log_dir=tmp_path / "logs"),
        service=ServiceConfig(),
        root_dir=tmp_path,
    )


def test_background_runner_graceful_shutdown(tmp_path):
    collector = FakeCollector()
    sqlite_store = FakeStore()
    json_exporter = FakeStore()
    runner = BackgroundRunner(_config(tmp_path), collector=collector, sqlite_store=sqlite_store, json_exporter=json_exporter)

    runner.start(blocking=False)
    time.sleep(0.2)
    runner.stop()

    assert runner.wait(timeout=3)
    assert collector.calls >= 1
    assert sqlite_store.opened
    assert sqlite_store.closed
