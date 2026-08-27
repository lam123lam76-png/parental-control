/**
 * PC Failover Worker — simplified: home machine REMOVED.
 * Proxies everything to the cloud web (Vercel), which serves the SPA and
 * rewrites /api, /ws, /static to the backup API (Supabase). No home dependency.
 */
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
