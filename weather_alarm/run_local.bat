@echo off
chcp 65001 >nul
echo [weather_alarm] Local mode - SQLite (no Docker required)
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.12+
    pause
    exit /b 1
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo Installing packages...
pip install -r requirements.txt -q
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

set WEATHER_ALARM_LOCAL=1

echo.
echo [DB] SQLite - weather_alarm.db
echo [START] python main.py  ^(Ctrl+C to stop^)
echo.
python main.py
pause
