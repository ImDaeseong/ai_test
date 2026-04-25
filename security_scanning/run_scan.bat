@echo off
setlocal

echo ============================================================
echo  DefenseScan - Full Demo Run
echo ============================================================
echo.

:: ---- Web scan ----
echo [1/3] Web scan : https://naver.com
echo ------------------------------------------------------------
python main.py --web https://naver.com
echo.

:: ---- System scan ----
echo [2/3] System scan (Windows)
echo ------------------------------------------------------------
python main.py --system
echo.

:: ---- Help ----
echo [3/3] Help
echo ------------------------------------------------------------
python main.py --help
echo.

echo ============================================================
echo  Done.
echo ============================================================
pause
