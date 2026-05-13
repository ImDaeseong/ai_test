@echo off
setlocal
title AI Anime MV Builder - Web Server

cd /d "%~dp0"
set PORT=8000

echo [1/3] Checking Python environment...
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please check your PATH.
    pause
    exit /b 1
)

python --version

echo [2/3] Checking for existing processes on port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo [3/3] Starting web server at http://127.0.0.1:%PORT%...
echo * Close this window to stop the server.

:: Open browser
start "" "http://127.0.0.1:%PORT%/results"

:: Run server
python scripts\web_app.py --host 127.0.0.1 --port %PORT%

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start server.
    pause
)
