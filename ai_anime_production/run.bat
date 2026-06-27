@echo off
cd /d "%~dp0"
title AI Anime Production

if not exist "node_modules" (
    echo [SETUP] Installing npm packages...
    call npm install
    if errorlevel 1 ( echo [ERROR] npm install failed. & pause & exit /b 1 )
    echo [OK] npm packages ready.
    echo.
)

if /I "%~1"=="full" goto FULL
if /I "%~1"=="import" goto IMPORT
if /I "%~1"=="render" goto RENDER
if /I "%~1"=="check" goto CHECK
if /I "%~1"=="studio" goto STUDIO

:MENU
cls
echo ==================================================
echo   AI Anime Production
echo ==================================================
echo.
echo   1. Full run  (import + render, create mp4)
echo   2. Import    (read input files)
echo   3. Render    (create scene mp4)
echo   4. Studio    (browser preview)
echo   5. Check     (asset check only, no render)
echo   6. Exit
echo.
set "CHOICE="
set /p CHOICE="Select (1-6): "

if "%CHOICE%"=="1" goto FULL
if "%CHOICE%"=="2" goto IMPORT
if "%CHOICE%"=="3" goto RENDER
if "%CHOICE%"=="4" goto STUDIO
if "%CHOICE%"=="5" goto CHECK
if "%CHOICE%"=="6" exit /b 0
goto MENU

:FULL
cls
echo [1/2] Importing input files...
echo.
node scripts\import_input.mjs
if errorlevel 1 (
    echo.
    echo ERROR: Import failed. Check the input folder and file names.
    goto END
)
echo.
echo [2/2] Rendering mp4...
echo.
node scripts\render_scenes.mjs
if errorlevel 1 (
    echo.
    echo ERROR: Render failed.
    goto END
)
echo.
echo Done. Opening output\clips.
if exist "output\clips" start explorer output\clips
goto END

:IMPORT
cls
echo Importing input files...
echo.
node scripts\import_input.mjs
if errorlevel 1 (
    echo ERROR: Import failed.
) else (
    echo Done.
)
goto END

:RENDER
cls
if not exist "manifests\render_manifest.json" (
    echo ERROR: manifests\render_manifest.json not found. Run Import first.
    goto END
)
echo Rendering mp4...
echo.
node scripts\render_scenes.mjs
if errorlevel 1 (
    echo ERROR: Render failed.
) else (
    echo Done.
    if exist "output\clips" start explorer output\clips
)
goto END

:STUDIO
cls
echo Starting Remotion Studio... Press Ctrl+C to stop.
echo.
npx remotion studio src/index.ts
goto END

:CHECK
cls
node scripts\check_assets.mjs --allow-placeholders
echo.
echo Check complete: this menu only checks assets.
echo To create an mp4, select menu 1 Full run or menu 3 Render.
goto END

:END
echo.
if not "%~1"=="" exit /b %ERRORLEVEL%
pause
goto MENU