@echo off
chcp 65001 >nul
echo [1/2] Kiem tra va don dep cong 8000 (Auto-kill dangiling processes)...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [2/2] Starting FastAPI Backend for Parental Control Agent...
cd backend_api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
