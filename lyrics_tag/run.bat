@echo off
title Lyrics Tag
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] .venv not found. Run: py -3.12 -m venv .venv
    pause
    exit /b 1
)

netstat -ano 2>nul | findstr ":5000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [INFO] Already running - opening browser...
    start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Process 'http://127.0.0.1:5000'"
    exit /b 0
)

echo [>>]  Starting server...
start "" ".venv\Scripts\pythonw.exe" "%~dp0app.py"
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://127.0.0.1:5000'"
