@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==============================================================================
echo  DONG GOI PARENTAL CONTROL AGENT EXECUTABLE (CHO MAY CHU NOI BO MAY NAY)
echo ==============================================================================

set SERVER_URL=%1

if "%SERVER_URL%"=="" set SERVER_URL=https://nguyentruclam.io.vn

echo.
echo  Máy chủ kết nối: %SERVER_URL%
echo.

echo [1/3] Đang cập nhật file cấu hình agent\.env...
echo BACKEND_URL=%SERVER_URL%> .env
echo WS_URL=%SERVER_URL%>> .env

echo [2/3] Dang kiem tra va cai dat PyInstaller...
python -m pip install --upgrade pyinstaller psutil websocket-client pillow mss pywin32 passlib requests

echo [3/3] Dang biendich ParentalControlAgent.exe (Noconsole Mode)...
python -m PyInstaller --noconsole --onefile --name="ParentalControlAgent" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="win32crypt" --hidden-import="mss" --hidden-import="PIL" --hidden-import="websocket" --clean main.py

if exist dist\ParentalControlAgent.exe (
    echo ==============================================================================
    echo  DA DONG GOI FILE EXECUTABLE THANH CONG!
    echo  Binary: agent\dist\ParentalControlAgent.exe
    echo  Ket noi toi May chu hien tai: %SERVER_IP%:8000
    echo ==============================================================================
    echo  Copy file ParentalControlAgent.exe va file Install_Agent_1Click.bat 
    echo  sang may em trai va chay Install_Agent_1Click.bat la xong!
    echo ==============================================================================
) else (
    echo [ERROR] Dong goi file .exe khong thanh cong. Vui long kiem tra lai!
)
pause
