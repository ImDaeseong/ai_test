from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CollectorConfig:
    polling_interval_seconds: float = 5.0
    include_tcp: bool = True
    include_udp: bool = True
    include_ipv6: bool = True
    process_cache_ttl_seconds: float = 30.0


@dataclass(frozen=True)
class StorageConfig:
    sqlite_enabled: bool = True
    json_export_enabled: bool = True
    database_path: Path = Path("data/port_monitor.sqlite3")
    json_export_path: Path = Path("data/port_records.jsonl")
    sqlite_busy_timeout_ms: int = 5000
    retention_days: int = 30
    batch_size: int = 500


@dataclass(frozen=True)
class LoggingConfig:
    log_dir: Path = Path("logs")
    log_file: str = "port_monitor.log"
    level: str = "INFO"
    max_bytes: int = 5_242_880
    backup_count: int = 5


@dataclass(frozen=True)
class ServiceConfig:
    name: str = "WindowsPortMonitor"
    display_name: str = "Windows TCP/UDP Port Monitor"
    description: str = "Collects TCP/UDP port, connection, and process metadata."


@dataclass(frozen=True)
class AppConfig:
    collector: CollectorConfig
    storage: StorageConfig
    logging: LoggingConfig
    service: ServiceConfig
    root_dir: Path


def _resolve_path(root_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root_dir / path


def load_config(config_path: str | Path | None = None) -> AppConfig:
    root_dir = Path(__file__).resolve().parent
    path = Path(config_path) if config_path else root_dir / "config" / "config.yaml"
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {path}") from None

    collector_raw = raw.get("collector", {})
    storage_raw = raw.get("storage", {})
    logging_raw = raw.get("logging", {})
    service_raw = raw.get("service", {})

    collector = CollectorConfig(
        polling_interval_seconds=max(1.0, float(collector_raw.get("polling_interval_seconds", 5.0))),
        include_tcp=bool(collector_raw.get("include_tcp", True)),
        include_udp=bool(collector_raw.get("include_udp", True)),
        include_ipv6=bool(collector_raw.get("include_ipv6", True)),
        process_cache_ttl_seconds=max(1.0, float(collector_raw.get("process_cache_ttl_seconds", 30.0))),
    )
    storage = StorageConfig(
        sqlite_enabled=bool(storage_raw.get("sqlite_enabled", True)),
        json_export_enabled=bool(storage_raw.get("json_export_enabled", True)),
        database_path=_resolve_path(root_dir, storage_raw.get("database_path", "data/port_monitor.sqlite3")),
        json_export_path=_resolve_path(root_dir, storage_raw.get("json_export_path", "data/port_records.jsonl")),
        sqlite_busy_timeout_ms=int(storage_raw.get("sqlite_busy_timeout_ms", 5000)),
        retention_days=max(1, int(storage_raw.get("retention_days", 30))),
        batch_size=max(1, int(storage_raw.get("batch_size", 500))),
    )
    logging_config = LoggingConfig(
        log_dir=_resolve_path(root_dir, logging_raw.get("log_dir", "logs")),
        log_file=str(logging_raw.get("log_file", "port_monitor.log")),
        level=str(logging_raw.get("level", "INFO")).upper(),
        max_bytes=max(1024, int(logging_raw.get("max_bytes", 5_242_880))),
        backup_count=max(1, int(logging_raw.get("backup_count", 5))),
    )
    service = ServiceConfig(
        name=str(service_raw.get("name", "WindowsPortMonitor")),
        display_name=str(service_raw.get("display_name", "Windows TCP/UDP Port Monitor")),
        description=str(service_raw.get("description", "Collects TCP/UDP port, connection, and process metadata.")),
    )
    return AppConfig(
        collector=collector,
        storage=storage,
        logging=logging_config,
        service=service,
        root_dir=root_dir,
    )
