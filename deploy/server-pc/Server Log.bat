@echo off
rem What the server and the updater are doing (who logged in, updates). Close the window to stop watching.
title Dragon Sword: log
cd /d "%~dp0"
docker compose logs --tail 60 -f
