# ==============================================================================
# PROJECT PERMANENT RULES & IMMUTABLE SYSTEM CONSTRAINTS
# Parental Control System
# ==============================================================================

## 1. BUILT-IN SUPER ADMIN ACCOUNT (BẤT BIẾN - TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA)
Hệ thống Parental Control được tích hợp một tài khoản Quản trị viên tối cao (Super Admin) mặc định.
Tài khoản này có các đặc quyền và thông tin định danh vĩnh viễn như sau:

- **ID / Email:** `admin@nguyentruclam.io.vn`
- **Mật khẩu (Password):** `Truc@1905s`

### Đặc quyền và Hành vi bắt buộc:
1. **Đăng nhập không cần đăng ký:** Tài khoản này LUÔN LUÔN có thể đăng nhập trực tiếp tại `POST /api/auth/login` trên Web Dashboard mà không cần phải thực hiện thao tác đăng ký trước (kể cả khi Database rỗng hoặc vừa được reset). Hệ thống sẽ tự động khởi tạo bản ghi trong Database nếu chưa tồn tại.
2. **Quyền truy cập không giới hạn (Full Access):** 
   - `is_system_admin = True`
   - `role = "admin"`
   - Sở hữu 100% tất cả các quyền trong hệ thống (`can_view_screenshots: True`, `can_manage_rules: True`, `can_view_logs: True`, `can_remote_control: True`, `can_manage_users: True`).
3. **Mở khóa mọi tính năng:** Mọi tính năng (System Console Log Box, Rules, Screenshots, Quản lý phân quyền tài khoản con, Auto-update, Dọn dẹp lưu trữ, Focus mode, v.v.) luôn luôn hiển thị và sử dụng được cho tài khoản này.
4. **Phân quyền tài khoản thường:** Các tài khoản thông thường (sub-accounts) bắt buộc phải được tài khoản Super Admin cấp quyền trong mục *Account Permissions* mới được mở khóa các tính năng tương ứng.
5. **Mật khẩu chủ mở khóa Agent:** Mật khẩu `Truc@1905s` là Master Password dùng để giải khóa màn hình máy con khẩn cấp tại `POST /api/auth/verify-password`.
6. **CẤM XÓA BỎ:** Trong tất cả các đợt refactor, audit bảo mật, clean code sau này, AI và lập trình viên TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA bỏ cơ chế hỗ trợ tài khoản Super Admin này.

---

## 2. DESIGN SYSTEM TOKENS & UI RULES
- Bảng màu chủ đạo: Emerald Ink (`#064E3B`) và Champagne Cream (`#F8E7C9`).
- Toàn bộ component trên `manager-web` phải sử dụng `getThemeStyles(theme)` từ `src/lib/theme.js`.
- Không sử dụng màu ad-hoc ngoài theme token.

---

## 3. QUY TẮC AN TOÀN TUYỆT ĐỐI KHI FORCE UPDATE AGENT (CHỐNG MẤT KẾT NỐI MÁY CON)

1. **Zero Missing Dependencies (Bắt buộc Standalone 100%):**
   - Máy con không cài Python. Mọi bản build (`ParentalControlAgent.exe`, `Updater.exe`, `ParentalControlWatchdog.exe`, `Agent_check_good.exe`) BẮT BUỘC PHẢI NHÚNG ĐỦ `sqlite3.dll`, `_sqlite3.pyd` và toàn bộ C extensions (`win32*`, `mss`, `PIL`, `psutil`, `websocket`).
   - Phải biên dịch qua `agent/build_prod_exe.bat` với Exit Code = 0 trước khi nén zip phát hành.

2. **Tiến Trình Độc Lập Hoàn Toàn (Detached Process Lifecycle - BẤT DI BẤT DỊCH):**
   - Mọi thao tác khởi chạy tiến trình con từ `Updater.exe`, `Watchdog`, hoặc `Agent` BẮT BUỘC phải sử dụng cờ:
     `creationflags = DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200) | CREATE_NO_WINDOW (0x08000000)` và `close_fds=True`.
   - TUYỆT ĐỐI CẤM gọi `Popen` trần không cờ, để đảm bảo khi tiến trình cha (`Updater.exe`) kết thúc bằng `sys.exit(0)`, Windows KHÔNG ĐƯỢC THU HỒI hay đóng tiến trình con (`Agent` / `Watchdog`).

3. **Cơ Chế Tự Động Phục Hồi Bản Cũ (Auto-Rollback on Startup Crash):**
   - `Updater.exe` phải lưu bản cũ thành `.bak`. Sau khi khởi chạy file mới, `Updater.exe` phải kiểm tra trạng thái sống của tiến trình mới trong 3 giây.
   - Nếu bản mới bị crash hoặc thoát sớm (exitcode != None), `Updater.exe` BẮT BUỘC phải tự động phục hồi file `.bak` và khởi động lại bản cũ, chống hiện tượng máy đích bị mất kết nối vĩnh viễn.

