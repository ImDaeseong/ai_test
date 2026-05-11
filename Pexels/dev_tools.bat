@echo off
setlocal EnableExtensions

cd /d "%~dp0"
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run run.bat first.
    pause
    exit /b 1
)

echo ============================================================
echo Developer tools
echo ============================================================
echo   1. Run tests only
echo   2. Validate data only
echo   3. Generate both formats without opening browser
echo   4. Open latest browser report
echo   5. Show CLI help
echo   6. Clean temporary processed files
echo   7. Clean all generated cache files
echo   8. Exit
echo.
set /p ACTION="Enter choice [1-8]: "

if "%ACTION%"=="1" goto :tests
if "%ACTION%"=="2" goto :validate
if "%ACTION%"=="3" goto :generate
if "%ACTION%"=="4" goto :open
if "%ACTION%"=="5" goto :help
if "%ACTION%"=="6" goto :clean_temp
if "%ACTION%"=="7" goto :clean_all
goto :done

:tests
".venv\Scripts\python.exe" -m pytest
goto :check

:validate
".venv\Scripts\python.exe" scripts\validate_data.py
goto :check

:generate
if not exist "output" (
    echo Creating output folder...
    mkdir "output"
    if errorlevel 1 goto :fail
)
if not exist "output\.gitkeep" type nul > "output\.gitkeep"
".venv\Scripts\python.exe" scripts\generate_from_data.py --data-dir data --report output\index.html --both
goto :check

:open
if not exist "output\index.html" (
    echo ERROR: output\index.html does not exist. Run run.bat first.
    goto :fail
)
start "" "output\index.html"
goto :done

:help
".venv\Scripts\python.exe" -m app.main --help
goto :check

:clean_temp
".venv\Scripts\python.exe" scripts\cleanup_storage.py
goto :check

:clean_all
echo This removes downloaded Pexels videos and API caches too.
set /p CONFIRM="Type YES to continue: "
if not "%CONFIRM%"=="YES" goto :done
".venv\Scripts\python.exe" scripts\cleanup_storage.py --all
goto :check

:check
if errorlevel 1 goto :fail
goto :done

:fail
echo.
echo FAILED: Check the message above.
pause
exit /b 1

:done
echo.
echo Done.
pause
exit /b 0
