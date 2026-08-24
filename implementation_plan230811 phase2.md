# Phase 2: Xây dựng lại Desktop Agent — Implementation Plan

> Mục tiêu: Đập bỏ code Agent cũ (Supabase polling, DEVICE_NAME-based identity) và xây lại từ đầu theo kiến trúc MVP mới: **WebSocket Decoupled Streams, DPAPI Token, Local-First SQLite + HMAC Fail-Closed**.

---

## User Review Required

> [!IMPORTANT]
> **Toàn bộ các file cũ trong `agent/`** (như `core_agent.py`, `supabase.py`, `storage/`, `monitor/`) sẽ bị **ghi đè hoàn toàn**. Code cũ dùng Supabase client, DEVICE_NAME làm identity, polling loop 60s — tất cả sẽ bị thay thế bằng kiến trúc WebSocket + 3-Stream mới.

> [!WARNING]
> **Tương thích ngược = 0.** Agent cũ không thể giao tiếp với Backend mới (Phase 1). Đây là quyết định có chủ đích — "đập đi xây lại".

## Open Questions

> [!IMPORTANT]
> 1. **DPAPI vs đơn giản hóa:** Có muốn implement DPAPI thật (dùng `win32crypt.CryptProtectData`) ngay trong Phase 2, hay tạm dùng file encrypted đơn giản rồi nâng cấp sau?
> 2. **Blocker UI:** Có muốn giữ lại cơ chế blocker nhiều màn hình (multi-monitor) từ code cũ, hay xây mới?
> 3. **Screenshot:** Có muốn đưa tính năng chụp ảnh màn hình vào Phase 2, hay để Phase 3?

---

## Tinh thần thiết kế (Từ `kinh-nghiem.html` & `docs.html`)

Mọi quyết định code đều tuân thủ **8 bài học xương máu**:

| Bài học | Nguyên tắc | Cách áp dụng trong code |
|---------|-----------|------------------------|
| BL1: Device Name ngây thơ | **DPAPI > .env** | Token lưu bằng `win32crypt.CryptProtectData`, không bao giờ plaintext |
| BL2: Windows Service viển vông | **User-mode + Watchdog** | Chạy ẩn user-mode, Watchdog kép restart khi bị kill |
| BL3: Alert Fatigue | **Graceful Shutdown Signal** | Bắt `SIGTERM`, Windows Power Events → gửi "Tạm biệt" hợp lệ |
| BL4: Bẫy hồi tố | **Detection > Prevention** | Log event startup, cross-check Windows Event Log (v2.0) |
| BL5: Ống API lẩu thập cẩm | **3 Luồng tách biệt** | WebSocket (Heartbeat), HTTP Alert Queue, HTTP Batch Logs |
| BL6: Database MVP | **In-memory + Batching** | Không ghi `last_seen_at` mỗi giây, batch 5 phút |
| BL7: Pairing by Login | **Màn hình đăng nhập 1 lần** | Agent hiện form → Parent login → Token → form biến mất |
| BL8: Offline Fail-Closed | **HMAC Signature** | SQLite rules ký HMAC, sai chữ ký → khóa đen toàn bộ |

---

## Proposed Changes

### Cấu trúc thư mục mới: `agent/`

```
agent/
├── main.py                      # Entry point: khởi tạo, spawn threads
├── config.py                    # Constants, env loading, paths
├── credential_store.py          # DPAPI token storage (win32crypt)
│
├── communication/               # 3-Stream Communication Engine
│   ├── __init__.py
│   ├── ws_client.py             # Luồng 1: WebSocket client (Heartbeat + Commands)
│   ├── alert_sender.py          # Luồng 2: HTTP Alert Queue (Retry 3s)
│   └── log_uploader.py          # Luồng 3: Batch Log Upload (5 phút)
│
├── enforcement/                 # Rule Enforcement Engine
│   ├── __init__.py
│   ├── process_monitor.py       # psutil: quét tiến trình, active window
│   ├── app_enforcer.py          # Chặn app cấm (taskkill)
│   ├── web_enforcer.py          # Chặn web cấm (kill browser tab)
│   └── time_enforcer.py         # Kiểm tra khung giờ + daily limit
│
├── local_store/                 # Local-First Storage
│   ├── __init__.py
│   ├── local_db.py              # SQLite wrapper (rules cache, pending logs)
│   └── integrity.py             # HMAC signature cho rules (Fail-Closed)
│
├── protection/                  # Self-Protection Layer
│   ├── __init__.py
│   ├── watchdog.py              # Watchdog kép: restart agent khi bị kill
│   ├── blocker.py               # Màn hình khóa multi-monitor (tkinter)
│   └── shutdown_handler.py      # Graceful shutdown: bắt SIGTERM, Power Events
│
└── requirements.txt             # Dependencies
```

