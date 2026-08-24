@echo off
setlocal
chcp 65001 > nul

:: Kiem tra quyen Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Dang yeu cau quyen Administrator...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ==============================================================================
echo       GO CAI DAT PARENTAL CONTROL AGENT TREN MAY DICH (UNINSTALLATION)
echo ==============================================================================
echo.

set "TARGET_DIR=C:\ProgramData\ParentalControl"

:: ==============================================================================
:: 2. Dung triet de cac tien trinh Agent & Watchdog
:: ==============================================================================
echo [1/4] Dang dung va tieu diet toan bo tien trinh Agent...
taskkill /F /IM ParentalControlWatchdog.exe >nul 2>&1
taskkill /F /IM ParentalControlAgent.exe >nul 2>&1
taskkill /F /IM Updater.exe >nul 2>&1
taskkill /F /IM Agent_check_good.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: ==============================================================================
:: 3. Xoa bo dang ky khoi dong Run Registry
:: ==============================================================================
echo [2/4] Dang xoa dang ky tu khoi dong cung Windows...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlWatchdog" /f >nul 2>&1

:: ==============================================================================
:: 4. Xoa Windows Defender Exclusion
:: ==============================================================================
echo [3/4] Xoa cau hinh ngoai le Windows Defender...
powershell -Command "Remove-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1

:: ==============================================================================
:: 5. Xoa sach thu muc cai dat C:\ProgramData\ParentalControl va %APPDATA%\ParentalControl
:: ==============================================================================
echo [4/4] Dang xoa thu muc cai dat %TARGET_DIR% va du lieu dang ky cu...
if exist "%TARGET_DIR%" (
    rmdir /S /Q "%TARGET_DIR%" >nul 2>&1
    if exist "%TARGET_DIR%" (
        echo       [CANH BAO] Mot so file dang bi khoa, thu luc xoa lan 2...
        timeout /t 1 /nobreak >nul
        rmdir /S /Q "%TARGET_DIR%" >nul 2>&1
    )
)
if exist "%APPDATA%\ParentalControl" (
    rmdir /S /Q "%APPDATA%\ParentalControl" >nul 2>&1
)
powershell -NoProfile -Command "Get-ChildItem 'C:\Users\*\AppData\Roaming\ParentalControl' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo.
echo ==============================================================================
echo [SUCCESS] DA GO CAI DAT HOAN TOAN PARENTAL CONTROL AGENT KHOI MAY DICH!
echo ==============================================================================
echo.
pause