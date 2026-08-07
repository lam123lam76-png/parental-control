# Parental Control — Self‑Hosted (Handover README)

Phiên bản: 2026-08-07

Người soạn: AI assistant (Copilot CLI runtime in VS Code)

Mục đích tài liệu

Tài liệu này là bản Handover (bàn giao) chi tiết cho dự án "parental-control". Mục tiêu: cung cấp đầy đủ bối cảnh, kiến trúc, thay đổi đã thực hiện, hướng dẫn vận hành và bước tiếp theo để một AI/Agent hoặc kỹ sư khác có thể tiếp quản và tiếp tục phát triển hệ thống mà không bị lãng phí thời gian dò tìm.

---

1) Tổng quan dự án (Project Overview)

Mục đích hệ thống
- Hệ thống Parental Control giám sát và (tuỳ vào cấu hình) kiểm soát hành vi sử dụng máy tính của trẻ em: thu thập tiến trình đang chạy, ghi nhật ký hoạt động, chụp ảnh màn hình, lưu lịch sử trình duyệt, gửi/nhận lệnh điều khiển, và hiển thị dashboard quản trị.
- Hướng đi hiện tại: chuyển từ Supabase + Vercel sang mô hình Self‑Hosted (chạy trên máy gia đình / máy chủ nội bộ) để bảo mật dữ liệu, giảm chi phí và giảm độ trễ nội bộ.

Các thành phần chính
- Agent (Python): chạy trên máy con (Windows được ưu tiên) — thu thập dữ liệu, upload ảnh, polling lệnh, thực thi lệnh và gửi heartbeat.
- Backend API (FastAPI): REST API self-hosted thay thế Supabase. Cung cấp endpoints: /api/query, /api/rpc/{procedure}, /api/storage/{bucket}/(upload|download|remove), /api/health, v.v.
- Database (PostgreSQL): lưu devices, logs, cấu hình, commands.
- Manager Web (React + Vite): dashboard dùng để xem trạng thái, gửi lệnh, quản lý quy tắc.

---

2) Kiến trúc & Môi trường Self‑Hosted (Architecture & Environment)

Kiến trúc hiện tại (Docker Compose)
- docker-compose.yml orchestrates 3 services chính:
  - db: postgres:15-alpine (port 5432)
  - backend: parental-control-backend (FastAPI) (port 8000)
  - frontend: parental-control-frontend (Nginx serving built manager-web) (port 4173 -> container:80)

Địa chỉ URL / Port mặc định
- Backend API: http://localhost:8000 (cũng có thể truy cập thông qua proxy của frontend: http://localhost:4173/api/...)
- Manager Web (dev): http://localhost:5173 (vite dev) hoặc khi chạy trong Docker: http://localhost:4173
- PostgreSQL: port 5432 (host)

File cấu hình môi trường (.env)
> Ghi chú bảo mật: repo hiện chứa các file .env mẫu và trong workspace này có các giá trị đã cấu hình. Những khóa (API keys / tokens) nhạy cảm hiện có trong workspace — giữ cẩn mật nếu chia sẻ.

- backend_api/.env (được docker-compose sử dụng)
  - API_KEY=732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7
  - DATABASE_URL=postgresql://pcuser:pcpass@db:5432/parental_control (compose thiết lập)
  - STORAGE_PATH=/app/storage

- manager-web/.env (dùng khi chạy Vite hoặc build)
  - VITE_API_BASE_URL=http://localhost:8000
  - VITE_API_KEY=732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7

- agent/.env (agent chạy trên máy đích; tên biến giữ tương thích với code hiện tại)
  - SUPABASE_URL=http://localhost:8000
  - SUPABASE_KEY=732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7
  - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AGENT_PASSWORD, DEVICE_NAME, SEND_INTERVAL (các biến khác theo .env.example)

---

3) Tiến trình đã thực hiện & Cấu hình quan trọng (Progress & Patch History)

