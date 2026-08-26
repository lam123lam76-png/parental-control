/**
 * PC Failover Worker — reverse proxy "home-first, cloud fallback"
 *
 * nguyentruclam.io.vn
 *   ├─ HOME   = https://home.nguyentruclam.io.vn  (tunnel → máy nhà :8000)  — ƯU TIÊN
 *   └─ BACKUP = https://<thay-bang-web-tinh-cua-ban>.vercel.app            — FALLBACK khi home chết
 *
 * - HTTP  : thử home trước (timeout ngắn); lỗi/timeout → backup.
 * - WebSocket (agent realtime): chỉ về home; home chết → 503 (agent tự chuyển FALLBACK_MODE
 *   và poll BACKUP_SERVER_URL — đã có sẵn trong agent).
 * - Circuit breaker nhỏ: nếu home fail, tạm coi là down ~30s để tránh chờ timeout mỗi request.
 */

// ===== CẤU HÌNH — chỉ cần sửa 2 dòng này =====
const HOME = "https://home.nguyentruclam.io.vn";           // tunnel → máy nhà
const BACKUP = "https://parental-control-web.vercel.app";  // web tĩnh (rewrite /api) — THAY URL thật của bạn
// =============================================

const HOME_TIMEOUT_MS = 4000;       // thời gian chờ home trước khi fallback
const HOME_DOWN_GRACE_MS = 30000;   // nếu home fail, coi là down 30s (tránh timeout lặp)

let homeDownUntil = 0;

function target(base, url) {
  return new URL(url.pathname + url.search, base);
}

function headersFor(targetUrl, req) {
  const h = new Headers(req.headers);
  h.set("Host", new URL(targetUrl).host);
  return h;
}

async function tryFetch(targetUrl, req, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers: headersFor(targetUrl, req),
      body: ["GET", "HEAD"].includes(req.method) ? undefined : req.body,
      redirect: "manual",
      signal: controller.signal,
    });
    clearTimeout(timer);
    return resp;
  } catch (e) {
    clearTimeout(timer);
    return null;
  }
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const now = Date.now();

    // ---- WebSocket (agent realtime) → chỉ về HOME ----
    if ((request.headers.get("Upgrade") || "").toLowerCase() === "websocket") {
      const resp = await tryFetch(target(HOME, url), request, HOME_TIMEOUT_MS);
      if (resp && resp.status === 101) return resp;
      return new Response("home unavailable", { status: 503 });
    }

    // ---- HTTP → home ưu tiên ----
    if (now > homeDownUntil) {
      const resp = await tryFetch(target(HOME, url), request, HOME_TIMEOUT_MS);
      if (resp && resp.status < 500) return resp;          // home sống
      homeDownUntil = now + HOME_DOWN_GRACE_MS;            // home fail → tạm đánh dấu down
    }

    // ---- Fallback → backup (web tĩnh + /api rewrite sang backup API) ----
    const backup = await tryFetch(target(BACKUP, url), request, 20000);
    if (backup) return backup;

    return new Response("both origins unavailable", { status: 502 });
  },
};
