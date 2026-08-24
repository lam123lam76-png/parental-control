@echo off
echo Dang gop/xoa Task ParentalControlAgent...

schtasks /delete /tn "ParentalControlAgent" /f

if %ERRORLEVEL% EQU 0 (
    echo [OK] Da xoa thanh cong Task!
) else (
    echo [LOI] Vui long chay voi quyen Administrator.
)
pause
