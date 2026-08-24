@echo off
title PARENTAL CONTROL - NAMED TUNNEL LAUNCHER
setlocal enabledelayedexpansion

echo ==============================================================================
echo  KÍCH HOẠT CLOUDFLARE NAMED TUNNEL CHO NGUYENTRUCLAM.IO.VN
echo ==============================================================================

set TOKEN=%1

if "%TOKEN%"=="" (
    if exist .cloudflare_token.txt (
        set /p TOKEN=<.cloudflare_token.txt
    )
)

if "%TOKEN%"=="" (
    echo.
    echo Vui long nhap chuoi TOKEN tu trang Cloudflare Zero Trust:
    echo (Vd: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...)
    echo.
    set /p TOKEN="Token của bạn: "
    echo !TOKEN!>.cloudflare_token.txt
)

if "%TOKEN%"=="" (
    echo [ERROR] Token khong duoc de trong!
    pause
    exit /b 1
)

echo [OK] Dang khoi chay Cloudflare Named Tunnel cho nguyentruclam.io.vn...
"C:\Cloudflared\cloudflared.exe" tunnel run --token !TOKEN!

pause
