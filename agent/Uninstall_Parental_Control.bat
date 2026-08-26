@echo off
:: ============================================================
::  PARENTAL CONTROL AGENT - UNINSTALLER (TRIET DE / THOROUGH)
::  Run as administrator to completely remove the Agent.
::  Handles elevated agent/watchdog processes (taskkill alone
::  gets Access denied), both Run keys, all scheduled tasks,
::  Defender exclusions, and all data folders.
:: ============================================================
chcp 65001 > nul
color 0C
title PARENTAL CONTROL AGENT - GO CAI DAT TRIET DE

:: ---- Check Admin Rights ----
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Vui long chuot phai chon 'Run as administrator' de go cai dat!
    pause
    exit /b
)

set "TARGET_DIR=C:\ProgramData\ParentalControl"
set "FLAG_SECRET=PC_WATCHDOG_SAFE_EXIT_a8f3e1b9c2d7"

echo.
echo ============================================================
echo   PARENTAL CONTROL AGENT - GO CAI DAT TRIET DE (UNINSTALL)
echo ============================================================
echo.

:: ---- 1. Block watchdog (correct secret) + kill ALL processes ----
echo [1/6] Dung tien trinh Agent & Watchdog...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>&1
echo %FLAG_SECRET%> "%TARGET_DIR%\shutdown.flag" 2>nul
if exist "%APPDATA%\ParentalControl" echo %FLAG_SECRET%> "%APPDATA%\ParentalControl\shutdown.flag" 2>nul

:: Kill each process 3 ways (taskkill + PowerShell Stop-Process + wmic)
for %%P in (ParentalControlWatchdog ParentalControlAgent Updater ParentalControlAgent_Debug) do (
    taskkill /f /t /im %%P.exe >nul 2>&1
    powershell -NoProfile -Command "Get-Process -Name '%%P' -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1
    wmic process where "name='%%P.exe'" delete >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: ---- 2. Delete all scheduled tasks containing 'ParentalControl' ----
echo [2/6] Xoa cac lich khoi dong tu dong (Task Scheduler)...
powershell -NoProfile -Command "Get-ScheduledTask -TaskName '*ParentalControl*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false" >nul 2>&1
schtasks /delete /tn "WindowsSecurityAgent" /f >nul 2>&1
schtasks /delete /tn "ParentalControlSystem" /f >nul 2>&1
schtasks /delete /tn "ParentalControlAgentTask" /f >nul 2>&1
schtasks /delete /tn "ParentalControlWatchdogTask" /f >nul 2>&1

:: ---- 3. Remove Registry autorun (HKLM + HKCU, Agent + Watchdog) ----
echo [3/6] Xoa dang ky khoi dong cung Windows (Registry)...
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlWatchdog" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlWatchdog" /f >nul 2>&1

:: ---- 4. Remove Windows Defender exclusions (path + process) ----
echo [4/6] Xoa ngoai le Windows Defender...
powershell -NoProfile -Command "Remove-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1
powershell -NoProfile -Command "Remove-MpPreference -ExclusionProcess 'ParentalControlAgent.exe','ParentalControlWatchdog.exe','Updater.exe' -ErrorAction SilentlyContinue" >nul 2>&1

:: ---- 5. Delete all data folders (with retry + PS fallback) ----
echo [5/6] Xoa cac thu muc du lieu...
if exist "%TARGET_DIR%" (
    rmdir /s /q "%TARGET_DIR%" 2>nul
    if exist "%TARGET_DIR%" powershell -NoProfile -Command "Remove-Item -Path '%TARGET_DIR%' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
)
if exist "%APPDATA%\ParentalControl" (
    rmdir /s /q "%APPDATA%\ParentalControl" 2>nul
    if exist "%APPDATA%\ParentalControl" powershell -NoProfile -Command "Remove-Item -Path '%APPDATA%\ParentalControl' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
)
if exist "%LOCALAPPDATA%\ParentalControl" (
    rmdir /s /q "%LOCALAPPDATA%\ParentalControl" 2>nul
    if exist "%LOCALAPPDATA%\ParentalControl" powershell -NoProfile -Command "Remove-Item -Path '%LOCALAPPDATA%\ParentalControl' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
)

:: ---- 6. Verify ----
echo [6/6] Kiem tra ket qua...
set "PROCS_GONE=1"
tasklist | findstr /i "ParentalControl" >nul 2>&1 && set "PROCS_GONE=0"
if "%PROCS_GONE%"=="0" (
    echo   [!] Van con tien trinh ParentalControl dang chay - hay End task trong Task Manager.
) else (
    echo   [OK] Khong con tien trinh ParentalControl.
)
if exist "%TARGET_DIR%" (
    echo   [!] Thu muc %TARGET_DIR% van ton tai (file bi khoa) - xoa thu cong.
) else (
    echo   [OK] Da xoa sach %TARGET_DIR%.
)

echo.
echo ============================================================
echo   DA GO CAI DAT PARENTAL CONTROL AGENT TRIET DE!
echo   Neu muon cai lai: chay C:\Test\AgentInstaller.exe (admin)
echo ============================================================
echo.
pause
