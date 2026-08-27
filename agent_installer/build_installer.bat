@echo off
chcp 65001 > nul
echo ============================================================
echo   BUILD AgentInstaller.exe (PyInstaller onefile console)
echo ============================================================
cd /d "%~dp0"

set "PROJECT_ROOT=%~dp0.."
set "AGENT_DIR=%PROJECT_ROOT%agent"

echo [1/3] Building PC_Installer.exe ...
python -m PyInstaller --onefile --noconsole --name="PC_Installer" --uac-admin ^
  --paths "%AGENT_DIR%" ^
  --icon="icon2.ico" ^
  --add-data "new_logo.png;." ^
  --hidden-import="requests" ^
  agent_installer.py
if errorlevel 1 (
    echo     [ERROR] Build FAILED - xem output o tren.
    goto :failed
)

echo [2/3] Copy sang C:\Test ...
if not exist "C:\Test" mkdir "C:\Test"
copy /y "dist\PC_Installer.exe" "C:\Test\PC_Installer.exe" >nul

echo [3/3] Xong.
echo ============================================================
echo   DONE: C:\Test\PC_Installer.exe
echo   Su dung:
echo     PC_Installer.exe --url https://nguyentruclam.io.vn --install
echo     PC_Installer.exe --url https://nguyentruclam.io.vn --update
echo     PC_Installer.exe --url https://nguyentruclam.io.vn --auto
echo ============================================================
pause
exit /b 0

:failed
pause
exit /b 1
