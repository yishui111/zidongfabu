@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ==================================================
echo  zidongfabu - push to GitHub
echo  This script commits all local changes and pushes
echo  to the configured remote 'origin'.
echo  NOTE: make sure config.yaml contains no real
echo  account phone numbers before pushing (see README).
echo ==================================================

if not exist ".git" (
    echo Initializing git repository ...
    git init
    if errorlevel 1 exit /b 1
    git add -A
    git commit -m "init: multi-platform video auto publish scheduler"
)

git remote -v | findstr /I "origin" >nul
if errorlevel 1 (
    set /p REPO="Enter GitHub repo URL (e.g. https://github.com/user/repo.git): "
    if "%REPO%"=="" exit /b 1
    git remote add origin "%REPO%"
    if errorlevel 1 exit /b 1
)

git add -A
git commit -m "update: scheduler sync" >nul 2>&1
git push -u origin master
if errorlevel 1 git push -u origin main
endlocal
