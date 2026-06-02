@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"
title MP3 DAW Local Audio Processor

set "APP_URL=http://localhost:8080"
set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHON_BIN=%PYTHON_EXE%"
if exist "C:\Program Files\Go\bin\go.exe" (
    set "GOROOT=C:\Program Files\Go"
    set "PATH=C:\Program Files\Go\bin;%PATH%"
)

echo ============================================================
echo   MP3 DAW Local Audio Processor
echo ============================================================
echo.

where go >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Go is not installed or not available on PATH.
    echo         Install Go 1.21 or newer, then run this file again.
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [SETUP] Creating Python virtual environment...
    py -3.12 -m venv "%VENV_DIR%" >nul 2>nul
    if errorlevel 1 (
        where python >nul 2>nul
        if errorlevel 1 (
            echo [ERROR] Python is not installed or not available on PATH.
            echo         Install Python 3.10 or newer, then run this file again.
            pause
            exit /b 1
        )
        python -m venv "%VENV_DIR%"
        if errorlevel 1 (
            echo [ERROR] Failed to create Python virtual environment.
            pause
            exit /b 1
        )
    )
) else (
    echo [OK] Python virtual environment ready.
)

echo [SETUP] Installing/updating Python packages...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PIP_EXE%" install -r requirements.txt
if errorlevel 1 goto :fail

echo [SETUP] Downloading Go modules...
go mod download
if errorlevel 1 goto :fail

if not exist "inbox" mkdir "inbox"
if not exist "output" mkdir "output"

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [WARN] FFmpeg was not found on PATH.
    echo        MP3 decoding/export may be limited until FFmpeg is installed.
) else (
    echo [OK] FFmpeg found.
)

netstat -ano 2>nul | findstr ":8080 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [ERROR] Port 8080 is already in use.
    echo         Stop the existing process or change the server port in main.go.
    pause
    exit /b 1
)

echo.
echo [RUN] Opening %APP_URL%
start "" "%APP_URL%"

echo [RUN] Starting Go web server...
echo       Press Ctrl+C to stop.
echo.
go run .
if errorlevel 1 goto :fail

echo.
echo [DONE] Server stopped.
pause
exit /b 0

:fail
echo.
echo [ERROR] Run failed. Check the message above.
pause
exit /b 1
