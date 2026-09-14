@echo off
chcp 65001 > nul
echo ============================================================
echo   BUILD + PACK AGENT (REBUILD + COPY TO C:\Test)
echo ============================================================
echo.
echo   Build ra dist\, roi copy sang C:\Test va D:\Test de
echo   Install_Parental_Control.bat (chay admin) chuyen vao
echo   C:\ProgramData\ParentalControl.
echo.

set "PROJECT_ROOT=%~dp0"
set "AGENT_DIR=%PROJECT_ROOT%agent"
set "INSTALLER_DIR=%PROJECT_ROOT%agent_installer"
set "BACKEND_STORAGE=%PROJECT_ROOT%backend_api\storage\updates"
set "ZIP_PATH=%BACKEND_STORAGE%\agent-update.zip"

rem --- Nho TANG so version moi lan build (v0004, v0005, ...) ---
set "AGENT_VERSION=v0032"

if not exist "%BACKEND_STORAGE%" mkdir "%BACKEND_STORAGE%"

echo [1/4] Building executables (full rebuild)...
echo     - Xoa build cu (dist\build)...
if exist "%AGENT_DIR%\dist" rmdir /s /q "%AGENT_DIR%\dist" 2>nul
if exist "%AGENT_DIR%\build" rmdir /s /q "%AGENT_DIR%\build" 2>nul
del /f /q "%AGENT_DIR%\ParentalControlAgent.spec" 2>nul
del /f /q "%AGENT_DIR%\ParentalControlWatchdog.spec" 2>nul
del /f /q "%AGENT_DIR%\Updater.spec" 2>nul

echo     - Building ParentalControlAgent.exe ...
cd /d "%AGENT_DIR%"
python -m PyInstaller --noconsole --onefile --name="ParentalControlAgent" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="win32crypt" --hidden-import="win32api" --hidden-import="win32con" --hidden-import="mss" --hidden-import="PIL" --hidden-import="websocket" main.py
if errorlevel 1 (
    echo     [ERROR] Agent build FAILED - xem output o tren.
    goto :failed
)

echo     - Building ParentalControlWatchdog.exe ...
python -m PyInstaller --noconsole --onefile --name="ParentalControlWatchdog" --hidden-import="win32gui" --hidden-import="win32process" --hidden-import="psutil" protection\watchdog.py
if errorlevel 1 (
    echo     [ERROR] Watchdog build FAILED - xem output o tren.
    goto :failed
)

echo     - Building Updater.exe ...
python -m PyInstaller --noconsole --onefile --name="Updater" updater_main.py
if errorlevel 1 (
    echo     [ERROR] Updater build FAILED - xem output o tren.
    goto :failed
)

echo [2/4] Building AgentInstaller.exe ...
if exist "%INSTALLER_DIR%\dist" rmdir /s /q "%INSTALLER_DIR%\dist" 2>nul
if exist "%INSTALLER_DIR%\build" rmdir /s /q "%INSTALLER_DIR%\build" 2>nul
del /f /q "%INSTALLER_DIR%\AgentInstaller.spec" 2>nul
cd /d "%INSTALLER_DIR%"
python -m PyInstaller --console --onefile --name="AgentInstaller" --uac-admin --paths "%AGENT_DIR%" --hidden-import="requests" agent_installer.py
if errorlevel 1 (
    echo     [ERROR] AgentInstaller build FAILED - xem output o tren.
    goto :failed
)

echo [3/4] Copy binaries sang C:\Test va D:\Test ...
if not exist "D:\Test" mkdir "D:\Test"
if not exist "C:\Test" mkdir "C:\Test"

copy /y "%AGENT_DIR%\dist\ParentalControlAgent.exe"    "C:\Test\ParentalControlAgent.exe"    >nul
copy /y "%AGENT_DIR%\dist\ParentalControlWatchdog.exe" "C:\Test\ParentalControlWatchdog.exe" >nul
copy /y "%AGENT_DIR%\dist\Updater.exe"                 "C:\Test\Updater.exe"                 >nul
copy /y "%INSTALLER_DIR%\dist\AgentInstaller.exe"      "C:\Test\AgentInstaller.exe"          >nul
copy /y "%AGENT_DIR%\dist\ParentalControlAgent.exe"    "D:\Test\ParentalControlAgent.exe"    >nul
copy /y "%AGENT_DIR%\dist\ParentalControlWatchdog.exe" "D:\Test\ParentalControlWatchdog.exe" >nul
copy /y "%AGENT_DIR%\dist\Updater.exe"                 "D:\Test\Updater.exe"                 >nul
echo     Done.

echo [4/4] Packing zip + version.json (%AGENT_VERSION%) ...
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"
powershell -NoProfile -Command "Compress-Archive -Path '%AGENT_DIR%\dist\*', '%AGENT_DIR%\*.py', '%AGENT_DIR%\communication', '%AGENT_DIR%\enforcement', '%AGENT_DIR%\local_store', '%AGENT_DIR%\protection', '%AGENT_DIR%\utils' -DestinationPath '%ZIP_PATH%' -Force"
powershell -NoProfile -Command "$v = @{ version = '%AGENT_VERSION%'; download_url = '/static/updates/agent-update.zip'; created_at = (Get-Date).ToUniversalTime().ToString('o') }; $v | ConvertTo-Json | Set-Content -Path '%BACKEND_STORAGE%\version.json' -Encoding ascii"

echo.
echo [5/5] Upload len R2 (neu co R2 credentials trong env)...
if not defined R2_ACCESS_KEY goto :skip_r2
if not defined R2_SECRET_KEY goto :skip_r2
python "%PROJECT_ROOT%upload_r2.py" --access-key "%R2_ACCESS_KEY%" --secret-key "%R2_SECRET_KEY%"
if errorlevel 1 goto :r2_fail
echo     Upload R2 thanh cong.
goto :after_r2
:r2_fail
echo     [WARN] Upload R2 that bai - vui long chay upload_r2.py thu cong.
goto :after_r2
:skip_r2
echo     Bo qua (chua dat R2_ACCESS_KEY / R2_SECRET_KEY env).
echo     Chay thu cong bang lenh upload_r2.py voi Access Key va Secret Key.
:after_r2

echo.
echo ============================================================
echo   DONE. Exe moi da o C:\Test (version %AGENT_VERSION%).
echo   Zip:  %ZIP_PATH%
echo   Tiep theo: chay AgentInstaller.exe (admin) tren may dich,
echo   hoac dung force-update tren web de cap nhat tu xa.
echo ============================================================
pause
exit /b 0

:failed
echo.
echo ============================================================
echo   BUILD FAILED - fix loi o tren roi chay lai.
echo ============================================================
pause
exit /b 1
