# HƯỚNG DẪN DEPLOY — Vercel + Supabase (parental-control)

> ⚠️ **QUY TẮC VÀNG:** Deploy API **BẮT BUỘC qua CLI từ thư mục `backend_api`**.
> **TUYỆT ĐỐI KHÔNG** redeploy qua Vercel Dashboard cho project API — gây lỗi **508 INFINITE_LOOP**.

---

## 1. Kiến trúc cloud (hiện tại)

```
Agent (máy con)
   │  poll /api/device/{id}/commands mỗi 5s  +  tải agent-update.zip từ R2
   ▼
quanlypc-api-backup.vercel.app   ←── API FastAPI (project Vercel "quanlypc-api-backup")
   │        │
   │        └─ Supabase Postgres (Singapore) — dữ liệu
   │        └─ Supabase Storage (bucket "screenshots") — ảnh chụp
   ▼
parental-control-sepia.vercel.app  ←── Web manager React (project "parental-control")
   │        │
   │        └─ /api/*  → rewrite → quanlypc-api-backup.vercel.app
   ▼
nguyentruclam.io.vn  ←── domain trỏ CNAME tới web Vercel
```

- **Không còn máy nhà.** Web + API + DB + Storage + phê duyệt Telegram + update agent đều từ cloud.
- R2 (`pub-68ac9fad65e94c8f886542276f2e490c.r2.dev`) = nguồn phát hành agent update (zip + version.json).

---

## 2. Hai project Vercel (PHÂN BIỆT RÕ — tránh 508)

| Project | Thư mục deploy | Nội dung | Framework |
|---|---|---|---|
| **`quanlypc-api-backup`** | `backend_api/` | FastAPI backend | Python (`api/index.py`) |
| **`parental-control`** | thư mục gốc repo | React web manager | Vite |

> Lý do 508: repo gốc có `vercel.json` build web; nếu deploy **nhầm project** (deploy API bằng vercel.json web hoặc redeploy dashboard) → Vercel thấy nhiều `vercel.json` → vòng lặp. Chỉ CLI + đúng thư mục.

---

## 3. Deploy BACKEND (API) — quan trọng nhất

### 3.1 Lần đầu
```bash
cd backend_api
vercel link          # chọn project "quanlypc-api-backup"
vercel --prod
```

### 3.2 Mỗi lần sửa backend
```bash
cd backend_api
vercel deploy --prod --yes
```
> Kết quả: `https://quanlypc-api-backup.vercel.app` (alias tự động trỏ bản mới).

### 3.3 Env vars bắt buộc cho API (Vercel → Settings → Environment Variables)
Đặt trên **Production**:

| Tên | Giá trị / nguồn | Ghi chú |
|---|---|---|
| `DATABASE_URL` | Supabase SG pooler (xem mục 5) | bắt buộc |
| `API_KEY` | *(bí mật riêng của server — KHÔNG dùng giá trị từng nằm trong repo, xem mục 7b)* | agent auth |
| `SUPABASE_PROJECT_URL` | `https://xqscnzdghjvgdozwfdbj.supabase.co` | storage |
| `SUPABASE_SERVICE_KEY` | service_role key (Secret) | storage upload/quota |
| `SUPABASE_STORAGE_BUCKET` | `screenshots` | mặc định đúng |
| `JWT_SECRET_KEY` | *(chuỗi ngẫu nhiên ≥ 48 ký tự — BẮT BUỘC, xem mục 7b)* | ký token đăng nhập web |
| `MASTER_UNLOCK_PASSWORD` | mật khẩu **mở khoá màn hình máy con** (không dùng để đăng nhập web) | xem mục 7c |
| `WEB_ADMIN_PASSWORD` | mật khẩu **đăng nhập web**, chỉ dùng khi tạo admin trên DB trống | xem mục 7c |
| `TELEGRAM_BOT_TOKEN` | *(token bot thật, KHÔNG ghi vào repo)* | bot cha |
| `TELEGRAM_CHAT_ID` | *(chat ID phụ huynh, phân tách bằng phẩy)* | các phụ huynh |
| `R2_ACCESS_KEY` / `R2_SECRET_KEY` | token R2 quyền Object Read & Write | phát hành agent update |

