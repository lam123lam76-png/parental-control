# 🛠️ Bộ Công Cụ Kiểm Tra — Parental Control System

Thư mục này chứa các công cụ để kiểm tra và đánh giá độ ổn định của hệ thống.

---

## 📁 Danh Sách Công Cụ

| File | Dành cho | Mô tả |
|------|----------|-------|
| `check_system.bat` | **Người dùng** | Kiểm tra nhanh — double-click để chạy |
| `test_api.py` | Dev | Test toàn bộ API Backend |
| `test_agent_health.py` | Dev & Người dùng | Kiểm tra Agent trên máy Windows |
| `run_all_tests.bat` | Dev | Chạy tất cả test một lần |

---

## 👤 Hướng Dẫn Cho Người Dùng (Không Cần Biết Kỹ Thuật)

### Kiểm tra nhanh:
1. Tìm file **`check_system.bat`** trong thư mục `tools/`
2. **Double-click** vào file đó
3. Đọc kết quả:
   - ✅ = Tốt
   - ❌ = Có vấn đề, xem hướng dẫn sửa bên dưới
   - ⚠️ = Cần lưu ý nhưng vẫn hoạt động

### Nếu thấy ❌ Agent KHÔNG chạy:
- Tìm file `run_agent.bat` ở thư mục gốc và double-click
- Hoặc khởi động lại máy tính

### Nếu thấy ❌ Không có Internet:
- Kiểm tra dây mạng hoặc Wi-Fi
- Thử restart router

---

## 👨‍💻 Hướng Dẫn Cho Dev

### Yêu cầu:
```
Python 3.9+
pip install requests psutil python-dotenv
```

### Test API Backend:
```bash
# Tự động đọc URL và key từ .env
python tools/test_api.py

# Chỉ định thủ công
python tools/test_api.py --url http://myserver:8000 --key MY_API_KEY
```

### Test Agent trên máy Windows:
```bash
# Chạy trên chính máy đang cài Agent
python tools/test_agent_health.py
```

### Chạy tất cả test:
```bash
# Windows
tools\run_all_tests.bat
```

### Dùng trong CI/CD:
```bash
python tools/test_api.py
# Exit code 0 = tất cả pass, 1 = có fail
```

---

## 📋 Các Lỗi Phổ Biến & Cách Sửa

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| ❌ Agent KHÔNG chạy | Tiến trình bị tắt | Chạy `run_agent.bat` hoặc restart máy |
| ❌ File .env không tồn tại | Chưa cấu hình | Copy `.env.example` → `.env`, điền giá trị |
| ❌ Kết nối Backend thất bại | Backend chưa chạy | Chạy `docker compose up` hoặc `run_backend.bat` |
| ❌ API_KEY chưa có | Thiếu cấu hình | Thêm `API_KEY=xxx` vào `agent/.env` |
| ⚠️ Watchdog không chạy | Bình thường khi debug | Dùng `python main.py` thay vì `--core-only` |

---

## 🔄 Lịch Chạy Test Đề Xuất

| Khi nào | Chạy gì |
|---------|---------|
| Sau khi cài Agent mới | `check_system.bat` |
| Trước khi deploy Backend | `python test_api.py` |
| Sau khi cập nhật Agent | `test_agent_health.py` |
| Maintenance định kỳ (1 tuần/lần) | `run_all_tests.bat` |
| Khi có báo cáo lỗi từ người dùng | `check_system.bat` trước |

---

*Tạo bởi Audit Agent — 2026-08-18*
