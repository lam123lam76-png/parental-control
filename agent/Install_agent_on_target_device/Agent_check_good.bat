@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

:: ==============================================================================
:: 1. Kiem tra va yeu cau quyen Administrator
:: ==============================================================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Dang yeu cau quyen Administrator (UAC)...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%Agent_check_good.exe" (
    "%SCRIPT_DIR%Agent_check_good.exe"
) else if exist "%SCRIPT_DIR%agent_check_good\Agent_check_good.exe" (
    "%SCRIPT_DIR%agent_check_good\Agent_check_good.exe"
) else if exist "%SCRIPT_DIR%agent_check_good\agent_check_good.py" (
    python "%SCRIPT_DIR%agent_check_good\agent_check_good.py"
) else (
    echo [ERROR] Khong tim thay Agent_check_good.exe hoac agent_check_good.py!
    echo Vui long chay build_prod_exe.bat de tao file executable.
)

echo.
pause