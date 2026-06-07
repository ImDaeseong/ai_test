@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "RUNNER=%PROJECT_ROOT%scripts\webtoon-capcut.ps1"
set "MENU=%PROJECT_ROOT%scripts\webtoon-capcut-menu.ps1"

if not exist "%RUNNER%" (
    echo [ERROR] Missing: %RUNNER%
    pause
    exit /b 1
)

if not "%~1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" %*
    exit /b %ERRORLEVEL%
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%MENU%"
exit /b %ERRORLEVEL%
