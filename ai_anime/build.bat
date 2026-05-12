@echo off
setlocal
cd /d "%~dp0"

echo === AI Anime MV Builder - PyInstaller Build ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please add Python to PATH.
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

if exist dist\ai_anime_mv_builder (
    echo Removing previous build...
    rmdir /s /q dist\ai_anime_mv_builder
)
if exist build rmdir /s /q build

echo Building...
echo.

pyinstaller --name ai_anime_mv_builder --noconsole --paths scripts --hidden-import emotion_engine --hidden-import image_prompt_generator --hidden-import video_prompt_generator --hidden-import scene_generator --hidden-import run_pipeline --hidden-import song_parser --hidden-import common --hidden-import web_app scripts\main_entry.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo === Build complete ===
echo Output: dist\ai_anime_mv_builder\ai_anime_mv_builder.exe
echo Copy the entire dist\ai_anime_mv_builder\ folder to deploy.
echo.

pause
