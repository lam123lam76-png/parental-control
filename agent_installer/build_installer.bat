@echo off
chcp 65001 > nul
echo ============================================================
echo   BUILD AgentInstaller.exe (PyInstaller onefile console)
echo ============================================================
cd /d "%~dp0"

set "PROJECT_ROOT=%~dp0.."
set "AGENT_DIR=%PROJECT_ROOT%agent"

echo [1/3] Building AgentInstaller.exe ...
python -m PyInstaller --onefile --console --name="AgentInstaller" ^
  --paths "%AGENT_DIR%" ^
  --hidden-import="requests" ^
  agent_installer.py
if errorlevel 1 (
    echo     [ERROR] Build FAILED - xem output o tren.
    goto :failed
)

echo [2/3] Copy sang C:\Test ...
if not exist "C:\Test" mkdir "C:\Test"
copy /y "dist\AgentInstaller.exe" "C:\Test\AgentInstaller.exe" >nul

echo [3/3] Xong.
echo ============================================================
echo   DONE: C:\Test\AgentInstaller.exe
echo   Su dung:
echo     AgentInstaller.exe --url https://nguyentruclam.io.vn --install
echo     AgentInstaller.exe --url https://nguyentruclam.io.vn --update
echo     AgentInstaller.exe --url https://nguyentruclam.io.vn --auto
echo ============================================================
pause
exit /b 0

:failed
pause
exit /b 1
