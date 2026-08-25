# ==============================================================================
# QUY TẮC CHUẨN HÓA BỘ CÀI ĐẶT VÀ ENGINE GIÁM SÁT (AGENT INSTALL & ENFORCEMENT)
# Scope: Parental Control System - Windows Agent, Installer Kit & Rule Engines
# ==============================================================================

Mục tiêu: Đảm bảo bộ cài đặt cài đặt thành công 100% trên máy đích (Windows 10/11) mà không bị Windows Defender chặn, và toàn bộ engine giám sát (App, Web, Time, Screen Capture, Remote Commands) hoạt động chính xác, ổn định và tự phục hồi.

---

## 1. QUY TẮC CÀI ĐẶT & THỨ TỰ CẤU HÌNH WINDOWS DEFENDER
- **Quy tắc bất biến:** Phải thêm ngoại lệ Windows Defender (`Add-MpPreference -ExclusionPath`) **TRƯỚC KHI** thực hiện lệnh sao chép bất kỳ file `.exe` nào vào thư mục cài đặt `C:\ProgramData\ParentalControl`.
- **Lý do:** Nếu sao chép trước khi Defender exclusion kích hoạt, trình diệt virus thời gian thực (Real-time Protection) của Windows sẽ phát hiện và cách ly (quarantine) file `.exe` chưa có chứng chỉ số, làm hỏng bộ cài đặt.
- **Tập tin batch installer:**
  - File `Install_Parental_Control.bat` và `test_run.bat` bắt buộc phải có `@echo off` và kiểm tra quyền Administrator (UAC elevation) ở dòng đầu tiên.
  - Phải dừng sạch tiến trình cũ (`taskkill /F /IM ParentalControlAgent.exe /IM ParentalControlWatchdog.exe`) trước khi ghi đè file mới.

---

## 2. QUY TẮC GIÁM SÁT TRUY CẬP WEB (WEB ENFORCEMENT ENGINE)
- **Quét toàn bộ cửa sổ trình duyệt (All-Windows Scanning):**
  - Engine cấm web **KHÔNG ĐƯỢC CHỈ KIỂM TRA** `GetForegroundWindow()` (cửa sổ đang active).
  - Bắt buộc phải dùng `win32gui.EnumWindows` để duyệt qua **TẤT CẢ** các cửa sổ trình duyệt đang mở trên máy tính (`chrome.exe`, `msedge.exe`, `firefox.exe`, `brave.exe`, `opera.exe`, v.v.).
  - Lý do: Người dùng có thể mở tab YouTube/Facebook ở màn hình phụ hoặc chạy ngầm rồi chuyển sang làm việc trên ứng dụng khác.
- **Chuẩn hóa đối chiếu Domain và Tiêu đề Cửa sổ (TLD Normalization):**
  - Tiêu đề cửa sổ trình duyệt thường hiển thị tên trang thay vì domain đầy đủ (ví dụ: *"YouTube - Microsoft Edge"* thay vì *"youtube.com"*).
  - Engine phải tự động loại bỏ các đuôi miền phổ biến (`.com`, `.net`, `.org`, `.vn`, `.io`, `.co`, `.tv`, `.gg`, `.me`) để so khớp cả tên gốc (`youtube`) lẫn chuỗi URL đầy đủ.

---

## 3. QUY TẮC GHI LOG ĐỘC LẬP TRONG MÔI TRƯỜNG NOCONSOLE
- **Cơ chế ghi log:**
  - Agent chạy ở chế độ ngầm (`pythonw` hoặc PyInstaller `--noconsole`), `sys.stdout` và `sys.stderr` đều bị hướng vào `devnull`.
  - Mọi module bắt buộc phải ghi log thông qua `logging.FileHandler` trực tiếp vào `C:\ProgramData\ParentalControl\agent_debug.log` với mã hóa UTF-8.
  - Không dựa vào `print()` hoặc StreamHandler tiêu chuẩn để debug trên máy người dùng.

---

## 4. QUY TẮC NẠP FILE CẤU HÌNH (.ENV) & BIẾN MÔI TRƯỜNG
- **Thứ tự ưu tiên nạp cấu hình:**
  1. `C:\ProgramData\ParentalControl\.env` (Ưu tiên số 1 - cấu hình sản xuất máy đích)
  2. Thư mục mã nguồn agent `.env` (Ưu tiên số 2 - môi trường phát triển)
  3. Biến môi trường hệ thống Windows (`os.environ`)
- **Biến môi trường bắt buộc có fallback an toàn:**
  - `BACKEND_URL`: Tự động chuẩn hóa `http`/`https` và sinh ra `WS_URL` tương ứng (`ws`/`wss`).
  - `DEVICE_NAME`: Luôn có fallback sang `socket.gethostname()`.
  - `API_KEY`: Luôn có fallback sang khóa hệ thống chuẩn.

---

## 5. QUY TẮC MÃ HÓA & LƯU TRỮ CREDENTIALS (DPAPI)
- Token kết nối (`device.cred`) được mã hóa qua Windows DPAPI (`CryptProtectData`).
- Để hỗ trợ cả chế độ chạy dịch vụ và chạy người dùng, file credentials phải được kiểm tra theo thứ tự:
  1. `%APPDATA%\ParentalControl\device.cred`
  2. `C:\ProgramData\ParentalControl\device.cred`
- Nếu file chưa tồn tại, Agent tự động hiển thị Pairing UI (Tkinter) để phụ huynh đăng ký thiết bị.

---

## 6. QUY TẮC GIÁM SÁT VÀ TỰ PHỤC HỒI TIẾN TRÌNH (DUAL WATCHDOG)
- `ParentalControlWatchdog.exe` và `ParentalControlAgent.exe` giám sát chéo lẫn nhau.
- Nếu Agent bị tắt đột ngột (taskkill hoặc crash), Watchdog tự khởi động lại Agent trong vòng 1.5 giây.
- Chỉ khi nhận lệnh tắt chính thức từ Phụ huynh (qua WebSocket command `shutdown_pc` hoặc file cờ `shutdown.flag`), Watchdog mới cho phép Agent dừng mà không khởi động lại.
