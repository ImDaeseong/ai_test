from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class ProcessInfo:
    pid: int | None
    name: str | None = None
    exe: str | None = None
    username: str | None = None
    create_time: float | None = None
    service_names: tuple[str, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["service_names"] = list(self.service_names)
        return data


@dataclass(frozen=True)
class PortRecord:
    protocol: str
    local_ip: str | None
    local_port: int | None
    remote_ip: str | None
    remote_port: int | None
    state: str
    pid: int | None
    process_name: str | None
    process_exe: str | None
    username: str | None
    process_create_time: float | None
    service_names: tuple[str, ...]
    collection_time: str
    update_time: str

    def identity_key(self) -> tuple[Any, ...]:
        return (
            self.protocol,
            self.local_ip,
            self.local_port,
            self.remote_ip,
            self.remote_port,
            self.state,
            self.pid,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["service_names"] = list(self.service_names)
        return data


@dataclass(frozen=True)
class CollectorStats:
    collection_time: str
    total_records: int
    tcp_records: int
    udp_records: int
    access_denied: int = 0
    no_such_process: int = 0
    zombie_process: int = 0
    other_errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ServiceStatus:
    state: str
    started_at: str | None = None
    stopped_at: str | None = None
    last_collection_time: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
