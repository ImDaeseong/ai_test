@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONUTF8=1

echo.
echo ================================================================
echo   STEP 1/2  --  create-all
echo ================================================================
python main.py create-all --input-dir input --force
if errorlevel 1 goto :create_error

echo.
echo ================================================================
echo   STEP 2/2  --  summarize-all
echo ================================================================
python main.py summarize-all --input-dir input --output-dir output
if errorlevel 1 (
    echo.
    echo [WARNING] Some songs failed validation. Check output above.
)

echo.
pause
exit /b 0

:create_error
echo.
echo [ERROR] create-all failed.
pause
exit /b 1
