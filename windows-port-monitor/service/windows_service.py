from __future__ import annotations

import logging
import sys
from pathlib import Path

from config_loader import load_config
from logging_setup import configure_logging
from service.background_runner import BackgroundRunner

logger = logging.getLogger(__name__)


try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = None


if win32serviceutil:

    class WindowsPortMonitorService(win32serviceutil.ServiceFramework):
        _svc_name_ = "WindowsPortMonitor"
        _svc_display_name_ = "Windows TCP/UDP Port Monitor"
        _svc_description_ = "Collects TCP/UDP port, connection, and process metadata for local observability."

        def __init__(self, args) -> None:
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.runner: BackgroundRunner | None = None

        def SvcStop(self) -> None:
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            logger.info("service_stop_requested")
            if self.runner:
                self.runner.stop()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self) -> None:
            if servicemanager:
                servicemanager.LogInfoMsg("WindowsPortMonitor service starting")
            config = load_config()
            configure_logging(config.logging)
            self.runner = BackgroundRunner(config)
            self.runner.start(blocking=False)
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            if self.runner:
                self.runner.stop()
                self.runner.wait(timeout=30)
            if servicemanager:
                servicemanager.LogInfoMsg("WindowsPortMonitor service stopped")

else:

    class WindowsPortMonitorService:  # type: ignore[no-redef]
        """Fallback symbol used when pywin32 is unavailable."""


def handle_service_command() -> int:
    if not win32serviceutil:
        print("pywin32 is required for Windows Service commands. Install requirements on Windows.")
        return 2
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    win32serviceutil.HandleCommandLine(WindowsPortMonitorService)
    return 0
