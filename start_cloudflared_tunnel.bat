@echo off
setlocal enabledelayedexpansion

if exist "C:\Cloudflared\cloudflared.exe" (
    set "CLOUDFLARED_BIN=C:\Cloudflared\cloudflared.exe"
    goto run_tunnel
)

if exist "C:\Cloudflared\cloudflared.exe.exe" (
    set "CLOUDFLARED_BIN=C:\Cloudflared\cloudflared.exe.exe"
    goto run_tunnel
)

where cloudflared >nul 2>&1
if %errorlevel% equ 0 (
    set "CLOUDFLARED_BIN=cloudflared"
    goto run_tunnel
)

echo [INFO] Dang tai phan mem cloudflared tu Cloudflare...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'C:\Cloudflared\cloudflared.exe'"
set "CLOUDFLARED_BIN=C:\Cloudflared\cloudflared.exe"

:run_tunnel
echo [OK] Da phat hien Cloudflare Tunnel: !CLOUDFLARED_BIN!
echo.
echo Dang tao duong truyen Cloudflare Quick Tunnel sang Port 5173 (Manager Web)...
echo ------------------------------------------------------------------------------
echo Luu y: Vui long giu cua so nay chay ngam de duy tri duong truyen tu xa!
echo ------------------------------------------------------------------------------
echo.

"!CLOUDFLARED_BIN!" tunnel --url http://localhost:5173

pause
