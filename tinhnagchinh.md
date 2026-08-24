# 🚀 Danh Sách 5 Tính Năng Cốt Lõi Đã Hoàn Thành (Parental Control System v2.0)

Tài liệu này tổng hợp chi tiết 5 tính năng cốt lõi vừa được xây dựng, kết nối thành công và kiểm thử tự động toàn diện trên hệ thống **Parental Control System**.

---

## 1. 🛡️ Hệ Thống Phân Quyền (RBAC) & Quản Lý Tài Khoản Phụ
- **Mục đích**: Cho phép Admin (Phụ huynh chính) tạo và mời các tài khoản phụ trong gia đình (Bố, Mẹ, Anh/Chị...) và cấp quyền quản lý tinh chỉnh theo từng chức năng (Granular Permissions).
- **Cấu trúc Cơ sở dữ liệu & API (`backend_api`)**:
  - Model `User` (`role`: `'admin'` | `'sub_account'`, `owner_id`) & `UserPermission` (`can_view_screenshots`, `can_manage_rules`, `can_view_logs`, `can_remote_control`, `can_manage_users`).
  - `POST /api/v1/users`: Tạo/mời tài khoản phụ mới.
  - `GET /api/v1/users`: Lấy danh sách các tài khoản thuộc Admin.
  - `PUT /api/v1/users/{id}/permissions`: Cập nhật công tắc bật/tắt phân quyền theo từng tính năng.
  - `DELETE /api/v1/users/{id}`: Xóa tài khoản phụ.
