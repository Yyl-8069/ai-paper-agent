@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "TEMP=%~dp0tmp"
set "TMP=%~dp0tmp"
set "UV_CACHE_DIR=%~dp0.cache\uv"
if not exist "%TEMP%" mkdir "%TEMP%"
".venv\Scripts\python.exe" -X utf8 -m app.cli %*
if errorlevel 1 pause
