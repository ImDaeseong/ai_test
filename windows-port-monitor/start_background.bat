@echo off
setlocal

set "APP_DIR=%~dp0"
set "PID_FILE=%APP_DIR%data\port_monitor.pid"
set "STOP_FILE=%APP_DIR%data\port_monitor.stop"
set "START_FILE=%APP_DIR%data\port_monitor.started_at"
set "LOG_DIR=%APP_DIR%logs"

if not exist "%APP_DIR%data" mkdir "%APP_DIR%data"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if exist "%STOP_FILE%" del /f /q "%STOP_FILE%" >nul 2>&1

set "PYTHON_EXE=python"
if exist "%APP_DIR%.venv\Scripts\python.exe" set "PYTHON_EXE=%APP_DIR%.venv\Scripts\python.exe"

if exist "%PID_FILE%" (
    for /f "usebackq delims=" %%P in ("%PID_FILE%") do set "OLD_PID=%%P"
    if defined OLD_PID (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-Process -Id %OLD_PID% -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
        if not errorlevel 1 (
            echo Port monitor is already running. PID=%OLD_PID%
            exit /b 0
        )
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$startedAt = (Get-Date).ToUniversalTime().ToString('o'); $p = Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'main.py run' -WorkingDirectory '%APP_DIR%' -WindowStyle Hidden -PassThru; Set-Content -Path '%PID_FILE%' -Value $p.Id; Set-Content -Path '%START_FILE%' -Value $startedAt; Write-Host ('Started Windows Port Monitor. PID=' + $p.Id); Write-Host ('Session start UTC=' + $startedAt)"

endlocal