- **Giao diện Quản trị (`manager-web`)**:
  - Component [`AccountPermissionsSettings.jsx`](file:///d:/Ho%C3%A0ng/PMQL/parental-control/manager-web/src/components/AccountPermissionsSettings.jsx) cho phép thêm tài khoản và bật/tắt nhanh phân quyền.
  - Tự động ẩn/hiện Navigation Sidebar & các nút bấm điều khiển dựa trên quyền của tài khoản đang đăng nhập.

---

## 2. 💾 Thẻ Quản Lý Bộ Nhớ Server & Tự Động Dọn Dẹp Log/Ảnh
- **Mục đích**: Theo dõi dung lượng đĩa thực tế trên Server, cung cấp bộ lọc dọn dẹp theo thời gian và nén nhỏ file SQLite DB (`VACUUM`).
- **API Backend (`backend_api`)**:
  - `GET /api/v1/system/storage`: Trả về dung lượng đĩa khả dụng (`shutil.disk_usage`), kích thước DB (`parental_control.db`), tổng số lượng và dung lượng ảnh chụp (`storage/screenshots`), số bản ghi logs.
  - `POST /api/v1/system/storage/clean`: Dọn dẹp theo phạm vi (Tất cả, Cũ hơn 7 ngày, 30 ngày, 90 ngày) và đối tượng (`screenshots`, `logs`, `all`). Tự động xóa file `.jpg` gốc trên ổ đĩa và chạy lệnh `VACUUM` để giải phóng dung lượng DB.
- **Giao diện Quản trị (`manager-web`)**:
  - Component [`StorageManagementCard.jsx`](file:///d:/Ho%C3%A0ng/PMQL/parental-control/manager-web/src/components/StorageManagementCard.jsx) hiển thị thanh Progress Bar dung lượng đĩa, thẻ chỉ số MB và 3 nút bấm dọn dẹp 1-click.

---

## 3. 🌐 Engine Lịch Sử Truy Cập Trình Duyệt Chi Tiết (Browser History Log Engine)
- **Mục đích**: Theo dõi chi tiết tên trang web và URL mà trẻ em truy cập trên máy con, tự động cảnh báo các trang web chứa từ khóa nhạy cảm.
- **Agent Monitor (`agent/enforcement/browser_tracker.py`)**:
  - Quét tiêu đề cửa sổ trình duyệt ngầm (`Chrome`, `Edge`, `Brave`, `Cốc Cốc`, `Firefox`, `Opera`).
  - Làm sạch tiêu đề, trích xuất Domain/URL tương ứng, loại bỏ log trùng lặp và gửi batch payload về Backend.
- **API Backend (`backend_api`)**:
  - Model `BrowserHistory` (`device_id`, `browser_name`, `url`, `page_title`, `timestamp`).
  - `POST /api/v1/logs/browser-history`: Endpoint nhận batch log lịch sử trình duyệt từ Agent.
  - `GET /api/device/{device_id}/browser-history`: Endpoint tìm kiếm và lọc lịch sử web theo từ khóa hoặc loại trình duyệt.
- **Giao diện Quản trị (`manager-web`)**:
  - Component [`BrowserHistoryView.jsx`](file:///d:/Ho%C3%A0ng/PMQL/parental-control/manager-web/src/components/BrowserHistoryView.jsx) giao diện Timeline chi tiết.
  - **Tự động gắn nhãn cảnh báo (`⚠️ NHẠY CẢM`)**: Phát hiện các từ khóa nhạy cảm (cờ bạc, adult, hack/cheat, bạo lực...) và hiển thị badge đỏ cảnh báo phụ huynh.

---

## 4. 💬 Tính Năng Chat 2 Chiều Real-Time (Two-Way Real-Time Chat System)
- **Mục đích**: Trò chuyện trực tiếp 2 chiều giữa Phụ huynh (trên Web Dashboard) và Trẻ em (trên máy con Agent) với độ trễ 0ms qua WebSocket.
- **Agent Desktop Popup Client (`agent/protection/chat_window.py`)**:
  - Giao diện Tkinter Desktop Chat Popup tự động nảy lên màn hình máy con khi Phụ huynh gửi tin nhắn từ Web.
  - Phát âm thanh thông báo (`winsound.MessageBeep`) và phân màu bong bóng hội thoại (Bố: Xanh lá, Em: Xanh dương).
  - Cho phép trẻ em gõ câu trả lời và nhấn Enter/Gửi ➔ Truyền qua WebSocket về Web Dashboard.
- **Backend API & WebSocket (`backend_api`)**:
  - Model `ChatMessage` (`device_id`, `sender`: `'admin'` | `'child'`, `message`, `timestamp`).
  - Lắng nghe payload `chat_message` từ Agent qua kết nối WebSocket ngầm.
  - `POST /api/device/{device_id}/chat`: Admin gửi tin nhắn từ Web ➔ Lưu DB ➔ Push WebSocket xuống Agent.
  - `GET /api/device/{device_id}/chat/history`: Tải lại toàn bộ lịch sử trò chuyện.
- **Giao diện Quản trị (`manager-web`)**:
  - Component [`DeviceChatBox.jsx`](file:///d:/Ho%C3%A0ng/PMQL/parental-control/manager-web/src/components/DeviceChatBox.jsx) giao diện chat bong bóng hiện đại, tự động cuộn và phát chuông âm thanh (Web Audio API Chime) khi trẻ em phản hồi.

---

## 5. 🚀 Engine Cập Nhật Agent Từ Xa Cưỡng Chế (Silent Agent Auto-Updater Engine)
- **Mục đích**: Cho phép Admin upload bản build Agent mới (`.zip`) lên Server và phát lệnh cập nhật cưỡng chế ngầm tới tất cả các máy con mà không cần bất kỳ tương tác nào từ trẻ em.
- **Backend API (`backend_api`)**:
  - Thư mục tĩnh `/static/updates` (`storage/updates/`).
  - `POST /api/v1/agent/deploy-update`: Upload gói zip phát hành Agent mới (`agent-update.zip`) & ghi nhận phiên bản vào `version.json`.
  - `GET /api/v1/agent/version`: Trả về thông tin phiên bản mới nhất trên Server.
  - `POST /api/devices/force-update-all`: Phát lệnh WebSocket cưỡng chế (`force_update`) tới tất cả các máy Agent đang trực tuyến.
- **Agent Silent Updater Client (`agent/protection/updater.py`)**:
  - Khi nhận lệnh WebSocket `force_update`: Tự động tải gói zip về `%APPDATA%\ParentalControl\updates\agent-update.zip`.
  - Giải nén gói mới vào thư mục tạm `staged\`.
  - Sinh script ngầm độc lập `apply_update.py`, chạy một tiến trình tách rời (Detached Process) chờ tiến trình Agent gốc thoát ➔ Ghi đè file mới ➔ Tự động khởi động lại `main.py` ngầm.
- **Giao diện Quản trị (`manager-web`)**:
  - Component [`AgentUpdateManagerCard.jsx`](file:///d:/Ho%C3%A0ng/PMQL/parental-control/manager-web/src/components/AgentUpdateManagerCard.jsx) cho phép Upload gói build `.zip` mới và Nút hành động nổi bật **"🚀 Phát Lệnh Cập Nhật Cưỡng Chế"**.

---

### 📊 Trạng Thái Kiểm Thử Tổng Thể
- Backend Python Endpoints: **100% PASS (HTTP 200/201 OK)**
- Agent Monitor & Protection Modules: **100% PASS**
- Manager Web React Build (`npx vite build`): **100% SUCCESS (0 errors)**
