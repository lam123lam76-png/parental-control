@echo off
chcp 65001 > nul
color 0A
title RESTART PARENTAL CONTROL SERVER SYSTEM

echo.
echo ============================================================
echo   KHOI DONG LAI TOAN BO HE THONG SERVER (AN TOAN)
echo ============================================================
echo.

echo [1] Dang dung tat ca service server cu...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.CommandLine -like '*server_tray_app.py*' -or $_.CommandLine -like '*uvicorn*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: Free port 8000
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

timeout /t 2 /nobreak >nul

echo [2] Bat lai System Tray App (v3.0 Self-Healing)...
cd /d "%~dp0"
start "" pythonw "%~dp0server_tray_app.py"

echo [3] Dang khoi dong va kiem tra ket noi (5 giay)...
timeout /t 5 /nobreak >nul

python -c "import requests; r = requests.get('http://127.0.0.1:8000/api/devices'); print('[OK] Server da hoat dong binh thuong! Devices:', len(r.json().get('data', {}).get('devices', [])))" 2>nul || echo [DANG KHOI DONG] Server dang bat len trong ngam, vui long doi vai giay...

echo.
echo ============================================================
echo   HOAN TAT RESTART! Server dang chay ngam trong System Tray.
echo ============================================================
timeout /t 3 /nobreak
exit /b 0
