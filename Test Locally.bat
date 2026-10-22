@echo off
rem One click: builds the server from these files in Docker and (re)starts it here, at http://localhost:8080,
rem to try changes before publishing them. The test server keeps its own characters, apart from the real one.
title Dragon Sword: test locally
cd /d "%~dp0"
call "%~dp0deploy\server-pc\_docker.bat" || goto :end
echo Building (the first time takes a few minutes; after that only what changed)...
docker compose -f deploy\docker-compose.local.yml up -d --build || goto :failed
echo.
echo The test server is running: http://localhost:8080
start "" http://localhost:8080
goto :end
:failed
echo.
echo That didn't work (see above).
:end
echo.
pause
