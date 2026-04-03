@echo off
chcp 65001 >nul

:: 임베디드 Python(setup.bat) 우선, 없으면 .venv(개발환경) 사용
if exist "%~dp0python\Scripts\streamlit.exe" (
    set STREAMLIT=%~dp0python\Scripts\streamlit.exe
) else if exist "%~dp0.venv\Scripts\streamlit.exe" (
    set STREAMLIT=%~dp0.venv\Scripts\streamlit.exe
) else (
    echo [오류] 설치가 필요합니다. setup.bat 을 먼저 실행하세요.
    pause & exit /b 1
)

:: ffmpeg 확인
if not exist "%~dp0ffmpeg.exe" (
    echo [경고] ffmpeg.exe가 없습니다. 다운로드가 실패할 수 있습니다.
    echo.
)

echo Video Downloader 시작 중...
echo 브라우저가 자동으로 열립니다. 이 창을 닫으면 종료됩니다.
echo.

"%STREAMLIT%" run "%~dp0app.py" --server.headless false
