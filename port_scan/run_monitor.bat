@echo off
setlocal EnableDelayedExpansion

title Network Monitor v5.0

echo.
echo ============================================================
echo    Windows Network Connection and Process Monitor v5.0
echo ============================================================
echo.

:: ----------------------------------------------------------
:: [1] Administrator privilege check and auto-elevation
:: ----------------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Administrator privileges required.
    echo [*] Requesting elevation via UAC...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
echo [OK] Running as Administrator
echo.

:: ----------------------------------------------------------
:: [2] Change to script directory
:: ----------------------------------------------------------
cd /d "%~dp0"
echo [OK] Working directory: %CD%
echo.

:: ----------------------------------------------------------
:: [3] Python installation check
:: ----------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.8+ from https://www.python.org
    echo         Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] %PYVER%
echo.

:: ----------------------------------------------------------
:: [4] psutil installation check and auto-install
:: ----------------------------------------------------------
python -c "import psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] psutil not found. Installing...
    python -m pip install psutil --quiet
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install psutil.
        echo         Run manually: pip install psutil
        echo.
        pause
        exit /b 1
    )
    echo [OK] psutil installed successfully.
) else (
    for /f "tokens=*" %%v in ('python -c "import psutil; print(psutil.__version__)"') do (
        echo [OK] psutil %%v already installed.
    )
)
echo.

:: ----------------------------------------------------------
:: [5] network_monitor.py existence check
:: ----------------------------------------------------------
if not exist "%~dp0network_monitor.py" (
    echo [ERROR] network_monitor.py not found at:
    echo         %~dp0network_monitor.py
    echo.
    pause
    exit /b 1
)
echo [OK] network_monitor.py found.
echo.

:: ----------------------------------------------------------
:: [6] Output file paths
:: ----------------------------------------------------------
echo [INFO] Output log files will be created in:
echo        %~dp0
echo.
echo        network_monitor.log      - Text log (10MB rotate, backupCount=3)
echo        network_log.json         - TCP/UDP connections + HTTP/HTTPS detection (10MB rotate)
echo.
echo [INFO] Press Ctrl+C to stop monitoring.
echo ============================================================
echo.

:: ----------------------------------------------------------
:: [7] Launch monitor
::     Note: Python script itself also handles UAC elevation.
::     Running from this elevated batch provides a clean start.
:: ----------------------------------------------------------
python "%~dp0network_monitor.py"

:: ----------------------------------------------------------
:: [8] Exit handling
:: ----------------------------------------------------------
echo.
echo ============================================================
if %errorlevel% neq 0 (
    echo [ERROR] Monitor exited with code: %errorlevel%
) else (
    echo [OK] Monitor stopped normally.
)
echo ============================================================
echo.
pause
endlocal
