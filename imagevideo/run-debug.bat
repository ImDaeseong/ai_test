@echo off
chcp 65001 >nul
echo ========================================
echo  Lyric Video Generator [DEBUG]
echo ========================================
echo.
call npm run lyric-video -- --clean --debug
if %errorlevel% neq 0 (
    echo.
    echo [FAILED] Pipeline failed. Log: output\logs\pipeline.log
    exit /b 1
)
echo.
call npm run validate:media
echo.
echo Log: output\logs\pipeline.log
