@echo off
rem Gets the newest version at once (instead of waiting for the automatic check) and restarts the game with it.
rem Everyone's progress is kept. Players are disconnected for a moment and log in again.
title Dragon Sword: update now
cd /d "%~dp0"
call "%~dp0_docker.bat" || goto :end
docker compose pull game && docker compose up -d game
echo.
docker compose ps
:end
echo.
pause
