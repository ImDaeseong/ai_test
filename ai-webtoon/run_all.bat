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

echo.
echo ================================================================
echo   STEP 1/2  --  create-all
echo ================================================================
"%PY%" main.py create-all --input-dir input --force
if errorlevel 1 goto :create_error

echo.
echo ================================================================
echo   STEP 2/2  --  summarize-all
echo ================================================================
"%PY%" main.py summarize-all --input-dir input --output-dir output
if errorlevel 1 (
    echo.
    echo [WARNING] Some songs failed validation. Check output above.
)

echo.
pause
exit /b 0

:create_error
echo.
echo [ERROR] create-all failed.
pause
exit /b 1
