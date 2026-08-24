@echo off
:: Thêm Agent vào Windows Task Scheduler với quyền cao nhất (Highest Privileges)
echo Dang dang ky Parental Control Agent vao Task Scheduler...

schtasks /create /tn "ParentalControlAgent" /tr "\"%~dp0start_agent.bat\"" /sc onlogon /rl highest /f

if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo [OK] Da dang ky thanh cong Task "ParentalControlAgent"!
    echo Agent se tu dong khoi dong ngam moi khi Windows dang nhập.
    echo ========================================================
) else (
    echo ========================================================
    echo [LỖI] Vui long nhap phai vao file nay va chon "Run as Administrator".
    echo ========================================================
)
pause
