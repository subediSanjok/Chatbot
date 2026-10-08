@echo off
title Starting Chatbot...
cd /d "%~dp0"

:: 1. Check if g4f server daemon is running on port 1337
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:1337/v1/models' -UseBasicParsing -TimeoutSec 1; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
    echo Starting g4f AI background server...
    start /B python -m g4f --port 1337
    timeout /t 2 /nobreak >nul
)

:: 2. Launch Chatbot Desktop GUI
start pythonw g4f_global_assistant.py
exit
