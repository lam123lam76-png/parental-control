# HƯỚNG DẪN CHI TIẾT — LOẠI BỎ MÁY NHÀ (Cloud-first)

> Trạng thái: code agent poll 5s (v0012) + web/API đã deploy Vercel. Còn: trỏ domain + teardown máy nhà + cài agent.
> Backup: git tag `backup-before-remove-home` + `backups/`.

## Kiến trúc đích
```
Agent (thiết bị con) ──poll 5s──► nguyentruclam.io.vn ──► (Worker | CNAME) ──► parental-control-sepia.vercel.app (web)
                                                                                └─ /api rewrite ─► quanlypc-api-backup.vercel.app ─► Supabase
Phụ huynh mở nguyentruclam.io.vn ─► web cloud (luôn sẵn) ─► API cloud ─► Supabase
```
Không còn máy nhà. Domain + web + API đều cloud.

---

## STEP 4 — Trỏ domain `nguyentruclam.io.vn` → Vercel web

### Cách A — Cập nhật Cloudflare Worker (giữ Worker làm cổng) — khuyên dùng
1. Cloudflare dashboard → **Workers & Pages** → chọn Worker **`failover-router`**.
2. Bấm **Edit code**.
3. Xóa toàn bộ code cũ, **dán code mới** (lấy từ repo `cloudflare-worker/worker.js`):
```js
const WEB = "https://parental-control-sepia.vercel.app";
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = new URL(url.pathname + url.search, WEB);
    const headers = new Headers(request.headers);
    headers.set("Host", new URL(target).host);
    return fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });
  },
};
```
4. **Save and Deploy**.
5. Xóa route/home cũ trong tunnel (nếu còn): Zero Trust → Tunnels → bỏ `home.nguyentruclam.io.vn` (vì không dùng máy nhà nữa).

### Cách B — DNS CNAME thẳng tới Vercel (bỏ Worker, đơn giản hơn)
1. Cloudflare → **nguyentruclam.io.vn** → tab **DNS**.
2. Sửa record `nguyentruclam.io.vn` (hoặc `@`) → **Type CNAME**, Name `@`, Target `parental-control-sepia.vercel.app`, **Proxy status: ON** (orange).
3. Xóa route Worker: **Workers & Pages → failover-router → Settings → Triggers → Add Route** → xóa `*nguyentruclam.io.vn/*`.
4. (Nếu có tunnel `home.nguyentruclam.io.vn`) Zero Trust → Tunnels → xóa hostname đó.

### Verify Step 4
- Mở `https://nguyentruclam.io.vn` → phải hiện web quản lý (login).
- `https://nguyentruclam.io.vn/api/health` → trả `{"status":"ok",...}` (qua web → rewrite → backup API).

---

## STEP 5 — Teardown máy nhà (LÀM SAU KHI xác nhận Step 4 hoạt động)

### 5.1 Gỡ tray autostart (không cho máy nhà tự khởi động backend nữa)
1. Xóa file khởi động: `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Start_ParentalControl_Server.vbs`
2. Gỡ Run key (CMD admin):
```bat
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ParentalControlMasterServer" /f
```

### 5.2 Dừng tunnel Cloudflared (máy nhà)
CMD **admin**:
```bat
sc stop Cloudflared
sc config Cloudflared start= disabled
```
(hoặc nếu dùng WARP: tắt WARP tunnel.)

### 5.3 Dừng home backend
- Kill process uvicorn port 8000 (Task Manager / `taskkill /F /IM python.exe` cẩn thận).
- Không chạy `run_backend.bat` / tray nữa.

> Sau đó `nguyentruclam.io.vn` chỉ còn phục vụ từ cloud.

### 5.4 Cài agent v0012 lên các thiết bị (bỏ WS → poll 5s)
Trên từng thiết bị (double-click, tự đòi admin):
```bat
C:\Test\PC_Installer.exe --update
```
- Đảm bảo device đã cài v0012 (chỉ v0012 dùng polling; v0011 cũ dùng WS sẽ không hoạt động khi hết máy nhà).

---

## ⚠️ QUAN TRỌNG — Update zip agent khi bỏ máy nhà
`agent-update.zip` hiện **chỉ nằm trên máy nhà** (`backend_api/storage/updates/`). Khi tắt máy nhà, installer tải từ `nguyentruclam.io.vn/static/updates/agent-update.zip` → web → `/static` rewrite → backup API → **404** (Vercel không có zip).

**Giải pháp (chọn 1):**
- **(Khuyên dùng) Host zip lên cloud (Cloudflare R2 / GitHub Releases):** tải `agent-update.zip` + `version.json` lên, rồi sửa installer/agent `AutoUpdater` trỏ download URL cloud. → cập nhật từ xa vẫn được.
- **Hoặc:** giữ bản zip local và dùng `C:\Test\PC_Installer.exe` cài thủ công từ máy có zip (mỗi lần cập nhật phải cài tay).

---

## Thứ tự an toàn
1. ✅ Làm **Step 4** (trỏ domain) → **verify** web + API từ cloud.
2. Trước khi teardown, **cài agent v0012** lên các thiết bị (để chúng chuyển sang polling).
3. Mới **teardown máy nhà** (Step 5).
4. Xử lý **update-zip hosting** (R2 hoặc cài tay).