> ⚠️ Không đặt giá trị bí mật vào file này. Mọi token/key từng nằm trong repo phải coi
> như đã lộ và phải thu hồi (mục 7b).

> Supabase storage đọc env theo thứ tự: `SUPABASE_SERVICE_KEY` → `SUPABASE_SERVICE_ROLE_KEY` → `SUPABASE_SECRET_KEY`. Đặt ít nhất 1 trong 3.

> Env tự động: Vercel set sẵn `VERCEL`/`VERCEL_ENV` → code nhận biết đang chạy serverless (không bật poller getUpdates, UPDATES_DIR rơi về temp).

---

## 4. Deploy WEB (manager) — qua thư mục GỐC

### 4.1 Lần đầu / mỗi lần sửa web
```bash
# Từ THƯ MỤC GỐC repo (D:\Hoàng\PMQL\parental-control)
vercel deploy --prod --yes
```
> Kết quả alias: `nguyentruclam.io.vn` (web) + `parental-control-sepia.vercel.app`.

### 4.2 Web không cần env (chỉ static + rewrite)
- `vercel.json` (gốc) build `manager-web` rồi rewrite `/api/*`, `/ws/*`, `/static/*` → API.

---

## 5. Supabase — cấu hình

### 5.1 Kết nối (Singapore)
- Project ref: **`xqscnzdghjvgdozwfdbj`**
- Region: `ap-southeast-1`
- Connection string (pooler) — thay `[PASSWORD]`:
```
postgresql://postgres.xqscnzdghjvgdozwfdbj:[PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require
```
> Lấy `[PASSWORD]` từ Supabase → Project Settings → Database. Giá trị đang dùng trong `backend_api/.env`.

### 5.2 Storage — bucket screenshots
Tạo bucket (nếu chưa có) — chạy SQL trong Supabase → SQL Editor:
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('screenshots', 'screenshots', true, 52428800,
        ARRAY['image/png','image/jpeg','image/webp'])
ON CONFLICT (id) DO NOTHING;
```

### 5.3 Schema cần đảm bảo (migration tự động 1 phần)
Backend chạy `ensure_schema()` mỗi startup — tự thêm `pending_commands.delivered_at` và `process_logs.duration`. Tuy nhiên để chắc chắn, chạy SQL này 1 lần:
```sql
ALTER TABLE process_logs ADD COLUMN IF NOT EXISTS duration INTEGER DEFAULT 0;
UPDATE process_logs SET duration = 15 WHERE duration IS NULL OR duration = 0;
```

### 5.4 Bảng dữ liệu chính (đã tồn tại qua migration)
`parents`, `users`, `devices`, `pending_commands`, `screenshots`, `browser_history`, `process_logs`, `alerts`, `rules`, `telegram_settings`, `system_settings`, `pending_registrations`, v.v.

---

## 6. Telegram — webhook & bot

- Bot Telegram dùng cho phê duyệt đăng ký (tên bot xem trong BotFather). **Token không
  ghi vào tài liệu này** — đặt qua `TELEGRAM_BOT_TOKEN` trên Vercel hoặc nhập ở
  **Cài đặt → Telegram** trong web (lưu vào DB `telegram_settings`).
- Chat ID phụ huynh (nhiều, phân tách phẩy): nhập ở cùng chỗ, hoặc `TELEGRAM_CHAT_ID`.
- Webhook trỏ tới API:
  - URL: `https://quanlypc-api-backup.vercel.app/telegram/webhook`
  - Phải bật cả `message` lẫn `callback_query` (dùng JSON body):
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://quanlypc-api-backup.vercel.app/telegram/webhook",
       "allowed_updates":["message","callback_query"]}'
# kiểm tra:
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```
> ⚠️ Trước đây gặp lỗi bot im lặng vì `allowed_updates` chỉ có `["callback_query"]` (không gồm message) → **phải gồm `message`**. Xem `allowed_updates` trong getWebhookInfo phải có `"message"`.

---

## 7. Agent update pipeline (R2)

- **R2 bucket:** `parental-control-updates`
- **Public URL:** `https://pub-68ac9fad65e94c8f886542276f2e490c.r2.dev`
- File: `agent-update.zip` + `version.json` (có `sha256` + `size_bytes`)
- **R2 là nguồn chuẩn duy nhất.** `GET /api/v1/agent/version` đọc `version.json` từ R2;
  đĩa của backend chỉ còn là fallback cho chế độ chạy local (trên Vercel đĩa là `/tmp`
  tạm thời nên trước đây luôn báo sai `v0001`).

