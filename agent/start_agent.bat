@echo off
cd /d "%~dp0"

:: Chạy Watchdog (ẩn)
start "" pythonw watchdog.py

:: Chạy Agent chính (ẩn)
start "" pythonw main.py