Tóm tắt các bước đã hoàn thành
- Backend FastAPI đã được phát triển để thay thế dòng kênh Supabase. Endpoints chính:
  - POST /api/query — execute CRUD-like queries against SQLAlchemy models
  - POST /api/rpc/{procedure} — execute server-side procedures (ví dụ clean_old_logs)
  - Storage endpoints: POST /api/storage/{bucket}/upload, GET /api/storage/{bucket}/download, POST /api/storage/{bucket}/remove
  - GET /api/health — health check
- Docker Compose đã được cấu hình để chạy `db`, `backend`, `frontend` cùng nhau.
- Frontend manager-web được đóng gói bằng Dockerfile và Nginx config; frontend proxy `/api` và `/storage` tới backend container.
- Agent packaging: đã tạo agent-install.zip (trong agent-release/) chứa mã agent và script cài đặt (install_agent.sh / install_agent.bat) cùng .env.example đã mask.

Các sửa đổi/patch chi tiết (vị trí & nội dung)
- Authentication change: thống nhất sang Bearer token
  - Reason: self-hosted API dùng API_KEY so với Supabase token; agent & frontend cần gửi header Authorization dạng Bearer.
  - Files patched:
    - agent/supabase.py
      - Mục đích: supabase wrapper (local) đã được cập nhật để gắn header Authorization = f"Bearer {key}" khi khởi tạo client.
      - Vị trí: agent/supabase.py (class SupabaseClient.__init__)
    - manager-web/src/supabase.js
      - Mục đích: thay thế Supabase SDK bằng một client HTTP đơn giản; hàm _authHeaders() trả về Authorization: Bearer ${this.apiKey} và Content-Type khi cần; baseUrl được lấy từ VITE_API_BASE_URL.
      - Vị trí: manager-web/src/supabase.js
    - backend_api/main.py
      - Mục đích: verify_api_key() chấp nhận header Authorization: Bearer <token> hoặc x-api-key header; so khớp với API_KEY trong backend_api/.env.

- Frontend fixes
  - manager-web/src/App.jsx: đã sửa một runtime error (tham chiếu biến PromiseResults) bằng cách sử dụng đúng biến trả về từ Promise.all; đảm bảo UI không blank.
  - manager-web/Dockerfile + manager-web/nginx.conf: thêm để serve static build và proxy /api.

- Docker Compose
  - docker-compose.yml: thêm service frontend, kết nối internal network; backend/db/volumes/restart policies đã được xác định.

Kết quả kiểm tra
- Khi chạy stack: `docker compose ps` hiển thị frontend, backend, db đang Up.
- Kiểm tra health endpoint: GET /api/health trả về {"data":{"status":"ok"},"error":null}.
- Backend logs cho thấy POST /api/query trả 200 OK (frontend đã gửi request).

---

4) Hướng dẫn chạy & Thao tác hệ thống (Run & Build Instructions)

A. Chuẩn bị môi trường
- OS: Ubuntu Server 22.04 / 26.04 hoặc Windows + WSL2
- Cài Docker & Docker Compose
- Clone repo, chuyển vào thư mục dự án

B. Khởi động toàn bộ stack (Docker)

```bash
# từ thư mục gốc của repo
docker compose build
docker compose up -d
# Kiểm tra trạng thái
docker compose ps
# Xem logs (backend)
docker compose logs --follow backend
```

C. Kiểm tra health endpoint

```bash
# trực tiếp tới backend
curl -s http://localhost:8000/api/health | jq
# hoặc qua frontend proxy
curl -s http://localhost:4173/api/health | jq
```

D. Chạy / build Manager Web (local dev)

```bash
cd manager-web
npm install
# dev
npm run dev -- --host 0.0.0.0 --port 5173
# build production
npm run build
# preview static
npm run preview
```

E. Cài & chạy Agent (máy con)

Windows (PowerShell):

```powershell
cd C:\path\to\agent
python -m venv venv
# nếu policy chặn script activation:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
# tạo .env từ .env.example và chỉnh sửa các giá trị: SUPABASE_URL, SUPABASE_KEY, DEVICE_NAME, AGENT_PASSWORD
copy .env.example .env
# chạy (Watchdog mode mặc định)
python main.py
# hoặc chạy core agent trực tiếp (debug):
python main.py --core-only
```

