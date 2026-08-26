# CLOUDFLARE FAILOVER — HƯỚNG DẪN CHI TIẾT TỪNG THAO TÁC

Mục tiêu: `nguyentruclam.io.vn` luôn chạy — máy nhà mở thì chạy qua máy nhà, máy nhà tắt thì Cloudflare tự chuyển sang cloud (web tĩnh + backup API → Supabase).

Kiến trúc:

```
Phụ huynh / Agent → nguyentruclam.io.vn   (Cloudflare LOAD BALANCER)
   ├─ Pool "home"   (ưu tiên 1) → tunnel home.nguyentruclam.io.vn → máy nhà:8000
   └─ Pool "backup" (ưu tiên 2) → parental-control-web.vercel.app (web tĩnh + /api rewrite → backup API)
   Health check "home" fail → LB tự trỏ "backup" → site vẫn chạy ✓
```

> Đọc trước 1 lượt rồi làm từng phần theo thứ tự: **A → B → C → D**.

---

## PHẦN A — Deploy web tĩnh lên Vercel (backup origin)

Đã chuẩn bị sẵn `vercel.json` gốc trong repo (build web + rewrite `/api` → backup API). Giờ chỉ cần import lên Vercel.

1. Mở trình duyệt → **vercel.com** → đăng nhập.
2. Góc trên phải → nút **"Add New…"** → chọn **"Project"**.
3. Màn hình "Import Git Repository" → tìm repo **`parental-control`** (github `lam123lam76-png`) → bấm **Import**.
   - Nếu chưa thấy repo, bấm **"Adjust GitHub App Permissions"** / **Install GitHub App** để cấp quyền đọc repo.
4. Màn hình "Configure Project":
   - **Framework Preset**: tự nhận **Vite** (từ vercel.json). Nếu rỗng, chọn **Vite** thủ công.
   - **Root Directory**: giữ `/` (mặc định).
   - **Build Command**: `cd manager-web && npm install && npm run build` (vercel.json đã ghi, để nguyên).
   - **Output Directory**: `manager-web/dist`.
5. Cuộn xuống **Environment Variables** → **KHÔNG thêm `VITE_BACKEND_URL`** (bắt buộc rỗng để build same-origin).
   - (Tùy chọn) nếu bạn muốn dùng API key tĩnh: thêm `VITE_API_KEY` = `732F636DF7E2E6A0B95AAB8C139AB375D5B65D82241661C7`. Không bắt buộc.
6. Bấm **Deploy**. Chờ ~1–2 phút.
7. Khi xong, màn hình hiện URL **`https://parental-control-web-xxxx.vercel.app`** (hoặc ghi chú **Domains**). Copy URL này.
8. **Verify**: mở URL đó → dashboard phải hiện. Bấm đăng nhập → phải vào được (vì `/api` được rewrite sang backup API → Supabase).

> ⚠️ Đây chính là **backup origin** — ghi nhớ URL để dùng ở Phần C.

---

## PHẦN B — Chuyển tunnel sang subdomain `home.`

Load Balancer sẽ chiếm hostname `nguyentruclam.io.vn`, nên tunnel phải lộ qua **`home.nguyentruclam.io.vn`** (để Pool "home" trỏ về máy nhà).

1. Vào **Cloudflare dashboard** (dash.cloudflare.com) → đăng nhập → chọn account.
2. Trái chọn **Zero Trust** (Cloudflare One). Nếu chưa bật, kích hoạt (free).
3. Trong Zero Trust → **Networks** (hoặc **Access → Tunnels** trên giao diện cũ) → **Tunnels**.
4. Danh sách tunnel → bấm tên tunnel của bạn (ví dụ `cloudflared`) → **Configure**.
5. Tab **Public Hostname** → bấm **Add a public hostname**.
6. Điền:
   - **Subdomain**: `home`
   - **Domain**: chọn `nguyentruclam.io.vn`
   - **Path**: để trống
   - **Service → Type**: `HTTP`
   - **Service → URL**: `localhost:8000`
7. Bấm **Save hostname**.
8. Giờ tìm dòng hostname **`nguyentruclam.io.vn`** cũ trong danh sách → bấm icon **3 chấm (…) bên phải** → **Delete** → xác nhận. (Tránh xung đột DNS với LB.)
   - Nếu không có hostname `nguyentruclam.io.vn` cũ (chỉ có subdomain khác), bỏ qua bước này.
9. Xong. Tunnel giờ lộ `home.nguyentruclam.io.vn` → máy nhà:8000.
10. **Verify nhanh**: trên máy nhà mở backend (port 8000), rồi mở `https://home.nguyentruclam.io.vn` → phải ra dashboard. Nếu ra, tunnel ok.

> Lưu ý: agent không cần đổi — nó vẫn trỏ `nguyentruclam.io.vn` (= LB).

---

## PHẦN C — Tạo Load Balancer (quan trọng nhất)

