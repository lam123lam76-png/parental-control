@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

:: ==============================================================================
:: 1. Kiem tra va yeu cau quyen Administrator
:: ==============================================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Dang yeu cau quyen Administrator (UAC)...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

echo ==============================================================================
echo       CAI DAT PARENTAL CONTROL AGENT TREN MAY DICH (MANUAL INSTALLATION)
echo ==============================================================================
echo.

set "TARGET_DIR=C:\ProgramData\ParentalControl"
set "SOURCE_DIR=%~dp0"

:: ==============================================================================
:: 2. Tao thu muc cai dat chuan
:: ==============================================================================
if not exist "%TARGET_DIR%" (
    echo [1/6] Dang tao thu muc cai dat: %TARGET_DIR%...
    mkdir "%TARGET_DIR%" >nul 2>&1
) else (
    echo [1/6] Thu muc cai dat da ton tai: %TARGET_DIR%
)

:: ==============================================================================
:: 3. Dung cac tien trinh cu dang chay
:: ==============================================================================
echo [2/6] Dang dung cac tien trinh cu (neu co)...
taskkill /F /IM ParentalControlAgent.exe >nul 2>&1
taskkill /F /IM ParentalControlWatchdog.exe >nul 2>&1
taskkill /F /IM Updater.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: ==============================================================================
:: 4. Cau hinh Windows Defender Exclusion (TRUOC KHI COPY)
:: ==============================================================================
echo [3/6] Cau hinh Windows Defender bo qua thu muc %TARGET_DIR%...
powershell -Command "Add-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1
powershell -Command "Add-MpPreference -ExclusionPath '%SOURCE_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1

:: ==============================================================================
:: 5. Sao chep cac file Executable va Script
:: ==============================================================================
echo [4/6] Dang sao chep cac tep tin vao %TARGET_DIR%...

if exist "%SOURCE_DIR%ParentalControlAgent.exe" (
    copy /Y "%SOURCE_DIR%ParentalControlAgent.exe" "%TARGET_DIR%\ParentalControlAgent.exe" >nul
    echo       + Da sao chep ParentalControlAgent.exe
) else (
    echo       [CANH BAO] Khong tim thay ParentalControlAgent.exe trong thu muc goc!
)

if exist "%SOURCE_DIR%Updater.exe" (
    copy /Y "%SOURCE_DIR%Updater.exe" "%TARGET_DIR%\Updater.exe" >nul
    echo       + Da sao chep Updater.exe
) else (
    echo       [CANH BAO] Khong tim thay Updater.exe trong thu muc goc!
)

if exist "%SOURCE_DIR%ParentalControlWatchdog.exe" (
    copy /Y "%SOURCE_DIR%ParentalControlWatchdog.exe" "%TARGET_DIR%\ParentalControlWatchdog.exe" >nul
    echo       + Da sao chep ParentalControlWatchdog.exe
) else (
    echo       [CANH BAO] Khong tim thay ParentalControlWatchdog.exe trong thu muc goc!
)

if exist "%SOURCE_DIR%Agent_check_good.exe" (
    copy /Y "%SOURCE_DIR%Agent_check_good.exe" "%TARGET_DIR%\Agent_check_good.exe" >nul
    echo       + Da sao chep Agent_check_good.exe
)

if exist "%SOURCE_DIR%Agent_check_good.bat" (
    copy /Y "%SOURCE_DIR%Agent_check_good.bat" "%TARGET_DIR%\Agent_check_good.bat" >nul
    echo       + Da sao chep Agent_check_good.bat
)

if exist "%SOURCE_DIR%.env" (
    copy /Y "%SOURCE_DIR%.env" "%TARGET_DIR%\.env" >nul
    echo       + Da sao chep .env
)

:: Sao chep chinh file cai dat vao thu muc dich
copy /Y "%~dpnx0" "%TARGET_DIR%\Install_Parental_Control.bat" >nul
echo       + Da luu tru Install_Parental_Control.bat tai thu muc dich

:: ==============================================================================
:: 5. Cau hinh Windows Defender Exclusion
:: ==============================================================================
echo [4/6] Cau hinh Windows Defender bo qua thu muc %TARGET_DIR%...
powershell -Command "Add-MpPreference -ExclusionPath '%TARGET_DIR%' -ErrorAction SilentlyContinue" >nul 2>&1

:: ==============================================================================
:: 6. Dang ky tu khoi dong cung Windows (Run Registry & Scheduled Task)
:: ==============================================================================
echo [5/6] Dang ky tu khoi dong cung Windows...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /t REG_SZ /d "\"%TARGET_DIR%\ParentalControlAgent.exe\"" /f >nul 2>&1
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlWatchdog" /t REG_SZ /d "\"%TARGET_DIR%\ParentalControlWatchdog.exe\"" /f >nul 2>&1

:: ==============================================================================
:: 7. Khoi chay Agent va Kiem Tra Suc Khoe
:: ==============================================================================
echo [6/6] Dang khoi dong ParentalControlAgent va Watchdog...
cd /d "%TARGET_DIR%"
if exist "ParentalControlWatchdog.exe" (
    start "" "%TARGET_DIR%\ParentalControlWatchdog.exe"
)
if exist "ParentalControlAgent.exe" (
    start "" "%TARGET_DIR%\ParentalControlAgent.exe"
)

timeout /t 2 /nobreak >nul

echo.
echo ==============================================================================
echo [SUCCESS] DA CAI DAT VA KHOI DONG AGENT THANH CONG!
echo Dang chay chan doan kiem tra trang thai he thong (Diagnostic)...
echo ==============================================================================
echo.

if exist "%TARGET_DIR%\Agent_check_good.exe" (
    "%TARGET_DIR%\Agent_check_good.exe"
)

echo.
echo ==============================================================================
echo Hoan tat! Agent da hoat dong va tu dong ket noi toi may chu.
echo ==============================================================================
echo.
pause