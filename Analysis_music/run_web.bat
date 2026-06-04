@echo off
chcp 65001 > nul
title AI Music Producer - Web UI
if "%APP_PORT%"=="" set APP_PORT=5001
echo.
echo +--------------------------------------------------------------+
echo ^|      AI Music ^& Visual Content Executive Producer          ^|
echo ^|      Web UI ^@ http://localhost:%APP_PORT%                        ^|
echo +--------------------------------------------------------------+
echo.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo   Run: python -m venv .venv
    echo        .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('".venv\Scripts\python.exe" --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (set PY_MAJOR=%%a & set PY_MINOR=%%b)
if %PY_MAJOR% LSS 3 goto :pyerr
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 9 goto :pyerr
echo [OK]   Python %PY_VER%
goto :pyok

:pyerr
echo [ERROR] Python 3.9+ required. Current: %PY_VER%
pause
exit /b 1

:pyok
".venv\Scripts\python.exe" -c "import flask, librosa, markdown2, bleach" 2>nul
if errorlevel 1 (
    echo [WARN]  Missing packages - installing...
    ".venv\Scripts\pip.exe" install -r requirements.txt
    if errorlevel 1 (echo [ERROR] Install failed & pause & exit /b 1)
)
echo [OK]   Packages ready

if not exist "outputs" mkdir outputs
if not exist "uploads" mkdir uploads
echo [OK]   Output folders ready

if not exist ".env" (echo [WARN]  .env not found & echo.)

netstat -ano 2>nul | findstr ":%APP_PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo [WARN]  Port %APP_PORT% is already in use.
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 exit /b 0
)

echo [>>]  Starting Flask server...
echo [>>]  Browser opens in 3 seconds  ^(Ctrl+C to stop^)
echo.
start "" cmd /c "timeout /t 3 /nobreak > nul ^&^& start http://localhost:%APP_PORT%"

".venv\Scripts\python.exe" web\app.py

if errorlevel 1 (echo. & echo [ERROR] Server exited with error.)
pause
