# 🛡️ Parental Control System v2.0 (Local-First Architecture)

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Production-brightgreen?logo=vercel)](https://manager-web-plum.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.1-646CFF?logo=vite)](https://vitejs.dev)
[![Supabase](https://img.shields.io/badge/Supabase-Database%20%26%20Storage-3FCF8E?logo=supabase)](https://supabase.com)

Hệ thống quản lý và giám sát thiết bị máy tính **Parental Control System v2.0**, xây dựng theo kiến trúc **Local-First (Ưu tiên lưu trữ và vận hành dưới máy cục bộ)**, giúp hệ thống luôn hoạt động liên tục ngay cả khi mất kết nối Internet, tự động đồng bộ khi có mạng.

---

## 🌟 Tính Năng Nổi Bật

### 🖥️ 1. Agent Giám Sát Cục Bộ (Python Agent - Windows)
- 🔒 **Màn hình khóa bảo vệ (Screen Blocker):** Tự động khóa máy khi quá giờ cho phép hoặc ngoài thời gian quy định, hỗ trợ mở khóa mật khẩu trực tiếp.
- 📸 **Chụp ảnh màn hình tối ưu (WebP Screenshots):** Chụp ảnh tức thì từ Web Dashboard hoặc theo chu kỳ. Sử dụng định dạng WebP nén cao và quản lý bộ nhớ RAM thread-safe.
- ⚡ **Kiểm tra mạng Mức 2 (HTTP Latency Checker):** Đo độ trễ HTTP RTT chính xác tới Supabase (DNS -> TCP -> TLS -> HTTP). Tự động phân loại `good`, `slow`, `down` để điều chỉnh tần suất sync.
- 🛡️ **Watchdog Supervisor & Safe Rollback:** Tiến trình giám sát tự động khôi phục khi Core Agent gặp sự cố. Hỗ trợ cưỡng chế cập nhật từ xa (`force_update`) với cơ chế sao lưu (Backup) và tự động Rollback an toàn nếu bản cập nhật lỗi.
- 💾 **Cơ sở dữ liệu SQLite Local:** Ghi log cục bộ khi mất mạng và tự động đẩy đồng bộ lên Cloud khi kết nối mạng phục hồi.

### 🌐 2. Web Dashboard Quản Lý (React 19 + Vite)
- 🎨 **Giao diện Geist SaaS Premium:** Thiết kế Dark Mode sang trọng, hiển thị mượt mà trên Desktop và Điện thoại di động.
- 📱 **Mobile Bottom Navigation:** Thanh điều hướng cảm ứng thông minh trên di động với đầy đủ Icon và khả năng cuộn ngang mượt mà.
- ⏱️ **Kiểm soát thời gian linh hoạt:** Thiết lập khung giờ được phép sử dụng máy theo từng ngày trong tuần hoặc giới hạn tổng số giờ trong ngày.
- 🚫 **Quản lý danh sách chặn (Blacklist):** Chặn ứng dụng và trang web theo tên miền hoặc từ khóa.
- 🤖 **AI Phân tích thói quen:** Phân tích tỷ lệ thời gian Học tập vs Giải trí dựa trên tiến trình đang mở.
- 💬 **Chat 2 chiều tức thì:** Trò chuyện trực tiếp giữa Quản trị viên và thiết bị được quản lý.
- 📍 **Đồng bộ trạng thái Online Đa nguồn:** Tự động xác minh kết nối dựa trên Heartbeat, Ảnh chụp màn hình và Log cửa sổ hoạt động.

---

## 📂 Cấu Trúc Dự Án

```text
parental-control/
├── agent/                         # Python Agent (Chạy trên Windows)
│   ├── core_agent.py              # Bộ não điều phối chính của Agent
│   ├── watchdog_updater.py        # Tiến trình Giám sát & Tự động Rollback
│   ├── main.py                    # Entry point chính (Mặc định Watchdog)
│   ├── monitor/                   # Các module giám sát
│   │   ├── blocker.py             # Khóa màn hình an toàn
│   │   ├── screenshot.py          # Chụp ảnh WebP thread-safe
│   │   ├── network_checker.py     # Đo HTTP Latency RTT chính xác
│   │   ├── command_listener.py    # Lắng nghe lệnh từ Web Dashboard
│   │   ├── schedule_checker.py   # Kiểm tra lịch học tập
│   │   └── chat_client.py         # Nhận tin nhắn chat
│   ├── storage/                   # Lưu trữ & Đồng bộ
│   │   ├── local_db.py            # SQLite Local Database (Thread-safe)
│   │   └── sync_worker.py         # Worker đồng bộ dữ liệu hàng loạt
│   └── utils/                     # Tiện ích mở rộng
│       ├── config.py              # Cấu hình thiết bị & Supabase
│       ├── logger.py              # Nhật ký log
│       └── telegram_notify.py     # Gửi thông báo Telegram khẩn
│
├── manager-web/                   # Web Dashboard (React 19 + Vite)
│   ├── src/                       # Mã nguồn Frontend
│   │   ├── App.jsx                # Component chính toàn bộ ứng dụng
│   │   ├── components/            # Các UI Component phụ trách từng tab
│   │   │   ├── layout/            # Sidebar, Header, MobileNav
│   │   │   ├── overview/          # MetricCard, AI Analysis
│   │   │   ├── process/           # ProcessTable, ProcessCardList
│   │   │   └── schedule/          # ScheduleTable, ScheduleCardList
│   │   ├── lib/                   # Utilites & Google Sheet Parser
│   │   └── supabase.js            # Supabase Client SDK
│   ├── dist/                      # Bản đóng gói Production tệp tĩnh
│   └── package.json               # Thư viện & Scripts
│
├── vercel.json                    # Cấu hình tự động Deploy lên Vercel Cloud
└── README.md                      # Tài liệu hướng dẫn dự án
```

---

## 🚀 Hướng Dẫn Cài Đặt & Vận Hành

### 1. Khởi chạy Web Dashboard (`manager-web`)

```bash
# Di chuyển vào thư mục manager-web
cd manager-web

# Cài đặt các thư viện phụ thuộc
npm install

# Khởi chạy môi trường phát triển (Development)
npm run dev

# Đóng gói bản Production
npm run build
```

---

### 2. Khởi chạy Python Agent (`agent`)

#### Yêu cầu môi trường:
- Windows 10/11
- Python 3.11+

#### Cài đặt thư viện:
```bash
pip install supabase pillow requests psutil
```

#### Cấu hình môi trường (`agent/utils/config.py`):
```python
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-or-service-key"
DEVICE_NAME = "May_Em_Trai"
```

#### Khởi chạy Agent:
```bash
# Khởi chạy chế độ Production (chạy qua Watchdog Supervisor):
python agent/main.py

# Khởi chạy chế độ Debug (chạy trực tiếp Core Agent):
python agent/main.py --core-only
```

---

## 🔗 Liên Kết Live Production

- 🌐 **Web Dashboard Production:** [https://manager-web-plum.vercel.app](https://manager-web-plum.vercel.app)
- 📦 **GitHub Repository:** [https://github.com/lam123lam76-png/parental-control.git](https://github.com/lam123lam76-png/parental-control.git)

---

## 📜 Giấy Phép & Bảo Mật
Dự án được thiết kế chuyên biệt cho hệ thống quản lý thiết bị gia đình (Parental Control System). Toàn bộ dữ liệu được bảo mật qua lớp xác thực Supabase Row Level Security (RLS) và mã hóa kết nối HTTPS.
