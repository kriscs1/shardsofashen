@echo off
rem Once: links this folder to your GitHub repository and sends everything there.
rem First make the repository on github.com: + (top right) > New repository > name it (e.g. shardsofashen) >
rem Public or Private > Create (no README). Then run this and paste its address.
title Shards of Ashen: link to GitHub
cd /d "%~dp0"
git remote get-url origin >nul 2>&1 && (
    echo This folder is already linked to:
    git remote get-url origin
    goto :end
)
echo Paste your repository's address (like https://github.com/yourname/shardsofashen.git) and press Enter:
set /p REPO=
if "%REPO%"=="" goto :end
git remote add origin %REPO% || goto :failed
git branch -M main
echo.
echo Sending the game to GitHub (the first time, a browser window may ask you to sign in to GitHub)...
git push -u origin main || goto :failed
echo.
echo Done. GitHub is now building the server image: watch it under the repository's "Actions" tab.
echo From now on, "Publish Update.bat" sends your changes.
goto :end
:failed
echo.
echo That didn't work (see above).
:end
echo.
pause
