from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Protocol

import psutil

from models import ProcessInfo

logger = logging.getLogger(__name__)


class StatsSink(Protocol):
    access_denied: int
    no_such_process: int
    zombie_process: int
    other_errors: int


@dataclass
class _CacheEntry:
    expires_at: float
    value: ProcessInfo


class ProcessResolver:
    def __init__(self, cache_ttl_seconds: float = 30.0, enable_service_lookup: bool = True) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_service_lookup = enable_service_lookup
        self._cache: dict[int, _CacheEntry] = {}
        self._service_cache: dict[int, tuple[str, ...]] = {}
        self._service_cache_expires_at = 0.0

    def resolve(self, pid: int | None, stats: StatsSink | None = None) -> ProcessInfo:
        if pid is None:
            return ProcessInfo(pid=None, error="missing_pid")

        now = time.monotonic()
        cached = self._cache.get(pid)
        if cached and cached.expires_at > now:
            return cached.value

        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                info = ProcessInfo(
                    pid=pid,
                    name=self._safe_call(proc.name),
                    exe=self._safe_call(proc.exe),
                    username=self._safe_call(proc.username),
                    create_time=self._safe_call(proc.create_time),
                    service_names=self._service_names_for_pid(pid),
                )
        except psutil.AccessDenied:
            if stats:
                stats.access_denied += 1
            logger.debug("process_access_denied", extra={"pid": pid})
            info = ProcessInfo(pid=pid, service_names=self._service_names_for_pid(pid), error="access_denied")
        except psutil.NoSuchProcess:
            if stats:
                stats.no_such_process += 1
            logger.debug("process_no_such_process", extra={"pid": pid})
            info = ProcessInfo(pid=pid, error="no_such_process")
        except psutil.ZombieProcess:
            if stats:
                stats.zombie_process += 1
            logger.debug("process_zombie", extra={"pid": pid})
            info = ProcessInfo(pid=pid, error="zombie_process")
        except Exception:
            if stats:
                stats.other_errors += 1
            logger.exception("process_resolve_failed", extra={"pid": pid})
            info = ProcessInfo(pid=pid, error="resolve_failed")

        self._cache[pid] = _CacheEntry(expires_at=now + self.cache_ttl_seconds, value=info)
        self._purge_expired(now)
        return info

    def _safe_call(self, func):
        try:
            return func()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            return None
        except Exception:
            logger.debug("process_attribute_failed", exc_info=True)
            return None

    def _purge_expired(self, now: float) -> None:
        if len(self._cache) < 4096:
            return
        expired = [pid for pid, entry in self._cache.items() if entry.expires_at <= now]
        for pid in expired:
            self._cache.pop(pid, None)

    def _service_names_for_pid(self, pid: int) -> tuple[str, ...]:
        if not self.enable_service_lookup:
            return ()
        now = time.monotonic()
        if now >= self._service_cache_expires_at:
            self._service_cache = self._load_service_map()
            self._service_cache_expires_at = now + self.cache_ttl_seconds
        return self._service_cache.get(pid, ())

    def _load_service_map(self) -> dict[int, tuple[str, ...]]:
        if not psutil.WINDOWS:
            return {}
        try:
            completed = subprocess.run(
                ["sc.exe", "queryex", "type=", "service", "state=", "all"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            logger.debug("service_lookup_failed", exc_info=True)
            return {}

        if completed.returncode != 0:
            logger.debug("service_lookup_nonzero", extra={"returncode": completed.returncode})
            return {}

        services_by_pid: dict[int, list[str]] = {}
        current_name: str | None = None
        for raw_line in completed.stdout.splitlines():
            line = raw_line.strip()
            if line.startswith("SERVICE_NAME:"):
                current_name = line.split(":", 1)[1].strip()
            elif line.startswith("PID") and current_name:
                parts = line.split(":", 1)
                if len(parts) < 2:
                    continue
                try:
                    service_pid = int(parts[1].strip())
                except ValueError:
                    continue
                if service_pid > 0:
                    services_by_pid.setdefault(service_pid, []).append(current_name)
        return {pid: tuple(sorted(names)) for pid, names in services_by_pid.items()}
