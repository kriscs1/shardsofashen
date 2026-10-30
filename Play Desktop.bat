@echo off
rem The desktop app, from the game folder (pip install -r desktop\requirements.txt the first time)
cd /d "%~dp0"
python desktop\app.py
