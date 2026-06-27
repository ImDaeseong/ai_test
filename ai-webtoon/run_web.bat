@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set "PY=%~dp0.venv\Scripts\python.exe"
set "PIP=%~dp0.venv\Scripts\pip.exe"

if not exist "%PY%" (
    echo [SETUP] Creating virtual environment...
    py -3.12 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 ( echo [ERROR] Python not found. & pause & exit /b 1 )
)

"%PY%" -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing packages...
    "%PIP%" install -r requirements.txt -q
    if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
    echo [OK] Packages ready.
)

echo ------------------------------------------
echo   ai-webtoon  Web Viewer
echo   http://127.0.0.1:5350
echo   Ctrl+C to stop
echo ------------------------------------------
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://127.0.0.1:5350'"
"%PY%" web_app.py
