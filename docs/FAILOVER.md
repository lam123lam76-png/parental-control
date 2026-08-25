# Failover Architecture — Hướng dẫn vận hành (Parental Control)

Kiến trúc dự phòng: khi server nhà tắt, máy con vẫn nhận lệnh và đẩy dữ liệu qua
backup API trên Vercel, dùng chung 1 database Supabase.

```
Phụ huynh (web) ──► Home backend (máy nhà, SQLite cũ / giờ = Supabase) ──► Supabase
                        │  tắt máy →                                          ▲
                        ▼                                                     │ poll 30s
                 Vercel backup API (quanlypc-api-backup.vercel.app) ──────────┘
                        ▲                                          máy con (agent v0006)
                        └── WS chính sập → FALLBACK_MODE → đẩy alert/log/screenshot
```

## Các thành phần

| Thành phần | Vai trò |
|---|---|
| `backend_api/` | Backend chính (chạy máy nhà qua `server_tray_app.py`, port 8000, tunnel Cloudflare) |
| `backend_api/.env` | `DATABASE_URL` = Supabase pooler (IPv4) — **không commit** (đã ignore) |
| `quanlypc-api-backup.vercel.app` | Backup API: cùng code, mount trên Vercel serverless, đọc/ghi cùng Supabase |
| `backend_api/scripts/migrate_sqlite_to_pg.py` | Migration 1 lần SQLite → Supabase (chạy lại an toàn: remap email, skip orphan) |
| `agent/communication/fallback_client.py` | Thread poll lệnh tồn đọng từ backup API **mỗi 30s, luôn luôn** (không chỉ khi fallback) |
| `agent/utils/state.py` | Cờ `FALLBACK_MODE` (WS lỗi → bật; WS nối lại → tắt) |

## Máy con — setup (máy chưa từng cài hoặc cập nhật)

```bat
:: Cài mới / cập nhật, kèm backup URL (BẮT BUỘC cho failover):
AgentInstaller.exe --backup-url https://quanlypc-api-backup.vercel.app
```

Kiểm tra sau cài: `C:\ProgramData\ParentalControl\.env` phải có
`BACKUP_SERVER_URL=https://quanlypc-api-backup.vercel.app`;
`version.json` = v0006; `agent_debug.log` có dòng `[FALLBACK] FallbackClient started.`

> ⚠️ Cập nhật máy con TRƯỚC khi tắt server nhà (đường tải update nằm trên máy nhà).

## Khi server nhà tắt

- Backup API + Supabase vẫn sống độc lập (đã verify).
- Máy con v0006: WS lỗi → FALLBACK_MODE → alert/log/screenshot đẩy sang Vercel;
  poll lệnh mỗi 30s từ backup API → nhận lệnh Khóa/Mở/Shutdown đã queue.
- `last_seen_at` của thiết bị được cập nhật mỗi lần poll → biết thiết bị còn sống
  qua Supabase/backup API ngay cả khi home tắt.
- Lệnh queue khi offline nằm trong `pending_commands` (Supabase), đánh dấu
  `delivered_at` khi máy con lấy — không xóa trước khi thực thi (TTL 24h dọn dòng cũ).

## Còn thiếu (mắt xích cuối): web quản lý trên cloud

Hiện web được máy nhà phục vụ (FastAPI serve web UI cùng port 8000) → tắt server =
tắt web → phụ huynh không ra lệnh mới từ UI khi home down.

Cách hoàn thiện (cần xác nhận project Vercel hosting web + test UX):

1. Build web với backend trỏ backup API:
   ```bat
   cd manager-web
   set VITE_BACKEND_URL=https://quanlypc-api-backup.vercel.app
   set VITE_API_KEY=732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7
   npm run build
   ```
2. Deploy bản build lên Vercel/Cloudflare Pages (project web riêng, vd `quanlypcemhoang`):
   ```bat
   cd manager-web && vercel deploy --prod
   ```
3. Giới hạn khi web ở cloud: realtime (WS) không có trên backup API → trạng thái
   online lấy qua `last_seen_at` (poll 30s), lệnh đi qua REST → queue → máy con poll.

## Xử lý sự cố

| Hiện tượng | Kiểm tra |
|---|---|
| Máy con không nhận lệnh khi home tắt | `.env` thiếu `BACKUP_SERVER_URL` (chạy lại installer kèm `--backup-url`); `agent_debug.log` tìm `[FALLBACK]` |
| Backup API 500 | Xem log Vercel (`vercel logs --environment production`); kiểm tra env `DATABASE_URL` (phải là pooler IPv4 + `?sslmode=require`) |
| Lệnh queue không bao giờ tới tay | `pending_commands.delivered_at` còn NULL = máy con chưa poll; WS nối lại vẫn drain nhờ always-poll |
