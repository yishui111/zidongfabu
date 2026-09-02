@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo Checking Python ...
set "PYEXE="
if exist "runtime\python.exe" (
    set "PYEXE=runtime\python.exe"
    goto py_ok
)
where python >nul 2>nul
if not errorlevel 1 (
    set "PYEXE=python"
    goto py_ok
)
echo Python not found.
echo   Install Python 3.12+ and add it to PATH, then rerun.
exit /b 1

:py_ok
echo   Python: %PYEXE%
echo Checking dependencies ...
"%PYEXE%" -c "import requests, yaml" >nul 2>&1
if errorlevel 1 (
    if exist "runtime\python.exe" (
        echo Runtime dependencies incomplete, run install.bat first.
    ) else (
        echo Python dependencies missing. Run: pip install -r requirements.txt
    )
    exit /b 1
)
echo Running offline self-tests (mock API, no real account needed) ...
"%PYEXE%" scripts\run_tests.py
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo All tests passed.
) else (
    echo Tests failed with exit code %RC%.
)
endlocal & exit /b %RC%
