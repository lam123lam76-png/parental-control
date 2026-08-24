@echo off
chcp 65001 > nul
echo ╔════════════════════════════════════════════╗
echo ║  PARENTAL CONTROL - KIỂM TRA HỆ THỐNG     ║
echo ║  Double-click để chạy, đọc kết quả bên dưới║
echo ╚════════════════════════════════════════════╝
echo.

set PASS=0
set FAIL=0
set WARN=0

:: ────────────────────────────────────────────────
:: 1. Kiểm tra kết nối Internet
:: ────────────────────────────────────────────────
echo [1/6] Kiểm tra kết nối Internet...
ping -n 1 -w 3000 8.8.8.8 > nul 2>&1
if %errorlevel%==0 (
    echo        ✅ Có kết nối Internet
    set /a PASS+=1
) else (
    echo        ❌ KHÔNG có Internet - Agent sẽ không đồng bộ được!
    set /a FAIL+=1
)

:: ────────────────────────────────────────────────
:: 2. Kiểm tra Agent đang chạy
:: ────────────────────────────────────────────────
echo [2/6] Kiểm tra Agent đang chạy...
tasklist 2>nul | findstr /I "ParentalControlAgent" > nul
if %errorlevel%==0 (
    echo        ✅ Agent đang chạy
    set /a PASS+=1
) else (
    echo        ❌ Agent KHÔNG chạy!
    echo           → Hãy chạy file run_agent.bat hoặc khởi động lại máy
    set /a FAIL+=1
)

:: ────────────────────────────────────────────────
:: 3. Kiểm tra Watchdog đang chạy
:: ────────────────────────────────────────────────
echo [3/6] Kiểm tra Watchdog bảo vệ...
tasklist 2>nul | findstr /I "ParentalControlWatchdog" > nul
if %errorlevel%==0 (
    echo        ✅ Watchdog đang bảo vệ Agent
    set /a PASS+=1
) else (
    echo        ⚠️  Watchdog không chạy (Agent hoạt động nhưng ít bảo vệ hơn)
    set /a WARN+=1
)

:: ────────────────────────────────────────────────
:: 4. Kiểm tra file .env tồn tại
:: ────────────────────────────────────────────────
echo [4/6] Kiểm tra file cấu hình (.env)...
if exist "%~dp0.env" (
    echo        ✅ File .env tồn tại
    set /a PASS+=1
) else (
    echo        ❌ KHÔNG tìm thấy file .env
    echo           → Sao chép .env.example thành .env và điền giá trị
    set /a FAIL+=1
)

:: ────────────────────────────────────────────────
:: 5. Kiểm tra Python đã cài
:: ────────────────────────────────────────────────
echo [5/6] Kiểm tra Python...
python --version > nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        ✅ %%v đã cài
    set /a PASS+=1
) else (
    echo        ⚠️  Python chưa cài - một số công cụ test sẽ không chạy được
    set /a WARN+=1
)

:: ────────────────────────────────────────────────
:: 6. Kiểm tra Backend API (nếu có curl)
:: ────────────────────────────────────────────────
echo [6/6] Kiểm tra kết nối Backend...
where curl > nul 2>&1
if %errorlevel%==0 (
    curl -s --max-time 5 http://localhost:8000/api/health > nul 2>&1
    if %errorlevel%==0 (
        echo        ✅ Backend hoạt động tại localhost:8000
        set /a PASS+=1
    ) else (
        echo        ⚠️  Không kết nối được localhost:8000
        echo           (Backend có thể chạy ở địa chỉ khác - kiểm tra file .env)
        set /a WARN+=1
    )
) else (
    echo        ⚠️  Bỏ qua kiểm tra Backend (curl chưa có)
    set /a WARN+=1
)

:: ────────────────────────────────────────────────
:: Tổng kết
:: ────────────────────────────────────────────────
echo.
echo ════════════════════════════════════════════
echo   KẾT QUẢ KIỂM TRA
echo   ✅ Đạt:    %PASS%
echo   ❌ Lỗi:    %FAIL%
echo   ⚠️  Cảnh báo: %WARN%
echo ════════════════════════════════════════════

if %FAIL%==0 (
    if %WARN%==0 (
        echo   🎉 Hệ thống hoạt động hoàn hảo!
    ) else (
        echo   ✅ Cơ bản ổn - có một số điểm cần lưu ý (⚠️ ở trên)
    )
) else (
    echo   ❌ Có %FAIL% lỗi cần xử lý - xem hướng dẫn ở trên
)

echo ════════════════════════════════════════════
echo.
pause