4. **Cổng Kiểm Thử Mô Phỏng Local (Local Simulation Gate Before Remote Push):**
   - Trước khi phát lệnh `force-update-all` lên máy thật: BẮT BUỘC phải chạy bài test mô phỏng toàn trình trên máy local (tải zip ➔ Updater kill ➔ ghi đè ➔ spawn detached ➔ verify sống sau khi Updater thoát ➔ kết nối WebSocket).
   - Nếu bài test mô phỏng tiến trình local này chưa PASS 100%, NGHIÊM CẤM phát lệnh cập nhật lên máy con thật.

5. **Bảo Vệ Tuyệt Đối File Cấu Hình (.env):**
   - Quá trình cập nhật (`Updater.exe`) TUYỆT ĐỐI KHÔNG ĐƯỢC GHI ĐÈ hoặc XÓA file `C:`ProgramData`ParentalControl`.env` chứa `API_KEY`, `DEVICE_NAME`, `BACKEND_URL`.

6. **Lưới Giám Sát & Phục Hồi 3 Lớp (3-Layer Resilience):**
   - *Lớp 1 (Real-time):* Dual Cross-Monitoring giữa `ParentalControlAgent.exe` và `ParentalControlWatchdog.exe` (mỗi bên kiểm tra đối phương mỗi 1.5s).
   - *Lớp 2 (Logon Startup):* Windows Registry Run Key `HKCU`Software`Microsoft`Windows`CurrentVersion`Run`ParentalControlAgent` và `HKLM`.
   - *Lớp 3 (Scheduled Heartbeat):* Windows Task Scheduler `ParentalControlWatchdogTask` quét và nạp lại mỗi 2 phút độc lập trong nền.

7. **Cấm Lệnh Phá Hủy / Tắt Máy Thực Tế Khi Dev/Test:**
   - Tuyệt đối không gửi lệnh `shutdown_pc` hay lệnh phá hủy lên thiết bị máy con thật trong quá trình phát triển và kiểm thử.

---

## 4. QUY TẮC PHÁT HÀNH & CÀI ĐẶT WINDOWS (INSTALLATION & EXE RULES)
Nhằm tránh sự cố sập hoặc treo ứng dụng trên máy khách (Target Machine), mọi thao tác sửa lỗi Agent phải tuân thủ nghiêm:

1. **BẮT BUỘC BIÊN DỊCH LẠI (REBUILD EXE) SAU KHI SỬA CODE:**
   - Agent chạy trên máy khách dưới dạng tệp nhị phân đóng gói bằng PyInstaller (`ParentalControlAgent.exe`, `Watchdog.exe`). 
   - Sau khi sửa bất kỳ mã nguồn `.py` nào trong thư mục `agent/`, **TUYỆT ĐỐI BẮT BUỘC** phải chạy lệnh `.`build_prod_exe.bat` để biên dịch lại file `.exe` trước khi đóng gói file ZIP. Nếu không, máy khách sẽ chạy lại phiên bản dính lỗi cũ.

2. **XỬ LÝ TRIỆT ĐỂ FILE LOCK BẰNG TREE-KILL TRONG BATCH SCRIPT:**
   - Khi Agent crash, hộp thoại lỗi Windows (`WerFault.exe` hoặc popup Tkinter) sẽ giữ khóa cứng file `.exe` (File Lock). Lệnh `copy /Y` thông thường sẽ thất bại thầm lặng (swallow error).
   - Trong các file Batch (như `Install_Parental_Control.bat`), bắt buộc sử dụng cờ **Tree Kill (`taskkill /F /T`)** để diệt cả tiến trình lỗi và hộp thoại thông báo. Bắt buộc gọi lệnh `del /F /Q` để xóa file cũ trước khi copy file mới.

3. **CẤM SỬ DỤNG DẤU NGOẶC ĐƠN TRONG KHỐI IF CỦA WINDOWS BATCH:**
   - Cấm sử dụng các dấu ngoặc đơn không được escape `()` bên trong các khối lệnh `if (...)` hoặc `for (...)`. 
   - Ví dụ: Dòng chữ `echo [INFO] Quyen (UAC)...` sẽ làm `cmd.exe` đóng sập cửa sổ đen trong 0.1 giây với lỗi `... was unexpected at this time.` vì hiểu nhầm `)` là kết thúc khối lệnh.

