@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "TEMP=%~dp0tmp"
set "TMP=%~dp0tmp"
set "PYTHONUTF8=1"
if not exist "%TEMP%" mkdir "%TEMP%"
echo AI Paper Agent: http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop.
".venv\Scripts\python.exe" -X utf8 -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log
pause
