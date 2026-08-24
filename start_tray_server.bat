@echo off
chcp 65001 > nul
title Parental Control System Tray App Launcher

cd /d "%~dp0"

echo [1] Dang khoi dong Parental Control Server (System Tray v3.0 Self-Healing)...
start "" pythonw "%~dp0server_tray_app.py"
echo [OK] Server da duoc khoi dong chay ngam thanh cong trong khay he thong!
timeout /t 2 /nobreak > nul
exit /b 0