4. **CHUẨN HÓA CÚ PHÁP NÂNG QUYỀN (UAC RUNAS) CỦA POWERSHELL:**
   - PowerShell không hỗ trợ chạy trực tiếp tệp `.bat` bằng tham số `-Verb RunAs` (sẽ báo lỗi `The request is not supported`).
   - Mẫu chuẩn bắt buộc dùng để xin quyền Admin cho file Batch:
     `powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c `"`"%~f0`"`"' -Verb RunAs"`
---

## 5. QUY TẮC XỬ LÝ LỖI MẤT KẾT NỐI & XUNG ĐỘT CREDENTIALS (403 FORBIDDEN)

1. **Xung Đột File Cache (Stale Credentials):**
   - Lỗi `403 Forbidden` trên Agent thường xảy ra khi Agent ưu tiên đọc nhầm tệp credential bị kẹt hoặc hết hạn tại `C:`Users`<User>`AppData`Roaming`ParentalControl`device.cred`, trong khi Web Dashboard lại đang quản lý Device ID mới nằm ở `C:`ProgramData`ParentalControl`device.cred`.
   - Backend sẽ ngay lập tức từ chối kết nối (403) vì Device ID cũ không còn hợp lệ trên hệ thống, dẫn đến tình trạng Web Frontend báo Offline vĩnh viễn dù Agent đã được khởi động lại.

2. **Cách Khắc Phục Khi Xảy Ra Sự Cố Đang Test:**
   - Để khôi phục kết nối, bắt buộc phải diệt tiến trình Agent đang chạy (vd: `	askkill /F /IM pythonw.exe`), sau đó xóa bỏ file `device.cred` trong `AppData` để ép Agent fallback (tìm kiếm dự phòng) sang tệp `device.cred` ở `ProgramData`. Khi nạp đúng Device ID mới, Agent sẽ gửi Heartbeat thành công.

3. **Nguyên Tắc Lập Trình (Preventive Code Rule):**
   - Để hệ thống không bao giờ lặp lại lỗi này trong tương lai, mã nguồn Agent CẦN thiết kế cơ chế tự động giải quyết lỗi 403:
   - Thay vì lặp lại vô thời hạn (retry loop) mỗi 60 giây một cách mù quáng, nếu Server trả về `403 Forbidden`, Agent PHẢI tự động xóa bỏ file `device.cred` (cả ở AppData và ProgramData), sau đó hiển thị lại giao diện Ghép nối (Pairing UI) cho người dùng để cấp lại phiên bản Device ID/Token mới.
   - Thao tác xóa credentials (`clear_credentials`) CẦN xử lý triệt để lỗi phân quyền (Permission/OSError), nếu thất bại ở ProgramData thì phải ghi log rõ ràng và không được swallow (bỏ qua thầm lặng) lỗi, nhằm cảnh báo cho SysAdmin.

---

## 6. QUY TẮC CẤU HÌNH MẠNG VÀ CHỐNG HARDCODE LOCALHOST (FAIL-FAST POLICY)

1. **Không Hardcode Localhost Trên Môi Trường Target (Agent):**
   - Tuyệt đối KHÔNG ĐƯỢC đặt fallback dự phòng về `http://127.0.0.1` hay `localhost` trong mã nguồn của Agent (như `ws_client.py`, `lert_sender.py`, `log_uploader.py`). 
   - Agent cài trên máy con phải tuân thủ nguyên tắc **Fail-Fast**: Bắt buộc đọc `BACKEND_URL` và `WS_URL` từ file `.env`. Nếu không tìm thấy, hệ thống phải ngắt (crash) ngay lập tức (`sys.exit(1)`) và báo lỗi ra Console/Log. Tránh hiện tượng lỗi câm (silent failure) khiến Agent ảo tưởng là đã gửi dữ liệu thành công nhưng thực chất gửi vào hư vô.

2. **CORS Headers Động Dành Cho Backend:**
   - `llow_origins` trong `ackend_api/main.py` tuyệt đối không được hardcode cứng danh sách `localhost`.
   - Bắt buộc phải đọc từ biến môi trường `ALLOWED_ORIGINS` nhằm dễ dàng cập nhật khi Manager Web được host trên các domain bên ngoài (Vercel, Netlify, Cloudflare).
   - Nếu không, Frontend truy cập bằng IP / domain công cộng sẽ bị trình duyệt chặn hoàn toàn (CORS blocked).

3. **Tệp Cấu Hình Chuẩn (Standard .env):**
   - Luôn duy trì `gent/.env.example` chứa domain Production làm mẫu (vd: `https://nguyentruclam.io.vn`). Lập trình viên và công cụ Deploy tự động cần copy chuẩn mẫu này, không được lén lút sửa mẫu về `localhost`.

4. **Khởi Động Backend API (Chống kẹt cổng 8000):**
   - TUYỆT ĐỐI KHÔNG gõ chay lệnh \python -m uvicorn main:app --reload\ trực tiếp vào Terminal.
   - Luôn luôn sử dụng lệnh \.\run_backend.bat\ để khởi động Backend trong quá trình dev/test.
   - Script này đã được tích hợp cơ chế tự động dò tìm và "tiêu diệt" (kill) các tiến trình cũ đang bị kẹt trên cổng 8000 trước khi chạy Uvicorn mới, ngăn chặn hoàn toàn lỗi deadlock và timeout.
