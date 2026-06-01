from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Protocol

from collector.port_collector import PortCollector
from config_loader import AppConfig
from models import ServiceStatus, utc_now_iso
from storage.json_exporter import JsonExporter
from storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    def write_records(self, records, stats=None) -> None: ...


class BackgroundRunner:
    def __init__(
        self,
        config: AppConfig,
        collector: PortCollector | None = None,
        sqlite_store: SQLiteStore | None = None,
        json_exporter: JsonExporter | None = None,
    ) -> None:
        self.config = config
        self.collector = collector or PortCollector(config.collector)
        self.sqlite_store = sqlite_store if sqlite_store is not None else SQLiteStore(config.storage)
        self.json_exporter = json_exporter if json_exporter is not None else JsonExporter(config.storage)
        self.stop_event = threading.Event()
        self.status = ServiceStatus(state="initialized")
        self._thread: threading.Thread | None = None
        self._last_retention_day: str | None = None

    def install_signal_handlers(self) -> None:
        def _handler(signum, _frame) -> None:
            logger.info("signal_received", extra={"signal": signum})
            self.stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _handler)
            except Exception:
                logger.debug("signal_handler_not_installed", extra={"signal": getattr(sig, "name", sig)}, exc_info=True)

    def start(self, blocking: bool = True) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("BackgroundRunner is already started")
        self._clear_stop_file()
        self._open_backends()
        self.status = ServiceStatus(state="running", started_at=utc_now_iso())
        logger.info("monitor_started", extra={"polling_interval_seconds": self.config.collector.polling_interval_seconds})
        if blocking:
            self.run_loop()
        else:
            self._thread = threading.Thread(target=self.run_loop, name="PortMonitorRunner", daemon=False)
            self._thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def wait(self, timeout: float | None = None) -> bool:
        if not self._thread:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def run_loop(self) -> None:
        try:
            while not self.stop_event.is_set():
                self._check_stop_file()
                started = time.monotonic()
                try:
                    records, stats = self.collector.collect()
                    self._write_all(records, stats)
                    self._maybe_purge_retention()
                    self.status = ServiceStatus(
                        state="running",
                        started_at=self.status.started_at,
                        last_collection_time=stats.collection_time,
                    )
                    logger.info(
                        "collection_cycle_complete",
                        extra={"records": stats.total_records, "tcp": stats.tcp_records, "udp": stats.udp_records},
                    )
                except Exception as exc:
                    self.status = ServiceStatus(
                        state="degraded",
                        started_at=self.status.started_at,
                        last_collection_time=self.status.last_collection_time,
                        last_error=repr(exc),
                    )
                    logger.exception("collection_cycle_failed")

                elapsed = time.monotonic() - started
                sleep_for = max(0.1, self.config.collector.polling_interval_seconds - elapsed)
                self.stop_event.wait(sleep_for)
        finally:
            self._close_backends()
            self.status = ServiceStatus(
                state="stopped",
                started_at=self.status.started_at,
                stopped_at=utc_now_iso(),
                last_collection_time=self.status.last_collection_time,
                last_error=self.status.last_error,
            )
            logger.info("monitor_stopped", extra=self.status.to_dict())

    @property
    def _stop_file_path(self):
        return self.config.root_dir / "data" / "port_monitor.stop"

    def _clear_stop_file(self) -> None:
        try:
            self._stop_file_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("stop_file_clear_failed", extra={"path": str(self._stop_file_path)}, exc_info=True)

    def _check_stop_file(self) -> None:
        try:
            if self._stop_file_path.exists():
                logger.info("stop_file_detected", extra={"path": str(self._stop_file_path)})
                self.stop()
        except Exception:
            logger.warning("stop_file_check_failed", extra={"path": str(self._stop_file_path)}, exc_info=True)

    def _open_backends(self) -> None:
        if self.config.storage.sqlite_enabled:
            try:
                self.sqlite_store.open()
            except Exception:
                logger.exception("sqlite_open_failed")

    def _close_backends(self) -> None:
        if self.config.storage.sqlite_enabled:
            try:
                self.sqlite_store.close()
            except Exception:
                logger.exception("sqlite_close_failed")

    def _write_all(self, records, stats) -> None:
        if self.config.storage.sqlite_enabled:
            self.sqlite_store.write_records(records, stats)
        if self.config.storage.json_export_enabled:
            self.json_exporter.write_records(records, stats)

    def _maybe_purge_retention(self) -> None:
        if not self.config.storage.sqlite_enabled:
            return
        today = datetime.now(timezone.utc).date().isoformat()
        if self._last_retention_day == today:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.storage.retention_days)
        self.sqlite_store.purge_older_than(cutoff.isoformat(timespec="milliseconds"))
        self._last_retention_day = today
