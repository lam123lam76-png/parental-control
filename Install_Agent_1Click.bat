@echo off
setlocal enabledelayedexpansion

echo ==============================================================================
echo BỘ CÀI ĐẶT 1-CLICK PARENTAL CONTROL AGENT TRÊN MÁY EM TRAI
echo ==============================================================================

set TARGET_DIR=%APPDATA%\ParentalControl
set EXE_NAME=ParentalControlAgent.exe

echo [1/3] Đang khởi tạo thư mục hệ thống bảo mật %TARGET_DIR%...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [2/3] Đang sao chép file thực thi Agent...
if exist "%~dp0agent\dist\%EXE_NAME%" (
    copy /Y "%~dp0agent\dist\%EXE_NAME%" "%TARGET_DIR%\%EXE_NAME%" >nul
) else if exist "%~dp0%EXE_NAME%" (
    copy /Y "%~dp0%EXE_NAME%" "%TARGET_DIR%\%EXE_NAME%" >nul
) else (
    echo [ERROR] Không tìm thấy file %EXE_NAME%. Vui lòng chạy build_prod_exe.bat trước!
    pause
    exit /b 1
)

echo [3/3] Đăng ký tự động khởi động cùng Windows (Registry Autostart)...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlAgent" /t REG_SZ /d "\"%TARGET_DIR%\%EXE_NAME%\"" /f >nul

echo [4/4] Đang kích hoạt Agent chạy ngầm...
start "" "%TARGET_DIR%\%EXE_NAME%"

echo ==============================================================================
echo ✅ CÀI ĐẶT VÀ BẬT AGENT TRÊN MÁY EM TRAI THÀNH CÔNG!
echo Agent đang tự động chạy ngầm và được bảo vệ bởi Dual Process Watchdog.
echo ==============================================================================
pause
