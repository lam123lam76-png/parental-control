# 📓 NHẬT KÝ LỖI DỰ ÁN (PROJECT ERROR LOG)

---

### 1. Lỗi CORS & Hardcode localhost khi gọi API từ Điện thoại/Tunnel
- **Thời gian**: 2026-08-11 19:30
- **Vị trí**: `manager-web/src/lib/api.js` & `backend_api/main.py`
- **Vấn đề**: `api.js` bị gán cứng `http://localhost:8000` làm thiết bị di động không kết nối được backend. Ngoài ra `allow_origins=["*"]` vi phạm chuẩn CORS khi bật `allow_credentials=True`.
- **Giải pháp**: 
  - Sửa `BASE_URL` trong `api.js` thành relative `""` (tận dụng Proxy).
  - Sửa FastAPI `CORSMiddleware` dùng `allow_origin_regex=r".*"`.
- **Kết quả**: Đăng ký & đăng nhập hoạt động mượt mà trên Mobile, Domain và Local.

---

### 2. Lỗi `TypeError: BlockerUI.__init__()` / `is_visible` (Agent Python)
- **Thời gian**: 2026-08-11 19:59
- **Vị trí**: `agent/main.py` & `agent/protection/blocker.py`
- **Vấn đề**: Code trong `main.py` gọi `self.blocker_ui.is_visible` nhưng trong `BlockerUI` đặt tên là `is_showing`, làm crash Agent khi quét luật thời gian.
- **Giải pháp**: Thêm alias `@property def is_visible(self): return self.is_showing` vào `blocker.py`.
- **Kết quả**: Agent không bị văng exception khi bật kiểm tra màn hình khóa.

---

### 3. Lỗi `ReferenceError: handlePair is not defined` (React Frontend)
- **Thời gian**: 2026-08-11 20:18
- **Vị trí**: `manager-web/src/components/FastAPIDashboard.jsx`
- **Vấn đề**: Sau khi refactor auth flow, nút "Pair Device" trên Header và Drawer vẫn gọi hàm `handlePair` đã bị xóa.
- **Giải pháp**: Khai báo hàm `handlePair = () => handleLogout()` trong `FastAPIDashboard.jsx`.
- **Kết quả**: Web UI load 100% không bị văng trắng màn hình (ErrorBoundary).

---

### 4. Lỗi `HTTP 404 Not Found` khi gọi Endpoint API mới
- **Thời gian**: 2026-08-11 20:20
- **Vị trí**: `backend_api/main.py` & Tiến trình `server_tray_app.py`
- **Vấn đề**: Viết thêm API `/api/device/{id}/logs` & `/alerts` nhưng tiến trình Backend ngầm vẫn chạy bản code cũ trong RAM (chưa reload code mới).
- **Giải pháp**: Kill tiến trình Python cũ (`taskkill /F /PID`) và bật lại `server_tray_app.py`.
- **Kết quả**: API trả về `HTTP 200 OK` dữ liệu thực.

---

### 5. Lỗi `TypeError: '>' not supported between LocalDB and int` (Agent Python)
- **Thời gian**: 2026-08-11 20:28
- **Vị trí**: `agent/main.py` & `agent/communication/log_uploader.py`
- **Vấn đề**: Khởi tạo `LogUploader` truyền sai thứ tự tham số vị trí làm đối tượng `self.local_db` bị gán nhầm vào biến số nguyên `batch_interval`.
- **Giải pháp**: Chuyển tất cả lệnh khởi tạo sang dạng Keyword Arguments (`name=value`).
- **Kết quả**: Agent chạy ngầm `LogUploader-Worker` ổn định, không bị crash thread.

---

### 6. Lỗi SystemConsoleLogBox hiển thị Log giả (Mock Data)
- **Thời gian**: 2026-08-11 20:26
- **Vị trí**: `manager-web/src/components/SystemConsoleLogBox.jsx`
- **Vấn đề**: Component Log Box dùng `setInterval` tự sinh log ngẫu nhiên hardcode, không phản ánh hoạt động thực của hệ thống.
- **Giải pháp**: Xóa fake log, kết nối props `realLogs`, `alerts`, `status`, `userActionLogs` từ Backend và các nút thao tác UI vào Log Box.
- **Kết quả**: Bảng Console phản ánh 100% các sự kiện thời gian thực (Gửi/Nhận lệnh chụp ảnh, Khóa/Mở màn hình, Tạo/Xóa quy tắc, Log tiến trình).

---

### 7. Lỗi Ảnh chụp màn hình bị vỡ (Broken Image) & Popup phóng to
- **Thời gian**: 2026-08-11 20:37
- **Vị trí**: `manager-web/vite.config.js` & `FastAPIDashboard.jsx`
- **Vấn đề**: `vite.config.js` thiếu proxy `/static` làm Vite trả về file `index.html` (text/html) cho đường dẫn ảnh. Lightbox Modal phóng to thiếu `onError` fallback.
- **Giải pháp**: 
  - Thêm proxy `/static` về `http://127.0.0.1:8000` trong `vite.config.js`.
  - Thêm tự động `onError` fallback cho ảnh gallery và popup phóng to.
- **Kết quả**: Cả ảnh thu nhỏ và ảnh phóng to hiển thị sắc nét 100%.

---

### 8. Lỗi `ReferenceError: handleToggleLock is not defined` (React Frontend)
- **Thời gian**: 2026-08-11 21:19
- **Vị trí**: `manager-web/src/components/FastAPIDashboard.jsx`
- **Vấn đề**: Tinh chỉnh widget Khóa màn hình Switch Toggle nhưng hàm `handleToggleLock` chưa được định nghĩa trong component làm văng lỗi ErrorBoundary.
- **Giải pháp**: Định nghĩa hàm `handleToggleLock = () => { isLocked ? handleUnlock() : handleLock() }` trong `FastAPIDashboard.jsx`.
- **Kết quả**: Nút gạt Switch Khóa/Mở màn hình hoạt động mượt mà 100%, trang dashboard load thành công không còn lỗi runtime.
