@echo off
setlocal enabledelayedexpansion

powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    set LOCAL_IP=!LOCAL_IP: =!
    goto found_ip
)

:found_ip
if "%LOCAL_IP%"=="" set LOCAL_IP=localhost

echo [1/2] Dang khoi chay FastAPI Backend (Port 8000)...
start "ParentalControl Backend" cmd /k "cd backend_api && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/2] Dang khoi chay Manager Web UI (Port 5173)...
start "ParentalControl Manager Web" cmd /k "cd manager-web && npm run dev -- --host 0.0.0.0"

echo.
echo ==============================================================================
echo  MAY CHU DA DUOC KICH HOA THANH CONG TREN MAY NAY!
echo ==============================================================================
echo  Trang Quan Ly (Phu Huynh):  http://localhost:5173  hoac  http://%LOCAL_IP%:5173
echo  Backend API Endpoint:      http://%LOCAL_IP%:8000
echo  WebSocket Real-time Stream:  ws://%LOCAL_IP%:8000/ws
echo ==============================================================================
echo.
echo  IP local cua may nay: %LOCAL_IP%
echo  De dong goi Agent cho may em trai, chay file: agent\build_local_agent.bat %LOCAL_IP%
echo ==============================================================================
pause
