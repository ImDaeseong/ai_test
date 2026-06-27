@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "PYTHONUTF8=1"

echo ============================================================
echo AI Pexels Video Generator
echo ============================================================
echo.
echo This will:
echo   1. Prepare Python environment
echo   2. Check .env and FFmpeg
echo   3. Run tests
echo   4. Generate landscape and shorts videos from data folder
echo   5. Open output\index.html in your browser
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [1/5] Virtual environment ready.
)

set "PYTHON=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

echo [2/5] Installing requirements...
"%PYTHON%" -m pip install --upgrade pip -q
if errorlevel 1 goto :fail
"%PIP%" install -r requirements.txt -q
if errorlevel 1 goto :fail
echo [OK] Requirements ready.

if not exist ".env" (
    echo.
    echo ERROR: .env not found.
    echo A .env file is required with GEMINI_API_KEY and PEXELS_API_KEY.
    echo Creating .env from .env.example now. Please edit it and run this again.
    copy ".env.example" ".env" >nul
    goto :fail
)

echo [3/5] Checking FFmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo ERROR: FFmpeg is not installed or not in PATH.
    goto :fail
)
ffmpeg -version >nul
if errorlevel 1 goto :fail

if not exist "data" (
    echo ERROR: data folder does not exist.
    goto :fail
)

if not exist "output" (
    echo Creating output folder...
    mkdir "output"
    if errorlevel 1 goto :fail
)
if not exist "output\.gitkeep" type nul > "output\.gitkeep"

echo [4/5] Running tests...
"%PYTHON%" -m pytest --basetemp=.pytest_tmp -q
if errorlevel 1 goto :fail

echo [5/5] Generating video and browser report...
"%PYTHON%" scripts\generate_from_data.py --data-dir data --report output\index.html --both --open
if errorlevel 1 goto :fail

echo.
echo Done.
echo Landscape: output\final_landscape.mp4
echo Shorts   : output\final_shorts.mp4
echo Report: output\index.html
echo.
pause
exit /b 0

:fail
echo.
echo FAILED: Check the message above.
echo.
pause
exit /b 1
