@echo off
chcp 65001 >nul
echo Validating output\lyric_video.mp4 ...
echo.
call npm run validate:media
