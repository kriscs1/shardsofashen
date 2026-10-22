@echo off
rem Makes sure Docker Desktop is running (starts it and waits, if it isn't). Used by the other .bat files.
docker info >nul 2>&1 && exit /b 0
echo Starting Docker Desktop...
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
for /l %%i in (1,1,90) do (
    timeout /t 2 /nobreak >nul
    docker info >nul 2>&1 && exit /b 0
)
echo Docker Desktop didn't start. Is it installed? https://www.docker.com/products/docker-desktop/
exit /b 1
