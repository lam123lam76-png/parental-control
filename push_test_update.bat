@echo off
chcp 65001 > nul
echo ========================================================
echo BÀI TEST CHẨN ĐOÁN CẬP NHẬT TỪ XA (AGENT DIAGNOSTICS)
echo ========================================================
echo.

set BACKEND_URL=http://127.0.0.1:8000
:: Lấy API Key từ file .env của backend
for /f "tokens=1,2 delims==" %%a in (backend_api\.env) do (
    if "%%a"=="API_KEY" set API_KEY=%%b
)

echo [1/3] Đang tiến hành đóng gói mã nguồn Agent (Pack-Zip) với version vTEST_01...
curl -s -X POST "%BACKEND_URL%/api/v1/agent/pack-zip" -d "version=vTEST_01"
echo.
echo.

echo [2/3] Phát lệnh cập nhật từ xa (Force-Update) qua Websocket...
curl -s -X POST "%BACKEND_URL%/api/devices/force-update-all?api_key=%API_KEY%"
echo.
echo.

echo [3/3] Đã phát lệnh thành công!
echo Hãy theo dõi log của Backend Console để xem khi nào Agent tải về, cài đặt
echo và gửi báo cáo kết quả chẩn đoán về endpoint /api/diagnostics/report
echo ========================================================
pause