Linux / macOS:

```bash
cd ~/agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

F. Lưu ý PowerShell (Windows)
- Dùng single-quote `'...'` để tránh PowerShell mở rộng biến nội dung.
- Tránh dùng `&&` (bash); trong PowerShell nối lệnh bằng `;` hoặc chạy nhiều dòng.
- Nếu chạy script activation gặp chính sách, chạy `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` trong phiên PowerShell hiện tại.

---

5) Bước tiếp theo cần triển khai (Next Steps / Roadmap)

Ưu tiên ngắn hạn
1. Chạy agent thực tế trên máy con (bằng gói agent-install.zip hoặc thủ công) và xác nhận end-to-end: agent gửi heartbeat, dữ liệu devices xuất hiện trong DB, ảnh/screenshot upload tới storage và hiển thị trên UI.
2. Chạy test chức năng: gửi lệnh (system_commands) từ dashboard và quan sát agent thực thi, kiểm tra trạng thái command update (completed/failed).
3. Nếu gặp lỗi 401: kiểm tra `agent/.env` SUPABASE_KEY khớp `backend_api/.env` API_KEY; kiểm tra `agent/supabase.py` và `manager-web/src/supabase.js` gửi header `Authorization: Bearer <key>`.

Trung hạn / Ops
- Tạo systemd unit file mẫu cho agent (Linux) hoặc Windows service wrapper (NSSM) cho agent để tự khởi động và tự khôi phục.
- Thiết lập backup định kỳ cho Postgres (pg_dump) và sao lưu storage (ví dụ rsync đến NAS hoặc S3-compatible endpoint).
- Thiết lập HTTPS & reverse-proxy nếu cần truy cập từ xa (Nginx + Let's Encrypt) hoặc triển khai VPN (WireGuard) để bảo vệ API.

---

6) Troubleshooting nhanh (Checklist khi gặp lỗi)

- Blank UI / JS errors: kiểm tra DevTools Console, sửa `manager-web/src/App.jsx` và `manager-web/src/supabase.js`.
- Agent 401 Unauthorized: kiểm tra SUPABASE_KEY / API_KEY và header Bearer trên cả agent và frontend.
- Storage missing images: kiểm tra thư mục `backend_api/storage` và endpoint `/storage/<bucket>/<path>`.
- DB permission/volume: kiểm tra quyền filesystem cho `backend_api/postgres_data`.

---

7) Bản đồ file quan trọng (Quick map)

- backend_api/
  - main.py, database.py, models.py, schemas.py, .env, storage/
- manager-web/
  - src/, src/supabase.js, .env, Dockerfile, nginx.conf
- agent/
  - core_agent.py, main.py, watchdog_updater.py, supabase.py, requirements.txt, .env.example, monitor/
- docker-compose.yml
- agent-release/agent-install.zip (nếu còn tồn tại trong repo)

---

8) Ghi chú bàn giao (Final Handover Notes)

- Hiện trạng: stack chạy bằng Docker Compose, frontend được đóng gói và served bằng Nginx, health endpoint hoạt động, agent gói cài đặt đã được tạo.
- Bảo mật: API_KEY và token hiện có trong .env — không chia sẻ công khai.
- Nếu muốn, tôi có thể tiếp tục:
  - sửa/cố định mọi chỗ còn tham chiếu tới Supabase SDK (ví dụ `push_update.py`),
  - tạo systemd unit mẫu / Windows service wrapper cho agent,
  - thực hiện thử nghiệm E2E với agent chạy trên máy hiện tại và báo cáo kết quả chi tiết.

---

Nếu bạn muốn tôi cập nhật README thêm mục chi tiết như sample systemd unit, ví dụ payload cho /api/query, hoặc hướng dẫn rollback/backup chi tiết, hãy nói rõ phần muốn bổ sung và tôi sẽ thêm vào ngay.


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
