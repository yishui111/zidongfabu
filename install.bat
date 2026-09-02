@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/4] Deploying embedded Python ...
if exist "runtime\python.exe" goto runtime_ok
if not exist "cache\python-3.12.10-embed-amd64.zip" (
    echo Missing cache\python-3.12.10-embed-amd64.zip
    echo   Download the Python 3.12 embedded package from python.org,
    echo   save it as cache\python-3.12.10-embed-amd64.zip, then rerun.
    echo   Or simply install Python 3.12+ and run start.bat directly.
    echo   Full steps: see DEPLOY.md.
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath 'cache\python-3.12.10-embed-amd64.zip' -DestinationPath 'runtime' -Force"
if errorlevel 1 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-ChildItem 'runtime\python3*._pth' | Select-Object -First 1; if($p){ $c=Get-Content -LiteralPath $p.FullName -Encoding ASCII; $c=$c -replace '^#import site','import site'; Set-Content -LiteralPath $p.FullName -Value $c -Encoding ASCII }"

:runtime_ok
echo [2/4] Installing Python dependencies from offline cache ...
if exist "runtime\Lib\site-packages\requests" goto deps_ok
if not exist "cache\get-pip.py" (
    echo Missing cache\get-pip.py
    echo   Download get-pip.py from https://bootstrap.pypa.io/get-pip.py
    echo   and save it as cache\get-pip.py, then rerun.
    exit /b 1
)
"runtime\python.exe" cache\get-pip.py --no-warn-script-location
if errorlevel 1 exit /b 1
"runtime\python.exe" -m pip install --no-index --find-links wheels -r requirements.txt --no-warn-script-location
if errorlevel 1 exit /b 1

:deps_ok
echo [3/4] Installing MatrixMedia ...
set "MM_EXE="
for %%i in ("%LOCALAPPDATA%\Programs\matrixmedia\matrixmedia.exe" "%ProgramFiles%\matrixmedia\matrixmedia.exe" "%ProgramFiles(x86)%\matrixmedia\matrixmedia.exe") do (
    if exist "%%~i" set "MM_EXE=%%~i"
)
if not defined MM_EXE (
    for %%i in ("matrixmedia\MatrixMedia-*.exe") do (
        if exist "%%~i" (
            echo Installing MatrixMedia silently ...
            "%%~i" /S
        )
    )
)
echo [4/4] Install finished.
endlocal
