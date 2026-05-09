@echo off
chcp 65001 >nul
cd /d %~dp0

:: ============================================================
::  아래 두 줄을 수정하고 실행하세요
:: ============================================================
set SONG_TITLE=노래 제목
set ARTIST_NAME=아티스트명
:: ============================================================

echo ========================================
echo  Lyric Video Generator
echo  Title : %SONG_TITLE%
echo  Artist: %ARTIST_NAME%
echo ========================================
echo.

echo [CLEAN] output 폴더 초기화 중...
if exist output (
    rd /s /q output
)
mkdir output
mkdir output\logs
echo [CLEAN] 완료
echo.

echo [1/2] 파이프라인 실행 중...
call npm run lyric-video -- --clean --title "%SONG_TITLE%" --artist "%ARTIST_NAME%"
if %errorlevel% neq 0 (
    echo.
    echo [FAILED] 파이프라인 실패. 로그 확인: output\logs\pipeline.log
    exit /b 1
)

echo.
echo [2/2] 출력 검증 중...
call npm run validate:media
if %errorlevel% neq 0 (
    echo.
    echo [FAILED] 검증 실패.
    exit /b 1
)

echo.
echo ========================================
echo  완료. 출력 파일: output\lyric_video.mp4
echo ========================================