---

### Component 1: Core Infrastructure

#### [NEW] `config.py`
- Constants: `INSTALL_DIR`, `HEARTBEAT_INTERVAL` (15s), `LOG_BATCH_INTERVAL` (300s), `ALERT_RETRY_INTERVAL` (3s)
- Load `.env` hoặc hardcoded backend URL
- `BACKEND_URL` = `http://server:8000` (hoặc `wss://server:8000`)

#### [NEW] `credential_store.py`
- **`save_token(token: str)`** — Mã hóa token bằng `win32crypt.CryptProtectData()`, lưu file binary tại `%APPDATA%\ParentalControl\device.cred`
- **`load_token() → str`** — Giải mã bằng `CryptUnprotectData()`
- **`has_token() → bool`** — Kiểm tra đã pairing chưa
- **`get_device_id() → str`** — Đọc device_id đã lưu
- Fallback: Nếu không có `win32crypt` (dev mode), dùng file JSON obfuscated

---

### Component 2: 3-Stream Communication Engine

#### [NEW] `communication/ws_client.py` — Luồng 1: Tuyến Sinh Tử
```
Heartbeat + Nhận lệnh tức thì (Push từ Server)
```
- **Kết nối:** `wss://server/ws/device/{device_id}?token={secret_token}`
- **Heartbeat loop:** Gửi `{"type": "heartbeat"}` mỗi 15s
- **Nhận lệnh:** Listen for `{"type": "command", "command": "kill_process", "payload": {...}}`
- **Reconnect:** Exponential Backoff (1s → 2s → 4s → 8s → 16s → max 60s)
- **SYNC_STATE:** Khi reconnect thành công, gửi event đồng bộ rules mới
- **Callback:** `on_command_received(command)` → dispatch tới enforcement engine

#### [NEW] `communication/alert_sender.py` — Luồng 2: Tuyến Báo Động
```
HTTP POST /api/alerts — Retry Queue (At-least-once)
```
- **In-memory Queue:** `queue.Queue()` thread-safe
- **Worker thread:** Dequeue → POST → Nếu fail → sleep 3s → retry
- **API:** `alert_sender.send_alert(device_id, alert_type, message)`
- **Offline:** Queue tích lũy trong RAM, đẩy hết khi có mạng lại (Ưu tiên 2 sau WebSocket)

#### [NEW] `communication/log_uploader.py` — Luồng 3: Tuyến Xe Tải
```
HTTP POST /api/logs/batch — Batch Upload mỗi 5 phút
```
- **Đọc SQLite:** Lấy tối đa 100 pending logs
- **Upload:** POST batch lên server
- **Cleanup:** Xóa records đã upload khỏi SQLite
- **Priority:** Thấp nhất — chỉ chạy khi Luồng 1 + 2 đã ổn định
- **Offline:** Logs tích lũy trong SQLite, upload khi có mạng

---

### Component 3: Local-First Storage (SQLite + HMAC)

#### [NEW] `local_store/local_db.py`
- **Bảng `cached_rules`:** Lưu rules tải từ server (app/web/time) — dùng khi offline
- **Bảng `pending_logs`:** Ghi log process, active window chờ upload
- **Bảng `pending_alerts`:** Ghi alerts chờ gửi khi offline
- **Bảng `device_state`:** Lưu device_id, last_sync timestamp

#### [NEW] `local_store/integrity.py` — HMAC Fail-Closed
- **`sign_rules(rules_data, secret_token) → hmac_hex`** — Tạo chữ ký HMAC-SHA256
- **`verify_rules(rules_data, hmac_hex, secret_token) → bool`** — Kiểm tra chữ ký
- Khi server push rules → Agent lưu rules + HMAC vào SQLite
- Khi offline đọc rules → Tính lại HMAC → Nếu sai → **FAIL-CLOSED: Khóa đen toàn bộ**

