# CLOUDFLARE FAILOVER — HƯỚNG DẪN CHI TIẾT (phương án Cloudflare WORKER — miễn phí)

Gói Free không có **Load Balancing** → dùng **Cloudflare Worker** (miễn phí 100k req/ngày). Worker là reverse proxy: **thử home trước, home chết thì trỏ sang cloud (Vercel)**.

Kiến trúc:

```
Phụ huynh / Agent → nguyentruclam.io.vn  → [Cloudflare WORKER pc-failover]
   ├─ thử HOME  = home.nguyentruclam.io.vn (tunnel → máy nhà:8000)     — ƯU TIÊN
   │    ├─ HTTP → trả về web + API của máy nhà
   │    └─ WebSocket (agent realtime) → về máy nhà
   └─ home fail/timeout → BACKUP = parental-control-web.vercel.app (web tĩnh + /api rewrite → backup API → Supabase)
```

- **Web dùng same-origin API** → LB/Worker trỏ về đâu thì web gọi API về đó.
- **Agent không cần đổi**: vẫn trỏ `nguyentruclam.io.vn` (= Worker). Worker proxy WS về home khi home bật; home tắt → WS 503 → agent tự **FALLBACK_MODE** (poll backup API 30s — code đã có).
- Code Worker đã viết sẵn tại **`cloudflare-worker/worker.js`** trong repo.

> Đọc trước rồi làm theo thứ tự **A → B → C → D**.

---

## PHẦN A — Deploy web tĩnh lên Vercel (backup origin)

`vercel.json` gốc đã cấu hình: build web + rewrite `/api`, `/ws`, `/static` → `https://quanlypc-api-backup.vercel.app`.

1. **vercel.com** → **Add New → Project** → Import repo `parental-control` (github `lam123lam76-png`).
   - Chưa thấy repo → bấm **"Adjust GitHub App Permissions"** / Install GitHub App để cấp quyền.
2. **Framework Preset**: tự nhận **Vite**. **Root Directory**: `/`. **Output**: `manager-web/dist`.
3. **Environment Variables**: **KHÔNG đặt `VITE_BACKEND_URL`** (phải rỗng để build same-origin).
4. **Deploy** → đợi ~1–2 phút → ghi URL **`https://parental-control-web-xxxx.vercel.app`**.
5. **Verify**: mở URL → dashboard hiện, **login được** (vì `/api` rewrite sang backup API).

---

## PHẦN B — Chuyển tunnel sang subdomain `home.`

Worker sẽ chiếm `nguyentruclam.io.vn`, nên tunnel lộ qua **`home.nguyentruclam.io.vn`**.

1. Cloudflare dashboard → **Zero Trust** → **Networks → Tunnels** → bấm tunnel của bạn → **Configure**.
2. Tab **Public Hostname** → **Add a public hostname**:
   - Subdomain: `home` · Domain: `nguyentruclam.io.vn` · Path: *(trống)*
   - Service Type: `HTTP` · URL: `localhost:8000`
   - → **Save hostname**.
3. Xóa hostname cũ `nguyentruclam.io.vn` khỏi tunnel (3 chấm → Delete) để nhường cho Worker.
4. **Verify**: mở `https://home.nguyentruclam.io.vn` (backend port 8000 đang chạy) → ra dashboard.

---

## PHẦN C — Tạo Worker + route

1. Cloudflare dashboard → **Workers & Pages** → **Create application** → **Worker**.
2. **Name**: `pc-failover` → **Deploy**.
3. **Chỉnh sửa code**:
   - Mở `cloudflare-worker/worker.js` trong repo (đã viết sẵn) → copy toàn bộ.
   - Dán vào trình soạn code → **sửa dòng `const BACKUP`** = URL thật từ Phần A (thay `parental-control-web.vercel.app`).
   - **Save and Deploy**.
4. Gắn route (giao diện cũ: **Workers → pc-failover → Settings → Triggers → Add Route**):
   - Route: **`nguyentruclam.io.vn/*`** → Worker `pc-failover`.
   - Cloudflare sẽ hỏi thêm DNS record → **đồng ý** (tự tạo CNAME proxied cho `nguyentruclam.io.vn`).
5. **Verify**: mở `https://nguyentruclam.io.vn` → phải ra dashboard (qua Worker → home).

---

## PHẦN D — Verify failover

- **Máy nhà bật** → `https://nguyentruclam.io.vn` → dashboard từ home, agent **online**.
- **Máy nhà tắt** (tắt backend/máy) → Worker thử home (timeout ~4s) → tự trỏ backup:
  - Dashboard vẫn hiện (web tĩnh Vercel), data từ Supabase, agent hiện **offline**.
- Kiểm tra nhanh: `curl -s https://nguyentruclam.io.vn/api/health`.
- **Máy nhà mở lại** → Worker tự quay về home (không cần thao tác).

> Lưu ý: khi home tắt, mỗi request mất thêm ~4s timeout trước khi fallback (có circuit breaker 30s nên không lặp lại liên tục). Đây là điều đánh đổi của bản Free — chấp nhận được.

---

## Khắc phục nhanh

| Vấn đề | Cách xử lý |
|---|---|
| Mở `nguyentruclam.io.vn` ra lỗi Worker | Route chưa gắn đúng `nguyentruclam.io.vn/*`, hoặc DNS chưa trỏ Worker. Kiểm tra Phần C b4. |
| `home.nguyentruclam.io.vn` OK nhưng main lỗi | Worker chưa deploy / route chưa active. |
| Login qua backup báo lỗi | `/api` chưa rewrite → kiểm tra `vercel.json` có đủ 4 dòng `rewrites`. |
| Agent không online dù máy nhà bật | Chưa chạy `C:\Test\AgentInstaller.exe --update` (agent đang ở bản cũ). |
