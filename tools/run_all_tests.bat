@echo off
chcp 65001 > nul
echo ╔════════════════════════════════════════════════╗
echo ║  PARENTAL CONTROL — CHẠY TẤT CẢ TESTS (DEV)  ║
echo ╚════════════════════════════════════════════════╝
echo.

:: Cài dependencies
echo 📦 Cài thư viện cần thiết...
pip install requests psutil python-dotenv --quiet
echo.

:: Khởi tạo bộ đếm
set TOTAL_PASS=0
set TOTAL_FAIL=0

:: ─────────────────────────────────────────
echo ══════════════════════════════════════════
echo   TEST 1/2: Kiểm tra API Backend
echo ══════════════════════════════════════════
python "%~dp0test_api.py"
if %errorlevel%==0 (
    echo   → ✅ API tests PASS
    set /a TOTAL_PASS+=1
) else (
    echo   → ❌ API tests FAIL
    set /a TOTAL_FAIL+=1
)

echo.
:: ─────────────────────────────────────────
echo ══════════════════════════════════════════
echo   TEST 2/2: Kiểm tra Agent trên máy này
echo ══════════════════════════════════════════
python "%~dp0test_agent_health.py"
if %errorlevel%==0 (
    echo   → ✅ Agent tests PASS
    set /a TOTAL_PASS+=1
) else (
    echo   → ❌ Agent tests FAIL
    set /a TOTAL_FAIL+=1
)

:: ─────────────────────────────────────────
echo.
echo ══════════════════════════════════════════
echo   📊 TỔNG KẾT CUỐI CÙNG
echo   ✅ Đạt: %TOTAL_PASS%/2 bộ test
echo   ❌ Lỗi: %TOTAL_FAIL%/2 bộ test
echo ══════════════════════════════════════════

if %TOTAL_FAIL%==0 (
    echo   🎉 TẤT CẢ ĐẠT! Hệ thống hoạt động ổn định.
    exit /b 0
) else (
    echo   ⚠️  Có %TOTAL_FAIL% bộ test thất bại. Xem chi tiết ở trên.
    echo      Gửi output này cho Dev để được hỗ trợ.
    exit /b 1
)