### Quy trình phát hành (đã kiểm chứng 14/09/2026)

0. **Chạy cổng kiểm thử mô phỏng local trước khi phát hành** (PROJECT_RULES 3.4):
   ```bat
   python tools\test_agent_update_gate.py
   ```
   Bài test dùng chính `Updater.exe` vừa build và hai "agent giả" trong thư mục tạm để
   kiểm chứng 2 kịch bản: (a) bản mới thay thế và chạy được, (b) bản mới crash thì
   Updater tự khôi phục `.bak` và chạy lại bản cũ. **Chỉ được phát hành khi PASS 100%**;
   bài test không khởi động agent thật và không gửi lệnh nào lên máy con.
1. Máy dev: **tăng `AGENT_VERSION`** trong `build_and_pack_agent.bat` rồi chạy file đó
   (build PyInstaller + zip ra `backend_api/storage/updates/agent-update.zip`).
   ⚠️ **Bắt buộc tăng version mỗi lần build**: cùng một nhãn version có thể ứng với 2 bộ
   binary khác nhau (đã từng xảy ra với `v0031` — bản 14:48 và bản build lại 14:52), khi đó
   phát hành sẽ đẩy bản cũ xuống máy con mà không ai biết.
2. Web → **Cài đặt → Cập nhật Agent**: chọn file zip + số phiên bản → **Tải Gói Lên R2**.
   Trình duyệt PUT trực tiếp lên R2 bằng URL có chữ ký (gói ~43 MB, vượt giới hạn body
   4.5 MB của Vercel function nên không thể đi qua backend), tự tính SHA-256 rồi gọi
   `/api/v1/agent/r2-publish` để ghi `version.json`.
3. Bấm **Phát Hành** → `POST /api/devices/force-update-all` đọc `version.json` từ R2, gửi
   `force_update` (kèm `sha256`) tới mọi máy: máy đang bật nhận trong ~5s qua kênh poll,
   máy đang tắt nhận khi bật lên lần sau.

### Endpoint liên quan

| Endpoint | Việc |
|---|---|
| `GET /api/v1/agent/version` | Bản phát hành (nguồn R2) + `sha256`, `size_bytes`, `r2_configured` |
| `POST /api/v1/agent/r2-presign` | Cấp URL PUT có chữ ký (hết hạn 30 phút) |
| `POST /api/v1/agent/r2-publish` | Ghi `version.json`; từ chối nếu bucket chưa có zip |
| `GET /api/v1/agent/r2-status` | Chẩn đoán token / gói trong bucket / CORS |
| `POST /api/v1/agent/r2-setup-cors` | Đặt CORS qua S3 API (cần token có quyền bucket) |
| `POST /api/devices/force-update-all` | Phát hành tới mọi máy (trả số máy online/offline thật) |

### Cấu hình bắt buộc

- Vercel (project `quanlypc-api-backup`, Production): `R2_ACCESS_KEY`, `R2_SECRET_KEY`
  (token R2 quyền **Object Read & Write** cho bucket này là đủ).
- **CORS của bucket** (một lần, Cloudflare → R2 → bucket → Settings → CORS Policy):
  `AllowedOrigins` = `https://nguyentruclam.io.vn`, `https://www.nguyentruclam.io.vn`,
  `http://localhost:5173`; `AllowedMethods` = `PUT, GET, HEAD`; `AllowedHeaders` = `*`;
  `ExposeHeaders` = `ETag`. **Thiếu CORS thì trình duyệt không tải gói lên được**
  (preflight `OPTIONS` phải trả `204` kèm `Access-Control-Allow-Origin`).
- Script `upload_r2.py` vẫn dùng được khi muốn đẩy gói bằng dòng lệnh.

---

## 7b. Bảo mật: bí mật từng bị lộ — đã sửa ngày 14/09/2026

