@echo off
rem One click: builds the server from these files in Docker and (re)starts it here, at http://localhost:8484,
rem to try changes before publishing them. The test server keeps its own characters, apart from the real one.
title Dragon Sword: test locally
cd /d "%~dp0"
docker info >nul 2>&1 || (
    echo Starting Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    for /l %%i in (1,1,90) do (
        timeout /t 2 /nobreak >nul
        docker info >nul 2>&1 && goto :ready
    )
    echo Docker Desktop didn't start. Is it installed? https://www.docker.com/products/docker-desktop/
    goto :end
)
:ready
rem (the version on the login screen: the commit count, commit and date, from git)
set /p DS_BASE=<VERSION
for /f %%v in ('git rev-list --count HEAD 2^>nul') do set DS_BUILD=%%v
for /f %%v in ('git rev-parse --short HEAD 2^>nul') do set DS_COMMIT=%%v
for /f %%v in ('git log -1 --format^=%%cs 2^>nul') do set DS_BUILD_DATE=%%v
echo Building version %DS_BASE%.%DS_BUILD% (the first time takes a few minutes; after that only what changed)...
docker compose -f deploy\docker-compose.local.yml up -d --build || goto :failed
echo.
echo The test server is running: http://localhost:8484
start "" http://localhost:8484
goto :end
:failed
echo.
echo That didn't work (see above).
:end
echo.
pause
