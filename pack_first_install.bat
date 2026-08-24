@echo off
chcp 65001 > nul
echo ============================================================
echo   BAT DAU DONG GOI BO CAI DAT LAN DAU
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "OUTPUT_DIR=%PROJECT_ROOT%update_ver\first_install"
set "ZIP_PATH=%OUTPUT_DIR%\ParentalControl_Setup.zip"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [1/2] Dang nen bo cai dat lan dau...
powershell -NoProfile -Command "Get-ChildItem -Path '%PROJECT_ROOT%' -Exclude @('update_ver', 'manager-web', 'node_modules', '.git', '__pycache__', '.vercel', 'scratch') | Compress-Archive -DestinationPath '%ZIP_PATH%' -Force"

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   THANH CONG: Da tao file cai dat lan dau tai:
    echo   %ZIP_PATH%
    echo ============================================================
) else (
    echo [!] LOI dong goi bo cai dat!
)
pause
