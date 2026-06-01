from __future__ import annotations

import argparse
import logging
import sys

from config_loader import load_config
from logging_setup import configure_logging
from service.background_runner import BackgroundRunner
from service.windows_service import handle_service_command

logger = logging.getLogger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Windows TCP/UDP Port Monitor")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "once", "install", "remove", "uninstall", "start", "stop", "restart", "debug"],
        help="Execution mode or Windows Service command.",
    )
    parser.add_argument("--config", help="Path to config.yaml", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command in {"install", "remove", "uninstall", "start", "stop", "restart", "debug"}:
        return handle_service_command()

    config = load_config(args.config)
    log_path = configure_logging(config.logging)
    logger.info("application_starting", extra={"command": args.command, "log_path": str(log_path)})

    runner = BackgroundRunner(config)
    if args.command == "once":
        try:
            runner._open_backends()
            records, stats = runner.collector.collect()
            runner._write_all(records, stats)
            logger.info("single_collection_complete", extra=stats.to_dict())
            print(f"Collected {stats.total_records} records ({stats.tcp_records} TCP, {stats.udp_records} UDP)")
            return 0
        finally:
            runner._close_backends()

    runner.install_signal_handlers()
    runner.start(blocking=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
