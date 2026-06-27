@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MP4 Downloader

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "CHROMIUM=%LOCALAPPDATA%\ms-playwright\chromium-1208\chrome-win64\chrome.exe"

echo ============================================================
echo   MP4 / Video Downloader
echo ============================================================
echo.

if exist "%PY%" goto :check_packages

echo [SETUP] Creating virtual environment with Python 3.12...
py -3.12 -m venv "%VENV%"
if errorlevel 1 (
    echo [ERROR] Python 3.12 not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Virtual environment created.
goto :install_deps

:check_packages
"%PY%" -c "import streamlit, yt_dlp, playwright" >nul 2>nul
if errorlevel 1 goto :install_deps
echo [OK] Packages ready.
goto :check_playwright

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

:check_playwright
if exist "%CHROMIUM%" (
    echo [OK] Browser ready.
    goto :run
)
echo [SETUP] Downloading Playwright browser (one-time, ~150 MB)...
"%PY%" -m playwright install chromium
if errorlevel 1 (
    echo [WARN] Playwright browser install failed. Playwright features may not work.
)
echo [OK] Browser ready.

:run
echo.
echo [RUN] Starting web UI...
echo       http://localhost:8501
echo       Press Ctrl+C to stop.
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 4; Start-Process 'http://localhost:8501'"
"%PY%" main.py
if errorlevel 1 goto :fail

endlocal
exit /b 0

:fail
echo.
echo [ERROR] An error occurred. Check the message above.
pause
exit /b 1
