@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ==============================================================================
echo   CHƯƠNG TRÌNH ĐÓNG GÓI PARENTAL CONTROL AGENT EXECUTABLE & INSTALL KIT
echo ==============================================================================

set VPS_DOMAIN=%~1
if "%VPS_DOMAIN%"=="" (
    set /p VPS_DOMAIN=Nhap IP hoac Domain VPS cua ban: 
)

if "%VPS_DOMAIN%"=="" (
    echo [ERROR] IP/Domain VPS khong duoc de trong!
    exit /b 1
)

:: Strip http:// and https:// and trailing slash if user mistakenly inputs them
set VPS_DOMAIN=%VPS_DOMAIN:http://=%
set VPS_DOMAIN=%VPS_DOMAIN:https://=%
if "%VPS_DOMAIN:~-1%"=="/" set VPS_DOMAIN=%VPS_DOMAIN:~0,-1%

echo.
echo [1/5] Dang cap nhat cau hinh VPS Domain: %VPS_DOMAIN%...
echo BACKEND_URL=https://%VPS_DOMAIN%> .env
echo WS_URL=wss://%VPS_DOMAIN%>> .env
echo SERVER_URL=https://%VPS_DOMAIN%>> .env

echo [2/5] Dang kiem tra va cai dat PyInstaller / Dependencies...
python -m pip install --upgrade pyinstaller psutil websocket-client pillow mss pywin32 passlib requests >nul 2>&1

python -c "import sys, os, shutil; dlls = os.path.join(sys.prefix, 'DLLs'); shutil.copy2(os.path.join(dlls, 'sqlite3.dll'), 'sqlite3.dll'); shutil.copy2(os.path.join(dlls, '_sqlite3.pyd'), '_sqlite3.pyd')"

echo [3/5] Dang bien dich ParentalControlAgent.exe (Noconsole Mode)...
python -m PyInstaller --noconsole --onefile --name="ParentalControlAgent" --add-binary="sqlite3.dll;." --add-binary="_sqlite3.pyd;." --collect-all="sqlite3" --hidden-import="sqlite3" --hidden-import="_sqlite3" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="win32crypt" --hidden-import="mss" --hidden-import="PIL" --hidden-import="websocket" --clean main.py

echo [4/5] Dang bien dich Updater, Watchdog va Agent_check_good...
python -m PyInstaller --noconsole --onefile --name="Updater" --clean updater_main.py
python -m PyInstaller --noconsole --onefile --name="ParentalControlWatchdog" --clean protection\watchdog.py
python -m PyInstaller --console --onefile --name="Agent_check_good" --add-binary="sqlite3.dll;." --add-binary="_sqlite3.pyd;." --collect-all="sqlite3" --clean Install_agent_on_target_device\agent_check_good\agent_check_good.py

echo.
echo [5/5] Dang xuat va dong bo vao thu muc Install_agent_on_target_device...
if not exist "Install_agent_on_target_device" mkdir "Install_agent_on_target_device"
if not exist "Install_agent_on_target_device\agent_check_good" mkdir "Install_agent_on_target_device\agent_check_good"

if exist dist\ParentalControlAgent.exe (
    copy /Y dist\ParentalControlAgent.exe Install_agent_on_target_device\ParentalControlAgent.exe >nul
    copy /Y dist\Updater.exe Install_agent_on_target_device\Updater.exe >nul
    copy /Y dist\ParentalControlWatchdog.exe Install_agent_on_target_device\ParentalControlWatchdog.exe >nul
    copy /Y dist\Agent_check_good.exe Install_agent_on_target_device\Agent_check_good.exe >nul
    copy /Y dist\Agent_check_good.exe Install_agent_on_target_device\agent_check_good\Agent_check_good.exe >nul
    copy /Y .env Install_agent_on_target_device\.env >nul

    echo ==============================================================================
    echo [SUCCESS] DA XUAT VA CAP NHAT BO CAI DAT THU CONG THANH CONG!
    echo Thu muc chua file: %CD%\Install_agent_on_target_device
    echo.
    echo Danh sach file trong bo cai dat:
    echo   1. ParentalControlAgent.exe
    echo   2. Updater.exe
    echo   3. ParentalControlWatchdog.exe
    echo   4. Install_Parental_Control.bat - Chay de cai dat vao C:\ProgramData\ParentalControl
    echo   5. Uninstall_Parental_Control.bat - Chay de go cai dat hoan toan
    echo   6. Agent_check_good.bat - Chay de kiem tra toan bo tinh nang va xuat log debug
    echo   7. Agent_check_good.exe - Executable chan doan
    echo ==============================================================================

    REM Dong thoi duy tri dong goi file ZIP de phuc vu tinh nang cap nhat tu xa
    set "UPDATES_DIR=..\backend_api\storage\updates"
    if not exist "!UPDATES_DIR!" mkdir "!UPDATES_DIR!"
    powershell -NoProfile -Command "Compress-Archive -Path 'dist\ParentalControlAgent.exe', 'dist\Updater.exe', 'dist\ParentalControlWatchdog.exe' -DestinationPath '!UPDATES_DIR!\agent-update.zip' -Force" >nul 2>&1
    echo [INFO] Da cap nhat luon file ZIP tu xa: backend_api\storage\updates\agent-update.zip
) else (
    echo [ERROR] Bien dich file executable khong thanh cong. Vui long kiem tra lai log PyInstaller!
)
echo.