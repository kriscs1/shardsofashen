@echo off
rem Stops the server (everyone's progress is saved first). "Start Server.bat" starts it again.
title Dragon Sword: stop
cd /d "%~dp0"
docker compose stop
echo The server is stopped. (It starts again with "Start Server.bat", or the next time you run that.)
pause
