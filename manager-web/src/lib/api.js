/**
 * FastAPI Backend API Client for Parental Control Manager Web UI
 * Uses relative BASE_URL by default to seamlessly proxy requests via Vite / Nginx / Cloudflare Tunnel.
 */

const BASE_URL = (
  import.meta.env.VITE_BACKEND_URL || 
  import.meta.env.VITE_API_BASE_URL || 
  ""
).replace(/\/+$/, "");

const API_KEY_ENV = import.meta.env.VITE_API_KEY || "";

export function isTokenExpired(token) {
  if (!token || typeof token !== "string") return true;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false; // Static API key, not a JWT
    const payload = JSON.parse(atob(parts[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

export function getAuthToken() {
  try {
    const saved = localStorage.getItem("pc_auth_token") || sessionStorage.getItem("pc_auth_token");
    if (saved) {
      if (isTokenExpired(saved)) {
        clearAuthToken();
        return API_KEY_ENV;
      }
      return saved;
    }
    return API_KEY_ENV;
  } catch {
    return API_KEY_ENV;
  }
}

export function setAuthToken(token, remember = true) {
  try {
    if (remember) {
      localStorage.setItem("pc_auth_token", token);
      sessionStorage.removeItem("pc_auth_token");
    } else {
      sessionStorage.setItem("pc_auth_token", token);
      localStorage.removeItem("pc_auth_token");
    }
  } catch (e) {
    console.error("Failed to store auth token:", e);
  }
}

export function clearAuthToken() {
  try {
    localStorage.removeItem("pc_auth_token");
    sessionStorage.removeItem("pc_auth_token");
  } catch (e) {
    console.error("Failed to clear auth token:", e);
  }
}

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const token = getAuthToken();
  const isFormData = options.body instanceof FormData;
  const config = {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  };

  if (config.body && typeof config.body === "object" && !isFormData) {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(url, config);
  const data = await response.json().catch(() => ({}));
  
  if (response.status === 401) {
    if (!endpoint.includes("/api/auth/login") && !endpoint.includes("/api/register") && !endpoint.includes("/api/pair")) {
      clearAuthToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("pc:unauthorized", { detail: data.detail || "Phiên làm việc đã hết hạn" }));
      }
      throw new Error("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.");
    }
  }

  if (!response.ok) {
    throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  }

  // Handle custom standard response error payloads
  if (data && data.error) {
    throw new Error(data.error);
  }
  
  return data;
}

export const api = {
  baseUrl: BASE_URL,

  // Detect which backend is actually serving this page (home vs Vercel backup)
  // via the X-PC-Source header. The domain is identical for both (nguyentruclam.io.vn),
  // so the hostname alone can't tell them apart.
  getServerSource: async () => {
    try {
      const resp = await fetch(`${BASE_URL}/api/health`, {
        headers: { "Cache-Control": "no-cache" },
      });
      return resp.headers.get("X-PC-Source") || "";
    } catch (e) {
      return "";
    }
  },

  // Auth & Pairing
  registerParent: (email, password) =>
    request("/api/register", { method: "POST", body: { email, password } }),

  pairDevice: (parent_email, parent_password, device_name, hardware_uuid = "web-pair") =>
    request("/api/pair", {
      method: "POST",
      body: { parent_email, parent_password, device_name, hardware_uuid },
    }),

  // Device Status & Remote Control
  getDevices: () =>
    request("/api/devices"),

  getDeviceStatus: (deviceId) =>
    request(`/api/device/${deviceId}/status`),

  sendCommand: (deviceId, command, payload = {}) =>
    request(`/api/device/${deviceId}/command`, {
      method: "POST",
      body: { command, payload },
    }),

  lockDevice: (deviceId, reason = "Bị khóa bởi Phụ huynh") =>
    request(`/api/device/${deviceId}/command`, {
      method: "POST",
      body: { command: "lock_screen", payload: { reason } },
    }),

  unlockDevice: (deviceId) =>
    request(`/api/device/${deviceId}/command`, {
      method: "POST",
      body: { command: "unlock_screen" },
    }),

  requestScreenshot: (deviceId) =>
    request(`/api/device/${deviceId}/command`, {
      method: "POST",
      body: { command: "take_screenshot" },
    }),

  sendDeviceCommand: (deviceId, command, payload = {}) =>
    request(`/api/device/${deviceId}/command`, {
      method: "POST",
      body: { command, payload },
    }),

  // Device Status
  getDeviceStatus: (deviceId) =>
    request(`/api/device/${deviceId}/status`),

  // Screenshots
  getScreenshots: (deviceId) =>
    request(`/api/device/${deviceId}/screenshots`),

  deleteScreenshot: (screenshotId) =>
    request(`/api/screenshots/${screenshotId}`, { method: "DELETE" }),

  deleteAllScreenshots: (deviceId) =>
    request(`/api/device/${deviceId}/screenshots`, { method: "DELETE" }),

  // Rules
  getRules: (deviceId) =>
    request(`/api/device/${deviceId}/rules`),

  createRule: (deviceId, ruleData) =>
    request(`/api/device/${deviceId}/rules`, {
      method: "POST",
      body: { device_id: deviceId, ...ruleData },
    }),

  deleteRule: (ruleId) =>
    request(`/api/rules/${ruleId}`, { method: "DELETE" }),

  // Process Logs
  getLogs: (deviceId, limit = 50) =>
    request(`/api/device/${deviceId}/logs?limit=${limit}`),
  getDeviceLogs: (deviceId, limit = 50) =>
    request(`/api/device/${deviceId}/logs?limit=${limit}`),

  // Alerts
  getAlerts: (deviceId, limit = 50) =>
    request(`/api/device/${deviceId}/alerts?limit=${limit}`),
  getDeviceAlerts: (deviceId, limit = 50) =>
    request(`/api/device/${deviceId}/alerts?limit=${limit}`),


  // Auth
  login: (email, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: { email, password },
    }),


  // RBAC & Sub-Account Management
  createSubAccount: (userData) =>
    request("/api/v1/users", { method: "POST", body: userData }),

  getSubAccounts: (adminEmail = "") =>
    request(`/api/v1/users?admin_email=${encodeURIComponent(adminEmail)}`),

  updateUserPermissions: (userId, permissions) =>
    request(`/api/v1/users/${userId}/permissions`, {
      method: "PUT",
      body: { permissions },
    }),

  deleteSubAccount: (userId) =>
    request(`/api/v1/users/${userId}`, { method: "DELETE" }),

  // System Storage & Cleanup Management
  getStorageMetrics: () =>
    request("/api/v1/system/storage"),

  cleanStorage: (target = "all", daysOlderThan = 0) =>
    request("/api/v1/system/storage/clean", {
      method: "POST",
      body: { target, days_older_than: daysOlderThan },
    }),

  cleanStorageByPeriod: (category, periods, periodType = "day", itemIds = null) =>
    request("/api/v1/storage/cleanup-by-period", {
      method: "POST",
      body: { category, periods, period_type: periodType, item_ids: itemIds },
    }),

  // Browser History
  getBrowserHistory: (deviceId, limit = 100, search = "", browser = "all") =>
    request(`/api/device/${deviceId}/browser-history?limit=${limit}&search=${encodeURIComponent(search)}&browser=${encodeURIComponent(browser)}`),

  // Two-Way Chat
  sendChatMessage: (deviceId, message) =>
    request(`/api/device/${deviceId}/chat`, {
      method: "POST",
      body: { message },
    }),

  getChatHistory: (deviceId, limit = 100) =>
    request(`/api/device/${deviceId}/chat/history?limit=${limit}`),

  // Silent Auto-Updater
  getAgentVersion: () =>
    request("/api/v1/agent/version"),

  packAgentZip: (version) => {
    const formData = new FormData();
    formData.append("version", version);
    return request("/api/v1/agent/pack-zip", {
      method: "POST",
      body: formData,
    });
  },

  deployAgentUpdate: (formData) =>
    request("/api/v1/agent/deploy-update", {
      method: "POST",
      body: formData,
    }),

  forceUpdateAllDevices: () =>
    request("/api/devices/force-update-all", { method: "POST" }),

  // Focus Mode (Chế độ Học bài 1 chạm)
  toggleFocusMode: (deviceId, enabled = true, durationMinutes = 60) =>
    request(`/api/device/${deviceId}/focus-mode`, {
      method: "POST",
      body: { enabled, duration_minutes: durationMinutes },
    }),

  // Usage Analytics (Phân tích Xu hướng sử dụng)
  getDeviceAnalytics: (deviceId) =>
    request(`/api/device/${deviceId}/analytics`),

  // Screen Time Today (Thời lượng sử dụng trong ngày)
  getTodayScreenTime: (deviceId) =>
    request(`/api/device/${deviceId}/screen-time/today`),

  // Remote Shutdown (Tắt máy từ xa)
  shutdownDevice: (deviceId, reason = "Thiết bị được tắt theo lệnh từ Phụ huynh") =>
    request(`/api/device/${deviceId}/shutdown`, {
      method: "POST",
      body: { reason },
    }),

  // Telegram Configuration & Testing
  getTelegramConfig: () =>
    request("/api/telegram/config"),

  saveTelegramConfig: (botToken, chatId) =>
    request("/api/telegram/config", {
      method: "POST",
      body: { bot_token: botToken, chat_id: chatId },
    }),

  sendTelegramTest: (botToken, chatId) =>
    request("/api/telegram/test", {
      method: "POST",
      body: { bot_token: botToken, chat_id: chatId },
    }),

  // Time Control & Allowed Hours
  getAllowedHours: (deviceId) =>
    request(`/api/settings/time-control/allowed-hours?device_id=${deviceId || ""}`),

  updateAllowedHours: (deviceId, schedules) =>
    request("/api/settings/time-control/allowed-hours", {
      method: "PUT",
      body: { device_id: deviceId, schedules },
    }),

  // Web & App Restrictions
  getRestrictions: (deviceId) =>
    request(`/api/settings/time-control/restrictions?device_id=${deviceId || ""}`),

  updateRestrictions: (deviceId, rules) =>
    request("/api/settings/time-control/restrictions", {
      method: "PUT",
      body: { device_id: deviceId, rules },
    }),

  // Period Settings
  getPeriodSettings: () =>
    request("/api/settings/periods"),

  updatePeriodSettings: (settings) =>
    request("/api/settings/periods", {
      method: "PUT",
      body: settings,
    }),
};


