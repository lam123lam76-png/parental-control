@echo off
:: PARENTAL CONTROL AGENT - UNINSTALLER SCRIPT
:: Run as administrator to cleanly remove Agent from system
chcp 65001 > nul
color 0C
title WINDOWS SECURITY COMPONENT UNINSTALLER

:: Check Admin Rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Vui long chuot phai chon 'Run as administrator' de go cai dat!
    pause
    exit /b
)

set TARGET_DIR=C:\ProgramData\ParentalControl

echo.
echo ============================================================
echo   PARENTAL CONTROL AGENT - GO CAI DAT (UNINSTALL)
echo ============================================================
echo.

:: 1. Tạo shutdown flag để Watchdog dừng hợp lệ
echo [1/5] Dang dung cac tien trinh Agent & Watchdog...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
echo PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7 > "%TARGET_DIR%\shutdown.flag" 2>nul
if exist "%APPDATA%\ParentalControl" echo PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7 > "%APPDATA%\ParentalControl\shutdown.flag" 2>nul

taskkill /f /t /im ParentalControlWatchdog.exe >nul 2>&1
taskkill /f /t /im ParentalControlAgent.exe >nul 2>&1
taskkill /f /t /im ParentalControlAgent_Debug.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2. Xóa các Task Scheduler
echo [2/5] Xoa cac lich khoi dong tu dong (Task Scheduler)...
schtasks /delete /tn "WindowsSecurityAgent" /f >nul 2>&1
schtasks /delete /tn "ParentalControlSystem" /f >nul 2>&1
schtasks /delete /tn "ParentalControlAgentTask" /f >nul 2>&1
schtasks /delete /tn "ParentalControlWatchdogTask" /f >nul 2>&1

:: 3. Xóa Registry Autorun
echo [3/5] Xoa dang ky Khoi dong cung Windows (Registry)...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /f >nul 2>&1

:: 4. Xóa Ngoại lệ Defender & Thư mục chương trình
echo [4/5] Xoa thu muc chuong trinh & ngoai le Windows Defender...
powershell -NoProfile -Command "Remove-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1
if exist "%TARGET_DIR%" rmdir /s /q "%TARGET_DIR%" >nul 2>&1

:: 5. Xóa dữ liệu credentials / local DB (AppData)
echo [5/5] Xoa du lieu va Token xac thuc local (%APPDATA%\ParentalControl)...
if exist "%APPDATA%\ParentalControl" rmdir /s /q "%APPDATA%\ParentalControl" >nul 2>&1

echo.
echo ============================================================
echo   DA GO CAI DAT PARENTAL CONTROL AGENT HOAN TAT!
echo   Thiet bi da duoc lam sach va tro ve trang thai ban dau.
echo ============================================================
echo.
pause