Repo này **public**, nên mọi giá trị bí mật từng nằm trong mã nguồn/tài liệu phải coi như
đã lộ và đã được thu hồi. Các lỗ hổng đã tìm thấy và cách xử lý:

| Lỗ hổng | Triệu chứng thực tế | Đã sửa thế nào |
|---|---|---|
| JWT secret mặc định có sẵn trong repo | Tôi tự ký token admin bằng chuỗi mặc định → API trả `HTTP 200`; ai đọc repo cũng phát hành được gói Agent giả (RCE trên máy con) | `core/config.py` **không còn secret mặc định**: thiếu `JWT_SECRET_KEY` thì sinh secret ngẫu nhiên theo tiến trình + log lỗi. Vercel đã đặt `JWT_SECRET_KEY` riêng |
| Mật khẩu admin mặc định trong repo, dùng làm "mật khẩu chủ" | Đăng nhập web bằng quyền super admin **và** mở khoá màn hình máy con qua `POST /api/auth/verify-password` — đứa trẻ tự mở khoá được máy mình | `SYSTEM_ADMIN_PASSWORD` không còn giá trị mặc định; cơ chế master password chỉ chạy khi biến môi trường được đặt (rỗng = tắt) |
| API key tĩnh hardcode được cấp quyền **system admin** | Key nằm trong `core/security.py` **và** trong agent (`.exe` phát cho máy con) → ai có nó phát hành được gói cập nhật giả | `get_current_user` nay ánh xạ mọi key tĩnh sang danh tính tối thiểu (`can_view_screenshots`), **không bao giờ** là system admin; `/api/telegram/config`, `/api/device/{id}/shutdown`, `/api/device/{id}/chat/history` đã siết lên quyền admin. Sau khi agent v0032 phổ biến thì xoá hẳn key tĩnh |
| Bot token Telegram hardcode (3 token khác nhau) | Nằm trong `routers/system.py`, `TelegramConfigModal.jsx` (⇒ **nhúng vào bundle JS công khai**), `docs/DEPLOY_VERCEL_SUPABASE.md`, `docs/FAILOVER.md`, guide test | Xoá hết khỏi code/docs/bundle; token chỉ lấy từ DB `telegram_settings` hoặc `TELEGRAM_BOT_TOKEN`. **Phải revoke các token cũ trong BotFather** |
| Vite nhúng `VITE_API_KEY` vào bundle | Bản build local chứa key tĩnh → ai xem JS cũng đọc được (bản production thì không, vì `.env` không lên Git) | `manager-web/.env` để trống `VITE_API_KEY` |

Bổ sung: `backend_api/tests/test_security_hardening.py` khoá các thuộc tính trên lại —
test sẽ **fail** nếu bất kỳ chuỗi bí mật cũ nào quay lại trong source, nếu key tĩnh được
cấp quyền admin, hoặc nếu key tĩnh bị phát tán ra ngoài `core/security.py`.

**Việc anh phải làm tay sau khi đổi key** (không thể tự động hoá):
1. BotFather → `/mybots` → chọn bot → **Revoke token** cho mọi bot đã từng bị lộ, rồi
   nhập token mới ở **Cài đặt → Telegram** trên web (lưu vào DB) hoặc đặt
   `TELEGRAM_BOT_TOKEN` trên Vercel.
2. Đổi mật khẩu tài khoản admin trên web (mật khẩu cũ đã lộ).
3. Muốn giữ "mật khẩu chủ" mở khoá máy con: đặt `SYSTEM_ADMIN_PASSWORD` (chuỗi mạnh,
   khác mật khẩu đăng nhập) trên Vercel rồi redeploy; không đặt thì cơ chế này tắt.
4. Sau khi máy đích đã cập nhật agent v0032: xoá `LEGACY_AGENT_KEY` khỏi
   `core/security.py` và xoá `API_KEY` khỏi `.env` của agent/backend.
   *Cách biết máy đã cập nhật:* lệnh `force_update` chuyển sang `delivered_at` khác NULL,
   và log Vercel không còn request nào dùng key tĩnh (agent v0032 chỉ dùng
   `secret_token` riêng của máy). Bản v0032 đã phát hành ngày 14/09/2026
   (`sha256 20b744cb…`) và cổng test local đã PASS 100%.

---

