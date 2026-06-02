@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MP4 Downloader

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"

echo ============================================================
echo   MP4 / Video Downloader
echo ============================================================
echo.

if exist "%PY%" goto :install_deps

echo [SETUP] Creating virtual environment with Python 3.12...
py -3.12 -m venv "%VENV%"
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Virtual environment created.

:install_deps
echo [SETUP] Installing packages (first run may take a few minutes)...
"%PY%" -m pip install --upgrade pip -q
"%PIP%" install "numpy>=2.0" "pyarrow>=14.0" --prefer-binary -q
"%PIP%" install -r requirements.txt --prefer-binary -q
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)
echo [OK] Packages ready.

echo [SETUP] Checking Playwright browser...
"%PY%" -m playwright install chromium >nul 2>nul
echo [OK] Browser ready.

echo.
echo [RUN] Starting web UI... browser will open automatically.
echo       Press Ctrl+C to stop.
echo.
"%PY%" main.py
if errorlevel 1 goto :fail

endlocal
exit /b 0

:fail
echo.
echo [ERROR] An error occurred. Check the message above.
pause
exit /b 1