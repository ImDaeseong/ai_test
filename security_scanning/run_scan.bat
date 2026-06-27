@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

set "PY=%~dp0.venv\Scripts\python.exe"
set "PIP=%~dp0.venv\Scripts\pip.exe"

if not exist "%PY%" (
    echo [SETUP] Creating virtual environment...
    py -3.12 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 ( echo [ERROR] Python not found. & pause & exit /b 1 )
)

"%PY%" -c "import requests, psutil, colorama" >nul 2>nul
if errorlevel 1 (
    echo [SETUP] Installing packages...
    "%PIP%" install -r requirements.txt -q
    if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
    echo [OK] Packages ready.
)

echo ============================================================
echo  DefenseScan - Full Demo Run
echo ============================================================
echo.

echo [1/3] Web scan : https://naver.com
echo ------------------------------------------------------------
"%PY%" main.py --web https://naver.com
echo.

echo [2/3] System scan (Windows)
echo ------------------------------------------------------------
"%PY%" main.py --system
echo.

echo [3/3] Help
echo ------------------------------------------------------------
"%PY%" main.py --help
echo.

echo ============================================================
echo  Done.
echo ============================================================
pause
