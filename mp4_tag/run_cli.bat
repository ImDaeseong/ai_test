@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"

if not exist "%PY%" (
    py -3.12 -m venv "%VENV%"
    "%PY%" -m pip install --upgrade pip -q
    "%PIP%" install "numpy>=2.0" "pyarrow>=14.0" --prefer-binary -q
    "%PIP%" install -r requirements.txt --prefer-binary -q
    "%PY%" -m playwright install chromium >nul 2>nul
)

"%PY%" main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Failed. See message above.
    pause
    exit /b 1
)

endlocal
exit /b 0