---

### Component 4: Enforcement Engine

#### [NEW] `enforcement/process_monitor.py`
- `get_running_processes(limit=30)` — Dùng `psutil.process_iter()`
- `get_active_window_info()` — Dùng `win32gui.GetForegroundWindow()`
- Trả về: `{"process_name", "window_title", "pid"}`

#### [NEW] `enforcement/app_enforcer.py`
- Đọc rules từ `local_db` (cached) hoặc từ in-memory (nếu online)
- So khớp `process_name` với rule `type='app'`
- Nếu `is_banned=True` → `taskkill /F /PID {pid}` + gửi Alert (Luồng 2)
- Nếu `daily_limit_minutes` vượt quá → block

#### [NEW] `enforcement/web_enforcer.py`
- Đọc `window_title` từ trình duyệt → extract URL/domain
- So khớp với rules `type='web'`
- Nếu banned → kill browser process + Alert

#### [NEW] `enforcement/time_enforcer.py`
- Đọc rules `type='time'` từ cache
- Kiểm tra `day_of_week` + `allowed_start` / `allowed_end`
- Nếu ngoài giờ → trigger Blocker

---

### Component 5: Self-Protection Layer

#### [NEW] `protection/watchdog.py`
- Process A chạy Agent, Process B giám sát A
- Nếu A chết → B restart A sau 10s
- Nếu B chết → A restart B
- **Không dùng Windows Service** (Bài học 2: MVP 80/20)

#### [NEW] `protection/blocker.py`
- Tkinter fullscreen đen trên **tất cả màn hình** (`win32api.EnumDisplayMonitors`)
- Mở khóa bằng: mật khẩu Admin HOẶC remote unlock từ server
- Nút "Tắt máy" cho trẻ
- Disable Task Manager shortcut (best-effort, user-mode)

#### [NEW] `protection/shutdown_handler.py`
- Bắt `signal.SIGTERM`, `signal.SIGINT`
- Bắt Windows Power Event (`WM_POWERBROADCAST`) — Sleep/Shutdown
- Khi shutdown hợp lệ → gửi "Tạm biệt" qua WebSocket trước khi exit
- Backend phân biệt: **Tạm biệt hợp lệ** vs **Mất kết nối đột ngột** (Bài học 3)

---

### Component 6: Entry Point

#### [MODIFY] `main.py`
```python
# Simplified flow:
1. Load config
2. Check credential_store → if no token → show Pairing Login UI
3. Init local_db (SQLite)
4. Verify rules integrity (HMAC) → Fail-Closed if tampered
5. Start Thread 1: ws_client (Luồng 1 — Heartbeat + Commands)
6. Start Thread 2: alert_sender (Luồng 2 — Alert Queue)
7. Start Thread 3: log_uploader (Luồng 3 — Batch Upload)
8. Start Thread 4: watchdog (Self-protection)
9. Register shutdown_handler (Graceful exit)
10. MAIN LOOP (every 15s):
    - Quét tiến trình (process_monitor)
    - Enforce app rules (app_enforcer)
    - Enforce web rules (web_enforcer)
    - Check time restrictions (time_enforcer)
    - Log active window → local_db
```

---

## Verification Plan

### Automated Tests
```bash
# Test 1: Agent kết nối WebSocket → gửi Heartbeat → nhận ACK
python -m pytest tests/test_ws_connection.py

# Test 2: Alert Queue retry khi server down
python -m pytest tests/test_alert_retry.py

# Test 3: HMAC integrity → tamper detection
python -m pytest tests/test_hmac_integrity.py
```

### Manual Verification
1. Chạy Agent → kiểm tra WebSocket kết nối + Heartbeat trên Backend log
2. Mở game cấm → kiểm tra Agent kill process + Alert xuất hiện trên Backend
3. Rút Wi-Fi → kiểm tra Agent vẫn chặn game (Local-First)
4. Sửa lén SQLite → kiểm tra Fail-Closed (màn hình khóa đen)
5. Kill Agent process → kiểm tra Watchdog restart sau 10s

---

Bấm **Proceed** để bắt đầu code Phase 2.
