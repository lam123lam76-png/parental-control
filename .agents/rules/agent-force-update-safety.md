# ==============================================================================
# QUY TẮC AN TOÀN TUYỆT ĐỐI KHI FORCE UPDATE AGENT (CHỐNG MẤT KẾT NỐI MÁY CON)
# Scope: Parental Control System - Agent & Remote Updater
# ==============================================================================

Mục tiêu tối thượng: Mọi lần nâng cấp phiên bản mới hoặc phát hành Force Update từ Web Manager / Backend TUYỆT ĐỐI KHÔNG ĐƯỢC LÀM HỎNG AGENT trên máy con (DESKTOP-IDUQ3QB), tránh dẫn đến mất kiểm soát từ xa.

---

## 1. NGUYÊN TẮC ZERO MISSING DEPENDENCIES (BẮT BUỘC STANDALONE 100%)
- **Môi trường máy đích:** Là máy tính Windows người dùng sạch, KHÔNG CÀI SẴN PYTHON RUNTIME.
- **Yêu cầu biên dịch PyInstaller:**
  - File chạy độc lập (`ParentalControlAgent.exe`, `Updater.exe`, `ParentalControlWatchdog.exe`, `Agent_check_good.exe`) BẮT BUỘC PHẢI NHÚNG ĐỦ:
    - `sqlite3.dll` và `_sqlite3.pyd` (Lấy từ `sys.prefix/DLLs`).
    - C extensions: `win32gui`, `win32process`, `win32crypt`, `mss`, `PIL`, `psutil`, `websocket`.
  - Phải sử dụng tham số: `--onefile --noconsole --add-binary="sqlite3.dll;." --add-binary="_sqlite3.pyd;." --collect-all="sqlite3"`.
  - Dung lượng file `.exe` hợp lệ phải từ 15MB - 35MB. Cấm phát hành file rỗng hoặc file lỗi biên dịch.

---

## 2. TIẾN TRÌNH ĐỘC LẬP HOÀN TOÀN (DETACHED PROCESS LIFECYCLE - BẤT BIẾN)
- Mọi thao tác khởi chạy tiến trình con từ `Updater.exe`, `Watchdog`, hoặc `Agent` BẮT BUỘC phải sử dụng cờ:
  `creationflags = DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)` và `close_fds=True`.
- **Lý do:** Trên Windows, nếu không có cờ `DETACHED_PROCESS`, khi tiến trình cha (`Updater.exe`) gọi `sys.exit(0)`, Windows sẽ tự động thu hồi (kill) toàn bộ tiến trình con nằm trong Process Tree.
- BẮT BUỘC phải khởi chạy song song cả `ParentalControlAgent.exe` VÀ `ParentalControlWatchdog.exe` sau khi cập nhật xong.

---

## 3. CƠ CHẾ TỰ ĐỘNG PHỤC HỒI BẢN CŨ (AUTO-ROLLBACK ON STARTUP CRASH)
- `Updater.exe` khi cập nhật phải sao lưu file cũ sang `.bak`.
- Sau khi khởi động tiến trình mới, `Updater.exe` phải quan sát trong 3 giây:
  - Nếu tiến trình mới thoát sớm hoặc crash (exitcode != None), `Updater.exe` BẮT BUỘC phải tự động phục hồi file `.bak` trở lại thành `.exe` và kích hoạt lại bản cũ.
  - Ngăn ngừa 100% tình huống máy đích bị treo do bản build mới bị lỗi runtime hoặc thiếu thư viện.

---

## 4. CỔNG KIỂM THỬ MÔ PHỎNG LOCAL (LOCAL SIMULATION GATE BEFORE REMOTE PUSH)
- Trước khi phát lệnh `force-update-all` lên máy thật: BẮT BUỘC phải chạy bài test mô phỏng toàn trình trên máy local:
  `python -m unittest agent/tests/test_updater_main.py`
  và kiểm thử khởi động độc lập:
  `agent\dist\ParentalControlAgent.exe` và `agent\dist\ParentalControlWatchdog.exe`.
- Nếu bài test mô phỏng tiến trình local này chưa PASS 100%, NGHIÊM CẤM phát lệnh cập nhật lên máy con thật.

---

## 5. BẢO VỆ NGUYÊN VẸN FILE CẤU HÌNH ĐỊNH DANH (.ENV)
- Quá trình cập nhật trên máy con (`Updater.exe`) TUYỆT ĐỐI KHÔNG ĐƯỢC GHI ĐÈ hoặc XÓA file `.env` tại `C:\ProgramData\ParentalControl\.env`.
- File `.env` chứa các thông số sống còn:
  - `BACKEND_URL` & `WS_URL` (Domain VPS `nguyentruclam.io.vn`)
  - `API_KEY` (Khóa xác thực thiết bị)
  - `DEVICE_NAME` (Tên định danh thiết bị)
- Nếu file `.env` bị mất, Agent sẽ mất kết nối hoàn toàn và không thể tự phục hồi từ xa.

---

## 6. LƯỚI GIÁM SÁT & PHỤC HỒI 3 LỚP (3-LAYER RESILIENCE)
- **Lớp 1 (Real-time):** Dual Cross-Monitoring giữa `ParentalControlAgent.exe` và `ParentalControlWatchdog.exe` (mỗi bên kiểm tra đối phương mỗi 1.5 giây).
- **Lớp 2 (Logon Startup):** Windows Registry Run Key `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ParentalControlAgent` và `HKLM`.
- **Lớp 3 (Scheduled Heartbeat):** Windows Task Scheduler `ParentalControlWatchdogTask` quét và nạp lại mỗi 2 phút độc lập trong nền.

---

## 7. TỰ ĐỘNG CHẨN ĐOÁN & BÁO CÁO SAU CẬP NHẬT (DIAGNOSTIC REPORT)
- Khi Agent khởi động ở phiên bản mới, `diagnostic.py` tự động kích hoạt:
  - Kiểm tra kết nối WebSocket tới Server.
  - Kiểm tra module chụp ảnh màn hình GDI/MSS.
  - Kiểm tra CSDL SQLite & chữ ký HMAC.
  - Tự động gửi báo cáo tình trạng toàn vẹn về Telegram của Quản trị viên (`chat_id: 1326412172`).
- Phải xác minh phản hồi lệnh `check_version` qua WebSocket đạt `200 OK` với số phiên bản mới trước khi tuyên bố cập nhật thành công.

---

## 8. QUY TẮC AN TOÀN PHÁT TRIỂN & TEST
- Tuyệt đối KHÔNG gửi lệnh tắt máy (`shutdown_pc`) hoặc các lệnh phá hủy lên thiết bị máy con thật trong quá trình dev/test.
- Mọi logic phải được kiểm thử qua Mock Unit Test (`pytest`) trên Backend trước khi phát hành.
