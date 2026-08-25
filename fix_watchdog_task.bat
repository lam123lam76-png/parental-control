@echo off
REM ============================================================
REM  FIX Watchdog Scheduled Task - run as Administrator
REM  (right-click -> Run as administrator)
REM ============================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix_watchdog_task.ps1"
