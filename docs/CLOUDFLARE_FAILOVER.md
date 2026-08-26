# CLOUDFLARE FAILOVER — Home ưu tiên, home chết → sang Cloud (Vercel)

Mục tiêu: `nguyentruclam.io.vn` luôn chạy. Khi máy nhà (LAPTOP-LAM, localhost:8000) mở → site chạy qua máy nhà (realtime agent + nhanh). Khi máy nhà tắt → Cloudflare **tự chuyển** sang bản cloud (web tĩnh + backup API → Supabase). Người phụ huynh vẫn vào dashboard, vẫn khóa/mở thiết bị.

## Kiến trúc

```
Phụ huynh / Agent → nguyentruclam.io.vn   (Cloudflare LOAD BALANCER)
   ├─ Pool "home"   (ưu tiên) → tunnel home.nguyentruclam.io.vn → máy nhà:8000  (web + API + WS agent)
   └─ Pool "backup" (fallback)→ parental-control-web.vercel.app  (web tĩnh, /api rewrite → backup API → Supabase)
   → Health check "home" fail → LB tự trỏ "backup" → site vẫn hoạt động ✓
```

- **Web dùng same-origin API** (`BASE_URL=""`), nên 1 bản `dist` chạy được trên cả home lẫn Vercel — LB trỏ về đâu thì API về đó.
- **Agent WS**: connect `nguyentruclam.io.vn` → LB → home (khi mở). Home tắt → WS fail → agent tự chuyển FALLBACK_MODE (poll backup API mỗi 30s) — đã có sẵn trong code.

## PHẦN 1 — Deploy web tĩnh lên Vercel (backup origin) — đã sẵn config

`vercel.json` gốc đã cấu hình: build web + rewrite `/api`, `/ws`, `/static` → `https://quanlypc-api-backup.vercel.app/...`.

1. Vào [vercel.com](https://vercel.com) → **Add New → Project** → Import repo `parental-control`.
2. **Root Directory**: để `/` (gốc repo). Framework tự nhận **Vite** (nhờ vercel.json).
3. **Environment Variables**: **KHÔNG** đặt `VITE_BACKEND_URL` (phải rỗng để build same-origin). `VITE_API_KEY` tùy chọn.
4. **Deploy**. Ghi lại URL, ví dụ `parental-control-web.vercel.app`.
5. Verify: mở URL → dashboard hiện; **login** được (vì `/api` được rewrite sang backup API → Supabase).

## PHẦN 2 — Chuyển tunnel sang subdomain `home.`

Load Balancer chiếm hostname `nguyentruclam.io.vn`, nên tunnel phải lộ qua subdomain khác.

1. Cloudflare **Zero Trust → Networks → Tunnels** → chọn tunnel của bạn → **Public Hostname**.
2. Thêm hostname **`home.nguyentruclam.io.vn`** → Service `http://localhost:8000`.
3. **Xóa** hostname `nguyentruclam.io.vn` khỏi tunnel (tránh xung đột DNS với LB).
4. (Agent không cần đổi: nó vẫn trỏ `nguyentruclam.io.vn` = LB.)

## PHẦN 3 — Tạo Load Balancer

1. Cloudflare **Traffic → Load Balancing → Create Load Balancer**.
2. **Hostname**: `nguyentruclam.io.vn`.
3. **Pool "home"** (đặt ưu tiên 1 / Primary):
   - Origin: hostname `home.nguyentruclam.io.vn` (đi qua tunnel → localhost:8000).
   - Health check: GET `/` (hoặc `/api/health`), timeout ~5s.
4. **Pool "backup"** (ưu tiên 2):
   - Origin: `https://parental-control-web.vercel.app`.
   - Health check: GET `/`.
5. **Traffic steering**: **Standard** (theo thứ tự pool) — để home được dùng trước, chỉ failover khi home chết.
6. **Health check interval**: 30s (fail threshold 2–3) — cân bằng giữa phát hiện nhanh và không tắt nhầm.
7. **Create**. Chờ LB bắt DNS record cho `nguyentruclam.io.vn`.

> ⚠️ **Free tier**: Load Balancing có thể là add-on trả phí hoặc giới hạn trên gói Free — nếu không thấy mục này, báo tôi để chuyển sang phương án **Cloudflare Worker** (free, tôi viết sẵn code).

## PHẦN 4 — Verify

| Tình huống | Kết quả mong đợi |
|---|---|
| Máy nhà mở | `nguyentruclam.io.vn` → dashboard từ home, agent online, realtime. |
| Máy nhà tắt (khoảng 1 phút sau health check fail) | `nguyentruclam.io.vn` → dashboard từ backup, data từ Supabase, agent hiện offline nhưng vẫn thấy last_seen. |

- Đổi pool health trong quá trình test bằng cách tắt máy nhà (hoặc dừng backend) → quan sát LB chuyển.
- Lệnh kiểm tra nhanh: `curl -s https://nguyentruclam.io.vn/api/health`.

## Ghi chú

- Khi home mở lại, health check hồi phục → LB tự trỏ về home (không cần thao tác).
- Mọi thay đổi code backend sau này: deploy lại backup API (`backend_api`) như cũ. Web tĩnh chỉ cần redeploy khi đổi UI.
