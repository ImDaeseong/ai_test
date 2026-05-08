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

echo Rendering YouTube-ready MP4...
call npm run build
if errorlevel 1 (
  echo Render failed.
  pause
  exit /b 1
)

echo.
echo Render complete:
echo %~dp0out\lyric-video.mp4
start "" "%~dp0out"
pause

endlocal
