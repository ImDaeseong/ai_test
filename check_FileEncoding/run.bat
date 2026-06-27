@echo off
title Check File Encoding
cd /d "%~dp0"

echo.
echo +--------------------------------------------------------------+
echo ^|      Check File Encoding  ^@  http://localhost:8080          ^|
echo +--------------------------------------------------------------+
echo.

where go > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Go not found. Install from https://go.dev/dl/
    pause
    exit /b 1
)

for /f "tokens=3" %%v in ('go version 2^>^&1') do set GO_VER=%%v
echo [OK]   Go %GO_VER%

netstat -ano 2>nul | findstr ":8080 " | findstr "LISTENING" > nul
if not errorlevel 1 (
    echo [WARN]  Port 8080 already in use.
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 exit /b 0
)

echo [>>]  Building...
go build -o check_FileEncoding.exe .
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)
echo [OK]   Build complete

echo [>>]  Starting server...
echo [>>]  Browser opens in 2 seconds  (Ctrl+C to stop)
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://localhost:8080'"
.\check_FileEncoding.exe

echo.
echo [INFO] Server stopped.
pause
