from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Iterable

from config_loader import StorageConfig
from models import CollectorStats, PortRecord

logger = logging.getLogger(__name__)


class JsonExporter:
    def __init__(self, config: StorageConfig) -> None:
        self.path: Path = config.json_export_path
        self._lock = threading.RLock()

    def write_records(self, records: Iterable[PortRecord], stats: CollectorStats | None = None) -> None:
        batch = list(records)
        if not batch and stats is None:
            return

        payloads = [{"type": "port_record", **record.to_dict()} for record in batch]
        if stats:
            payloads.append({"type": "collector_stats", **stats.to_dict()})

        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    for payload in payloads:
                        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                        handle.write("\n")
            logger.debug("json_export_complete", extra={"records": len(batch), "path": str(self.path)})
        except Exception:
            logger.exception("json_export_failed", extra={"records": len(batch), "path": str(self.path)})
