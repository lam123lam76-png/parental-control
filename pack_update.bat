@echo off
chcp 65001 > nul
echo ============================================================
echo   BAT DAU DONG GOI VA DAY CODE CAP NHAT AGENT (REMOTE UPDATE)
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "AGENT_DIR=%PROJECT_ROOT%agent"
set "OUTPUT_DIR=%PROJECT_ROOT%update_ver"
set "ZIP_PATH=%OUTPUT_DIR%\agent_update.zip"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo [1/2] Dang nen thu muc Agent...
powershell -NoProfile -Command "Get-ChildItem -Path '%AGENT_DIR%' -Exclude @('__pycache__', 'build', 'dist', '*.spec') | Compress-Archive -DestinationPath '%ZIP_PATH%' -Force"

if %errorlevel% equ 0 (
    echo.
    echo [2/2] Dang day file update len Supabase & gui lenh cap nhat tu xa...
    python "%PROJECT_ROOT%push_update.py"
    echo.
    echo ============================================================
    echo   THANH CONG! File da duoc day len Supabase Storage.
    echo   Lenh cap nhat tu xa da duoc gui toi may em trai!
    echo ============================================================
) else (
    echo [!] LOI dong goi file update!
)
pause
