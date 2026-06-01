@echo off
chcp 65001 >nul
cd /d %~dp0

echo ========================================
echo  Lyric Video Generator
echo ========================================
echo.

echo [CLEAN] Resetting output folder...
if exist output (
    rd /s /q output
)
mkdir output
mkdir output\logs
echo [CLEAN] Done.
echo.

echo [1/2] Running pipeline...
call npm run lyric-video -- --clean
if %errorlevel% neq 0 (
    echo.
    echo [FAILED] Pipeline failed. See log: output\logs\pipeline.log
    exit /b 1
)

echo.
echo [2/2] Validating output...
call npm run validate:media
if %errorlevel% neq 0 (
    echo.
    echo [FAILED] Validation failed.
    exit /b 1
)

echo.
echo ========================================
echo  Done. Output file: output\lyric_video.mp4
echo ========================================
