@echo off
setlocal

cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

echo ============================================================
echo   Suno AI Mastering Web UI
echo ============================================================

if not exist "%PYTHON_EXE%" (
    echo [SETUP] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo         Please check that Python is installed and available on PATH.
        pause
        exit /b 1
    )
)

echo [SETUP] Installing/updating required packages...
"%PIP_EXE%" install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install required packages.
    pause
    exit /b 1
)

echo.
echo [RUN] Opening http://localhost:5000
start "" "http://localhost:5000"

echo [RUN] Starting Flask server...
"%PYTHON_EXE%" server.py

echo.
echo [DONE] Server stopped.
pause
