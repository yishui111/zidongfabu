@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/2] Asking scheduler to stop gracefully ...
if not exist "data" mkdir data
type nul > "data\stop.flag"

if not exist "data\scheduler.pid" goto no_scheduler
set /p SCHED_PID=<data\scheduler.pid
echo Waiting for scheduler to exit (max 120s) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(120); while((Get-Date) -lt $deadline){ if(-not (Test-Path 'data\scheduler.pid')){ exit 0 }; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 (
    echo Timeout, force killing scheduler ...
    taskkill /PID %SCHED_PID% /F >nul 2>&1
)
goto sched_done

:no_scheduler
echo Scheduler is not running.

:sched_done
echo [2/2] Closing MatrixMedia ...
taskkill /IM matrixmedia.exe /F >nul 2>&1
del "data\stop.flag" >nul 2>&1
echo All stopped. Login state is kept on disk; next start does not need re-login.
endlocal
