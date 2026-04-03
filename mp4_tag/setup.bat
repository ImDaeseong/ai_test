@echo off
chcp 65001 >nul
echo ============================================
echo  Video Downloader - 완전 자동 설치
echo  (Python 설치 불필요)
echo ============================================
echo.

set PYVER=3.12.9
set PYDIR=%~dp0python
set PYEXE=%PYDIR%\python.exe
set PIPEXE=%PYDIR%\Scripts\pip.exe
set ZIPURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip
set ZIPFILE=%~dp0python-embed.zip
set GETPIP=%~dp0get-pip.py

:: ── ffmpeg 확인 ──────────────────────────────
if exist "%~dp0ffmpeg.exe" (
    echo [OK] ffmpeg.exe 확인됨
) else (
    echo [경고] ffmpeg.exe가 없습니다. 프로젝트 폴더에 복사하세요.
)
echo.

:: ── 1단계: Python 임베디드 다운로드 ─────────
if exist "%PYEXE%" (
    echo [1/4] Python 이미 존재 - 건너뜀
) else (
    echo [1/4] Python %PYVER% 다운로드 중...
    curl -L --progress-bar -o "%ZIPFILE%" "%ZIPURL%"
    if errorlevel 1 (
        echo [오류] 다운로드 실패. 인터넷 연결을 확인하세요.
        pause & exit /b 1
    )

    echo     압축 해제 중...
    powershell -NoProfile -Command "Expand-Archive -Path '%ZIPFILE%' -DestinationPath '%PYDIR%' -Force"
    del "%ZIPFILE%"

    :: site-packages 활성화 (._pth 에서 #import site → import site)
    powershell -NoProfile -Command ^
        "(Get-Content '%PYDIR%\python312._pth') -replace '^#import site', 'import site' | Set-Content '%PYDIR%\python312._pth'"

    echo [OK] Python 준비 완료
)
echo.

:: ── 2단계: pip 설치 ──────────────────────────
if exist "%PIPEXE%" (
    echo [2/4] pip 이미 존재 - 건너뜀
) else (
    echo [2/4] pip 설치 중...
    curl -L --progress-bar -o "%GETPIP%" "https://bootstrap.pypa.io/get-pip.py"
    if errorlevel 1 (
        echo [오류] get-pip.py 다운로드 실패.
        pause & exit /b 1
    )
    "%PYEXE%" "%GETPIP%" --quiet
    del "%GETPIP%"
    echo [OK] pip 설치 완료
)
echo.

:: ── 3단계: 패키지 설치 ───────────────────────
echo [3/4] 패키지 설치 중... (수 분 소요)
"%PYEXE%" -m pip install -r "%~dp0requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause & exit /b 1
)
echo [OK] 패키지 설치 완료
echo.

:: ── 4단계: Playwright Chromium 설치 ─────────
echo [4/4] Chromium 설치 중... (130MB 내외, 최초 1회)
"%PYEXE%" -m playwright install chromium
if errorlevel 1 (
    echo [오류] Chromium 설치 실패
    pause & exit /b 1
)
echo [OK] Chromium 설치 완료

echo.
echo ============================================
echo  설치 완료! run.bat 으로 실행하세요.
echo ============================================
pause
