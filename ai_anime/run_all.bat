@echo off
chcp 65001
title AI Anime - Import Input Songs

cd /d "%~dp0"

echo.
echo ============================================================
echo   AI Anime  input folder import
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please check your PATH.
    exit /b 1
)

python scripts\import_input_songs.py --force %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [FAILED]
) else (
    echo.
    echo [DONE]
)
echo.
pause