## 7c. HAI LOẠI MẬT KHẨU, TÁCH BIỆT HOÀN TOÀN

| | Mật khẩu WEB | Mật khẩu MỞ MÁY CON |
|---|---|---|
| Dùng để | đăng nhập web quản trị | mở khoá màn hình máy con (`blocker`) |
| Lưu ở đâu | hash trong DB (`users` + `parents`) | `MASTER_UNLOCK_PASSWORD` (Vercel env) |
| Endpoint | `POST /api/auth/login` | `POST /api/auth/verify-password` |
| Đổi bằng cách | sửa hash trong DB (chưa có UI) | `vercel env rm/add` + redeploy |
| Có mở khoá máy con? | **Có** (mật khẩu tài khoản luôn được chấp nhận) | — |
| Có vào được web? | — | **Không** |

⚠️ Cái bẫy đã xảy ra thật (14/09/2026): `MASTER_UNLOCK_PASSWORD` còn được nhận làm mật
khẩu đăng nhập web, và `seed_system_admin()` **ghi đè mật khẩu web** bằng giá trị của nó ở
mỗi lần server khởi động. Hệ quả: đặt "mật khẩu chỉ để mở máy" thì nó trở thành mật khẩu
web và xoá mật khẩu web đang dùng; còn khi biến rỗng thì nó ghi hash của chuỗi rỗng → đăng
nhập web bằng mật khẩu trống = quyền system admin. Nay đã sửa: login web chỉ kiểm tra hash
trong DB, và seeder không bao giờ lấy biến môi trường ghi vào mật khẩu web (test khoá lại).

Tên biến cũ `SYSTEM_ADMIN_PASSWORD` vẫn được nhận như bí danh của `MASTER_UNLOCK_PASSWORD`
để không phá cấu hình đang chạy; tên mới `MASTER_UNLOCK_PASSWORD` là tên nên dùng.

---

## 8. Checklist trước khi deploy

- [ ] Deploy API: **`git push`** (Vercel auto-deploy). *Không* chạy
      `vercel deploy --prod` trong `backend_api` nữa — project đã có Root Directory =
      `backend_api` nên CLI áp dụng thêm lần nữa và làm mọi route `/api/*` trả 404.
      Cần deploy lại bản Git: `vercel redeploy <deployment-url>`.
- [ ] Deploy web qua thư mục gốc `vercel deploy --prod --yes` (hoặc `git push`)
- [ ] Webhook Telegram đúng URL + gồm message
- [ ] Supabase env (DATABASE_URL, SERVICE_KEY) + R2 env + `JWT_SECRET_KEY` đặt trên Vercel Production
- [ ] `MASTER_UNLOCK_PASSWORD` (mở máy con) đã đặt — nếu không đặt thì màn hình khoá chỉ mở được bằng mật khẩu tài khoản
- [ ] Bucket R2 đã có CORS policy (nếu dùng nút tải gói trên web)
- [ ] Tăng `AGENT_VERSION` khi build bản mới rồi tải gói lên R2

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân / Fix |
|---|---|
| API 508 INFINITE_LOOP | Deploy nhầm project/dashboard → chỉ CLI từ `backend_api` |
| Mọi `/api/*` trả 404 sau deploy | CLI chạy trong `backend_api` khi project đã có Root Directory = `backend_api` → dùng `git push` hoặc `vercel redeploy` |
| Bot không trả lời | Webhook `allowed_updates` thiếu `message` → set lại |
| Screenshot upload 500 | MIME `image/jpg` bị Supabase từ chối → code tự chuẩn hoá `image/jpeg` |
| Force-update bản sai | Backend đọc version.json từ temp (serverless) → đã sửa đọc từ R2 |
| Version hiện `v0001` dù bản thật mới hơn | Cùng nguyên nhân trên → `/api/v1/agent/version` nay đọc R2 |
| Tải gói báo "Không tải được lên R2" | Bucket thiếu CORS → dán policy ở mục 7 |
| `r2-status` báo `AccessDenied` khi đọc CORS | Token chỉ có quyền Object Read & Write → đặt CORS thủ công trên Cloudflare |
| Agent lỗi "Another Agent instance" | Lock file cũ → PC_Installer mới tự xoá |

