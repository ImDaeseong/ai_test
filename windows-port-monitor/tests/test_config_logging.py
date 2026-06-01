from __future__ import annotations

import logging

from config_loader import load_config
from logging_setup import configure_logging


def test_config_loading_defaults():
    config = load_config()
    assert config.collector.polling_interval_seconds >= 1.0
    assert config.storage.database_path.name == "port_monitor.sqlite3"
    assert config.service.name == "WindowsPortMonitor"


def test_logging_initialization(tmp_path):
    config = load_config()
    logging_config = config.logging.__class__(
        log_dir=tmp_path,
        log_file="test.log",
        level="DEBUG",
        max_bytes=2048,
        backup_count=1,
    )
    log_path = configure_logging(logging_config)
    logging.getLogger("test").info("hello")

    assert log_path.exists()
