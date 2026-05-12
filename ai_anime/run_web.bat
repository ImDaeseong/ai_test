@echo off
setlocal

cd /d "%~dp0"
set PORT=8000

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python or add it to PATH.
  pause
  exit /b 1
)

for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"`) do (
  if not "%%P"=="" (
    echo Stopping existing web server on port %PORT%...
    taskkill /PID %%P /F >nul 2>nul
  )
)

start "AI Anime MV Web UI" python scripts\web_app.py --host 127.0.0.1 --port %PORT%
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:%PORT%/results"

pause
