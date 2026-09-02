@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/6] Checking Python ...
set "PYEXE="
set "PYWEXE="
if exist "runtime\python.exe" (
    set "PYEXE=runtime\python.exe"
    set "PYWEXE=runtime\pythonw.exe"
    goto python_ok
)
if not exist "cache\python-3.12.10-embed-amd64.zip" goto no_cache
echo Embedded runtime missing, running install.bat ...
call install.bat
if errorlevel 1 exit /b 1
if exist "runtime\python.exe" (
    set "PYEXE=runtime\python.exe"
    set "PYWEXE=runtime\pythonw.exe"
    goto python_ok
)

:no_cache
where python >nul 2>nul
if not errorlevel 1 (
    set "PYEXE=python"
    where pythonw >nul 2>nul
    if not errorlevel 1 (
        set "PYWEXE=pythonw"
    ) else (
        set "PYWEXE=python"
    )
    goto python_ok
)
echo Python not found.
echo   - Install Python 3.12+ and add it to PATH, then rerun, or
echo   - prepare the embedded runtime kit, see DEPLOY.md.
exit /b 1

:python_ok
echo   Python: %PYEXE%

echo [2/6] Checking dependencies ...
if exist "runtime\python.exe" (
    if exist "runtime\Lib\site-packages\requests" goto deps_ok
    echo Runtime dependencies incomplete, running install.bat ...
    call install.bat
    if errorlevel 1 exit /b 1
    goto deps_ok
)
"%PYEXE%" -c "import requests, yaml" >nul 2>&1
if errorlevel 1 (
    echo Python dependencies missing.
    echo   Run: pip install -r requirements.txt
    exit /b 1
)

:deps_ok
echo [3/6] Checking MatrixMedia ...
set "MM_EXE="
for %%i in ("%LOCALAPPDATA%\Programs\matrixmedia\matrixmedia.exe" "%ProgramFiles%\matrixmedia\matrixmedia.exe" "%ProgramFiles(x86)%\matrixmedia\matrixmedia.exe") do (
    if exist "%%~i" set "MM_EXE=%%~i"
)
if not defined MM_EXE (
    for /f "delims=" %%i in ('where matrixmedia 2^>nul') do set "MM_EXE=%%~i"
)
if not defined MM_EXE (
    for %%i in ("matrixmedia\MatrixMedia-*.exe") do (
        if exist "%%~i" (
            echo MatrixMedia not installed, installing silently ...
            "%%~i" /S
        )
    )
    for %%i in ("%LOCALAPPDATA%\Programs\matrixmedia\matrixmedia.exe" "%ProgramFiles%\matrixmedia\matrixmedia.exe") do (
        if exist "%%~i" set "MM_EXE=%%~i"
    )
)
if not defined MM_EXE (
    echo MatrixMedia not found.
    echo   Download the installer from
    echo   https://github.com/hanliang97/MatrixMedia/releases
    echo   and put it into the matrixmedia folder, or install it once manually.
    exit /b 1
)

tasklist /fi "imagename eq matrixmedia.exe" 2>nul | findstr /i "matrixmedia" >nul
if errorlevel 1 (
    echo [4/6] Starting MatrixMedia ...
    start "" "%MM_EXE%"
) else (
    echo [4/6] MatrixMedia already running.
)

echo [5/6] Waiting for MatrixMedia API ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 90;$i++){ try { Invoke-WebRequest -Uri 'http://127.0.0.1:30088/' -TimeoutSec 3 -UseBasicParsing | Out-Null; $ok=$true; break } catch { if($_.Exception.Response){ $ok=$true; break }; Start-Sleep -Seconds 2 } }; if(-not $ok){ Write-Host 'MatrixMedia API not ready. Check the app and port 30088.'; exit 1 }"
if errorlevel 1 exit /b 1

echo [6/6] Starting scheduler in background ...
if exist "data\stop.flag" del "data\stop.flag"
start "" "%PYWEXE%" scheduler\main.py --config config.yaml
echo Waiting for scheduler to start ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 30;$i++){ if(Test-Path 'data\scheduler.pid'){ $ok=$true; break }; Start-Sleep -Seconds 1 }; if(-not $ok){ Write-Host 'Scheduler failed to start. See logs\scheduler.log.'; exit 1 }"
if errorlevel 1 exit /b 1
echo.
echo Scheduler started in background. Log: logs\scheduler.log
echo To stop: run stop.bat
endlocal
