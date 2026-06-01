from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

import psutil

from collector.process_resolver import ProcessResolver
from config_loader import CollectorConfig
from models import CollectorStats, PortRecord, utc_now_iso

logger = logging.getLogger(__name__)


@dataclass
class _MutableStats:
    access_denied: int = 0
    no_such_process: int = 0
    zombie_process: int = 0
    other_errors: int = 0


class PortCollector:
    def __init__(
        self,
        config: CollectorConfig,
        resolver: ProcessResolver | None = None,
    ) -> None:
        self.config = config
        self.resolver = resolver or ProcessResolver(config.process_cache_ttl_seconds)

    def collect(self) -> tuple[list[PortRecord], CollectorStats]:
        collection_time = utc_now_iso()
        records: list[PortRecord] = []
        mutable_stats = _MutableStats()

        if self.config.include_tcp:
            records.extend(self._collect_kind("tcp", collection_time, mutable_stats))
        if self.config.include_udp:
            records.extend(self._collect_kind("udp", collection_time, mutable_stats))

        stats = CollectorStats(
            collection_time=collection_time,
            total_records=len(records),
            tcp_records=sum(1 for record in records if record.protocol == "TCP"),
            udp_records=sum(1 for record in records if record.protocol == "UDP"),
            access_denied=mutable_stats.access_denied,
            no_such_process=mutable_stats.no_such_process,
            zombie_process=mutable_stats.zombie_process,
            other_errors=mutable_stats.other_errors,
        )
        logger.debug("collection_complete", extra=stats.to_dict())
        return records, stats

    def _collect_kind(
        self,
        kind: str,
        collection_time: str,
        mutable_stats: _MutableStats,
    ) -> list[PortRecord]:
        try:
            connections = psutil.net_connections(kind=kind)
        except psutil.AccessDenied:
            mutable_stats.access_denied += 1
            logger.warning("net_connections_access_denied", extra={"kind": kind})
            return []
        except Exception:
            mutable_stats.other_errors += 1
            logger.exception("net_connections_failed", extra={"kind": kind})
            return []

        records: list[PortRecord] = []
        for conn in connections:
            try:
                if not self.config.include_ipv6 and self._is_ipv6(conn.laddr):
                    continue
                records.append(self._connection_to_record(kind, conn, collection_time, mutable_stats))
            except Exception:
                mutable_stats.other_errors += 1
                logger.exception("connection_record_failed", extra={"kind": kind, "pid": getattr(conn, "pid", None)})
        return records

    def _connection_to_record(
        self,
        kind: str,
        conn: psutil._common.sconn,
        collection_time: str,
        mutable_stats: _MutableStats,
    ) -> PortRecord:
        local_ip, local_port = self._endpoint_parts(conn.laddr)
        remote_ip, remote_port = self._endpoint_parts(conn.raddr)
        process = self.resolver.resolve(conn.pid, mutable_stats)

        state = conn.status if kind == "tcp" else "NONE"
        return PortRecord(
            protocol=kind.upper(),
            local_ip=local_ip,
            local_port=local_port,
            remote_ip=remote_ip,
            remote_port=remote_port,
            state=state or "UNKNOWN",
            pid=conn.pid,
            process_name=process.name,
            process_exe=process.exe,
            username=process.username,
            process_create_time=process.create_time,
            service_names=process.service_names,
            collection_time=collection_time,
            update_time=collection_time,
        )

    @staticmethod
    def _endpoint_parts(endpoint) -> tuple[str | None, int | None]:
        if not endpoint:
            return None, None
        try:
            return str(endpoint.ip), int(endpoint.port)
        except AttributeError:
            try:
                return str(endpoint[0]), int(endpoint[1])
            except (IndexError, TypeError, ValueError):
                logger.debug("malformed_endpoint", extra={"endpoint": repr(endpoint)})
                return None, None

    @staticmethod
    def _is_ipv6(endpoint) -> bool:
        ip, _ = PortCollector._endpoint_parts(endpoint)
        if not ip:
            return False
        try:
            return socket.inet_pton(socket.AF_INET6, ip) is not None
        except OSError:
            return False
