from __future__ import annotations

import json

from config_loader import StorageConfig
from models import CollectorStats, PortRecord
from storage.json_exporter import JsonExporter
from storage.sqlite_store import SQLiteStore


def _record() -> PortRecord:
    return PortRecord(
        protocol="TCP",
        local_ip="127.0.0.1",
        local_port=8080,
        remote_ip="127.0.0.1",
        remote_port=50000,
        state="ESTABLISHED",
        pid=123,
        process_name="python.exe",
        process_exe="C:/Python/python.exe",
        username="User",
        process_create_time=1.0,
        service_names=("ExampleService",),
        collection_time="2026-05-19T00:00:00.000+00:00",
        update_time="2026-05-19T00:00:00.000+00:00",
    )


def _stats() -> CollectorStats:
    return CollectorStats(
        collection_time="2026-05-19T00:00:00.000+00:00",
        total_records=1,
        tcp_records=1,
        udp_records=0,
    )


def test_sqlite_store_writes_records(tmp_path):
    config = StorageConfig(database_path=tmp_path / "monitor.sqlite3", json_export_path=tmp_path / "records.jsonl")
    store = SQLiteStore(config)
    store.open()
    try:
        store.write_records([_record()], _stats())
        conn = store._require_connection()
        record_count = conn.execute("SELECT COUNT(*) FROM port_records").fetchone()[0]
        stats_count = conn.execute("SELECT COUNT(*) FROM collector_stats").fetchone()[0]
    finally:
        store.close()

    assert record_count == 1
    assert stats_count == 1


def test_json_exporter_writes_jsonl(tmp_path):
    config = StorageConfig(database_path=tmp_path / "monitor.sqlite3", json_export_path=tmp_path / "records.jsonl")
    exporter = JsonExporter(config)
    exporter.write_records([_record()], _stats())

    lines = config.json_export_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["type"] == "port_record"
    assert first["local_port"] == 8080
