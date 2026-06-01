@echo off
setlocal

cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Please install Node.js first.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)

dir /b "public\media\*.mp3" "public\media\*.wav" >nul 2>nul
if errorlevel 1 (
  echo Missing audio file.
  echo Add an MP3 or WAV file to public\media.
  pause
  exit /b 1
)

dir /b "public\media\*.lrc" "public\media\*.srt" >nul 2>nul
if errorlevel 1 (
  echo Missing lyric timing file.
  echo Add an LRC or SRT file to public\media.
  pause
  exit /b 1
)

echo Select format:
echo   1. 16:9 Landscape (YouTube)
echo   2. 9:16 Vertical  (Shorts / Reels / TikTok)
echo   3. Both
set /p FORMAT="Enter 1, 2 or 3 [default: 1]: "
if "%FORMAT%"=="" set FORMAT=1

if "%FORMAT%"=="1" goto landscape
if "%FORMAT%"=="2" goto vertical
if "%FORMAT%"=="3" goto both
echo Invalid choice, rendering landscape.

:landscape
echo Rendering 16:9 MP4...
call npm run build
if errorlevel 1 ( echo Render failed. & pause & exit /b 1 )
goto done

:vertical
echo Rendering 9:16 MP4...
call npm run build:vertical
if errorlevel 1 ( echo Render failed. & pause & exit /b 1 )
goto done

:both
echo Rendering 16:9...
call npm run build
if errorlevel 1 ( echo Render failed. & pause & exit /b 1 )
echo Rendering 9:16...
call npm run build:vertical
if errorlevel 1 ( echo Render failed. & pause & exit /b 1 )

:done
echo.
echo Render complete. Output folder:
echo %~dp0out
start "" "%~dp0out"
pause

endlocal
