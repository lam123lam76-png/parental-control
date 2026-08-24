@echo off
cd /d "%~dp0"

:: Chạy Agent chính qua Watchdog Supervisor (mặc định)
start "" pythonw main.py
