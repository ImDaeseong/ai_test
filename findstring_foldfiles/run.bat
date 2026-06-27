@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 ( echo [ERROR] Python not found. Install from https://python.org & pause & exit /b 1 )
python "%~dp0find_string_app.py"
