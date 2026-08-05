@echo off
chcp 65001 >nul
title SYSTEM DIAGNOSTIC TOOL - PARENTAL CONTROL AGENT
cls

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check_Parental_Control_Status.ps1"

echo.
echo =====================================================================
echo    BAO CAO DA DUOC HIEN THI TREN MAN HINH. 
echo =====================================================================
echo.
pause
