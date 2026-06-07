@echo off
chcp 65001 > nul
setlocal
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo ------------------------------------------
echo   ai-webtoon  Web Viewer
echo   http://127.0.0.1:5350
echo   Ctrl+C to stop
echo ------------------------------------------
python web_app.py
endlocal
