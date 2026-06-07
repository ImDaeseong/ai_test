@echo off
setlocal
title AI Anime MV Builder - Build

cd /d "%~dp0"

echo === AI Anime MV Builder - Build System ===
echo.

echo [1/4] Checking Python environment...
python --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

echo [2/4] Installing dependencies (PyInstaller)...
python -m pip install --upgrade pip
python -m pip install pyinstaller

echo [3/4] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo [4/4] Starting build process...
echo.

python -m PyInstaller ^
    --name ai_anime_mv_builder ^
    --noconsole ^
    --onefile ^
    --paths scripts ^
    --hidden-import emotion_engine ^
    --hidden-import image_prompt_generator ^
    --hidden-import video_prompt_generator ^
    --hidden-import scene_generator ^
    --hidden-import run_pipeline ^
    --hidden-import song_parser ^
    --hidden-import common ^
    --hidden-import web_app ^
    scripts\main_entry.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo === Build Complete! (dist\ai_anime_mv_builder.exe) ===
echo.
pause
