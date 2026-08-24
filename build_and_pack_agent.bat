@echo off
chcp 65001 > nul
echo ============================================================
echo   TUTONG DONG GOI AGENT ZIP PACKAGING (AUTOMATED SERVER BUILD)
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "AGENT_DIR=%PROJECT_ROOT%agent"
set "BACKEND_STORAGE=%PROJECT_ROOT%backend_api\storage\updates"
set "ZIP_PATH=%BACKEND_STORAGE%\agent-update.zip"

if not exist "%BACKEND_STORAGE%" mkdir "%BACKEND_STORAGE%"

echo [1/3] Kiem tra binary executables trong agent\dist...
if not exist "%AGENT_DIR%\dist\ParentalControlAgent.exe" (
    echo     Building ParentalControlAgent.exe...
    cd /d "%AGENT_DIR%"
    python -m PyInstaller --noconsole --onefile --name="ParentalControlAgent" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="win32crypt" --hidden-import="mss" --hidden-import="PIL" --hidden-import="websocket" main.py
)

if not exist "%AGENT_DIR%\dist\ParentalControlWatchdog.exe" (
    echo     Building ParentalControlWatchdog.exe...
    cd /d "%AGENT_DIR%"
    python -m PyInstaller --noconsole --onefile --name="ParentalControlWatchdog" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="psutil" protection/watchdog.py
)

echo [2/3] Dong goi nen Zip sang storage\updates\agent-update.zip...
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"

powershell -NoProfile -Command "Compress-Archive -Path '%AGENT_DIR%\dist\*', '%AGENT_DIR%\*.py', '%AGENT_DIR%\communication', '%AGENT_DIR%\enforcement', '%AGENT_DIR%\local_store', '%AGENT_DIR%\protection', '%AGENT_DIR%\utils' -DestinationPath '%ZIP_PATH%' -Force"

echo [3/3] Dong bo binary sang D:\Test va C:\Test...
if not exist "D:\Test" mkdir "D:\Test"
if not exist "C:\Test" mkdir "C:\Test"

copy /y "%AGENT_DIR%\dist\ParentalControlAgent.exe" "D:\Test\ParentalControlAgent.exe" >nul
copy /y "%AGENT_DIR%\dist\ParentalControlWatchdog.exe" "D:\Test\ParentalControlWatchdog.exe" >nul
copy /y "%AGENT_DIR%\dist\ParentalControlAgent.exe" "C:\Test\ParentalControlAgent.exe" >nul
copy /y "%AGENT_DIR%\dist\ParentalControlWatchdog.exe" "C:\Test\ParentalControlWatchdog.exe" >nul

echo.
echo ============================================================
echo   DONG GOI FILE ZIP THANH CONG: %ZIP_PATH%
echo ============================================================
exit /b 0