1. Vào **Cloudflare dashboard** → account của bạn.
2. Thanh trái: **Traffic** → **Load Balancing** (có thể phải cuộn xuống nhóm "Traffic").
   - Nếu **không thấy** mục Load Balancing, tức gói Free chưa bật → đọc ghi chú cuối Phần này.
3. Bấm **Create Load Balancer**.
4. **Step 1 — Load Balancer name & hostname**:
   - **Name**: `nguyentruclam-failover` (bất kỳ).
   - **Hostname**: nhập `nguyentruclam` + chọn `.io.vn` → đầy đủ `nguyentruclam.io.vn`.
   - Bấm **Next**.
5. **Step 2 — Add origin pools** (tạo 2 pool theo thứ tự):

   **Pool 1 — "home" (ưu tiên, máy nhà):**
   - **Pool name**: `home`
   - **Origin name**: `home-tunnel`
   - **Origin address**: `home.nguyentruclam.io.vn` (đi qua tunnel → máy nhà:8000)
   - Bấm **Add origin**.
   - **Health Checks** (bên dưới):
     - **Path**: `/` (hoặc `/api/health`)
     - **Type**: HTTPS
     - **Method**: GET
     - **Port**: 443
     - **Interval**: `30s`
     - **Timeout**: `5s`
     - **Retries**: `2`
     - **Failure threshold**: `2`
   - Bấm **Add pool** → nó thêm vào list. Đặt pool này **phía trên** (thứ tự = mức ưu tiên).

   **Pool 2 — "backup" (cloud):**
   - **Pool name**: `backup`
   - **Origin name**: `backup-web`
   - **Origin address**: `parental-control-web-xxxx.vercel.app` (URL từ Phần A)
   - Bấm **Add origin**.
   - **Health Checks**: Path `/`, Type HTTPS, Interval `60s`, Timeout `5s`, Retries `2`, Failure threshold `2`.
   - Bấm **Add pool**.
   - Đảm bảo thứ tự list: **`home` ở trên, `backup` ở dưới**.
   - Bấm **Next**.

6. **Step 3 — Traffic steering**:
   - Chọn **Standard** (routing theo thứ tự pool: home trước, chỉ dùng backup khi home fail).
   - (Có thể chọn "Random" hoặc "Latency", nhưng **Standard** là đúng cho failover ưu tiên home.)
   - Bấm **Next**.

7. **Step 4 — Session affinity & others** (thường để mặc định, **Off**) → bấm **Next**.

8. **Step 5 — Review** → kiểm tra hostname `nguyentruclam.io.vn` + 2 pool đúng thứ tự → bấm **Create Load Balancer**.

9. Cloudflare tự tạo DNS record cho `nguyentruclam.io.vn` trỏ về LB (proxy bật). **Chờ 1–2 phút** cho DNS lan truyền.

> ⚠️ **Nếu không thấy mục Load Balancing (gói Free)**: Cloudflare có thể yêu cầu add-on trả phí cho gói của bạn. **Báo tôi ngay** — tôi chuyển sang phương án **Cloudflare Worker** (free, không cần LB), tôi viết sẵn code reverse-proxy.

---

## PHẦN D — Verify (test failover)

**Khi máy nhà ĐANG bật** (backend port 8000 chạy):
- Mở `https://nguyentruclam.io.vn` → dashboard phải hiện, agent **online** (real-time).
- Kiểm tra nguồn: dòng indicator trên web hiện "Tunnel → Local".

**Khi máy nhà TẮT** (tắt backend, hoặc tắt máy):
- Chờ **~1 phút** (health check fail 2 lần × 30s).
- Mở `https://nguyentruclam.io.vn` → dashboard **vẫn hiện** (từ backup), data đầy đủ (Supabase), agent hiện **offline** nhưng còn `last_seen`.
- Thử khóa/mở thiết bị → lệnh được xếp hàng trong Supabase (agent khi máy nhà bật lại sẽ nhận).

**Lệnh kiểm tra nhanh** (mở PowerShell / cmd):
```
curl -s https://nguyentruclam.io.vn/api/health
```
- Có JSON trả về = API sống.
- Đổi pool: bật/tắt máy nhà rồi lặp lại lệnh để xem LB chuyển.

**Khi máy nhà mở lại**: health check hồi phục → LB **tự trỏ về home** (không cần thao tác gì).

---

## Khắc phục nhanh

| Vấn đề | Cách xử lý |
|---|---|
| `nguyentruclam.io.vn` ra lỗi, `home.nguyentruclam.io.vn` vẫn chạy | LB đang trỏ backup nhưng backup web chưa đúng → kiểm tra Phần A URL + `/api` rewrite. |
| Mở backup origin ra "404 Not Found" | Deploy Phần A chưa xong hoặc URL sai → mở lại `parental-control-web-*.vercel.app` kiểm tra. |
| Login qua backup báo lỗi | `/api` chưa rewrite → kiểm tra `vercel.json` có đủ 4 dòng `rewrites`. |
| Agent không online dù máy nhà bật | Agent chưa cài bản mới / chưa kết nối LB → chạy `C:\Test\AgentInstaller.exe --update` (admin). |
