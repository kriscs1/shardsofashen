@echo off
rem One click after changing the game (maps, scripts, sprites, data, code): saves the changes and sends them to
rem GitHub. GitHub builds the new server image (a few minutes) and the server PC picks it up by itself.
title Dragon Sword: publish an update
cd /d "%~dp0"
git remote get-url origin >nul 2>&1 || (
    echo This folder isn't linked to GitHub yet: run "Link GitHub.bat" first.
    goto :end
)
git add -A || goto :failed
git diff --cached --quiet && (
    echo Nothing has changed since the last update.
    goto :push
)
git status --short
echo.
set "MSG="
set /p "MSG=What did you change? (Enter for "Game changes"): "
if not defined MSG set "MSG=Game changes"
git commit -q -m "%MSG%" || goto :failed
:push
echo Sending to GitHub...
git push origin HEAD:main || goto :failed
echo.
echo Sent. GitHub is building the new version (see the repository's Actions tab); the server PC
echo updates itself a few minutes after that build finishes.
goto :end
:failed
echo.
echo That didn't work (see above).
:end
echo.
pause
