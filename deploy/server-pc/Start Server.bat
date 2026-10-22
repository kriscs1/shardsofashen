@echo off
rem Starts the Dragon Sword server (the first time: signs in to GitHub's registry and downloads it).
rem After this it starts by itself whenever Docker Desktop starts, and updates itself.
title Dragon Sword server
cd /d "%~dp0"
call "%~dp0_docker.bat" || goto :end

if not exist ".env" (
    copy example.env .env >nul
    echo Fill in the settings first: .env is opening in Notepad. Save it, close Notepad, then run this again.
    notepad .env
    goto :end
)

for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if /i "%%a"=="GHCR_USER" set GHCR_USER=%%b
    if /i "%%a"=="GHCR_TOKEN" set GHCR_TOKEN=%%b
)
echo Signing in to GitHub's registry as %GHCR_USER%...
echo %GHCR_TOKEN%| docker login ghcr.io -u %GHCR_USER% --password-stdin || goto :failed

echo Downloading the latest version...
docker compose pull || goto :failed
docker compose up -d --remove-orphans || goto :failed
echo.
echo The server is running. Players connect to:
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /c:"IPv4"') do for /f "tokens=*" %%j in ("%%i") do echo    http://%%j:8080
echo    (and http://localhost:8080 on this PC)
echo It updates itself a few minutes after each "Publish Update", and starts again with Docker Desktop.
goto :end

:failed
echo.
echo Something went wrong (see above). Check the settings in .env, and that Docker Desktop is running.

:end
echo.
pause
