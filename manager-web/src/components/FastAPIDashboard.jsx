import React, { useState, useEffect, useRef } from "react";
import { api, setAuthToken, clearAuthToken, isTokenExpired } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import TelegramConfigModal from "./TelegramConfigModal";
import SystemConsoleLogBox from "./SystemConsoleLogBox";
import MobileBottomNav from "./MobileBottomNav";
import AccountPermissionsSettings from "./AccountPermissionsSettings";
import StorageManagementCard from "./StorageManagementCard";
import AgentUpdateManagerCard from "./AgentUpdateManagerCard";
import BrowserHistoryView from "./BrowserHistoryView";
import DeviceChatBox from "./DeviceChatBox";
import PeriodSettingsCard from "./PeriodSettingsCard";
import TimeControlSettingsCard from "./TimeControlSettingsCard";
import QuickRulesCatalog from "./QuickRulesCatalog";
import UsageAnalyticsCard from "./UsageAnalyticsCard";
import ScreenTimeTodayCard from "./ScreenTimeTodayCard";
import {
  RefreshCw,
  LayoutDashboard,
  Camera,
  Shield,
  FileText,
  Lock,
  Unlock,
  Sun,
  Moon,
  Plus,
  Trash2,
  Target,
  GraduationCap,
  Monitor,
  Clock,
  Calendar,
  Activity,
  Timer,
  CheckCircle2,
  AppWindow,
  Globe,
  BarChart2,
  Send,
  Terminal,
  Menu,
  X,
  Users,
  MessageSquare,
  Settings,
  ChevronRight,
  ArrowLeft,
  HardDrive,
  Rocket,
  Power,
  AlertTriangle,
} from "lucide-react";

export default function FastAPIDashboard() {
  // Theme mode: 'dark' | 'light'
  const [theme, setTheme] = useState("dark");
  const styles = getThemeStyles(theme);

  // Auth state (persisted in localStorage/sessionStorage with token validation)
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    const email = localStorage.getItem("pc_auth_email") || sessionStorage.getItem("pc_auth_email");
    const token = localStorage.getItem("pc_auth_token") || sessionStorage.getItem("pc_auth_token");
    if (!email || !token) return false;
    if (isTokenExpired(token)) {
      clearAuthToken();
      return false;
    }
    return true;
  });
  const [parentEmail, setParentEmail] = useState(() => localStorage.getItem("pc_auth_email") || sessionStorage.getItem("pc_auth_email") || "");
  const [parentPassword, setParentPassword] = useState("");
  const [userRole, setUserRole] = useState(() => localStorage.getItem("pc_user_role") || sessionStorage.getItem("pc_user_role") || "admin");
  const [userPermissions, setUserPermissions] = useState(() => {
    try {
      const saved = localStorage.getItem("pc_user_permissions") || sessionStorage.getItem("pc_user_permissions");
      return saved ? JSON.parse(saved) : {
        can_view_screenshots: true,
        can_manage_rules: true,
        can_view_logs: true,
        can_remote_control: true,
        can_manage_users: true
      };
    } catch {
      return { can_view_screenshots: true, can_manage_rules: true, can_view_logs: true, can_remote_control: true, can_manage_users: true };
    }
  });
  const [isLocked, setIsLocked] = useState(false);
  const [isSystemAdmin, setIsSystemAdmin] = useState(() => (localStorage.getItem("pc_is_system_admin") === "true" || sessionStorage.getItem("pc_is_system_admin") === "true"));
  const [settingSubTab, setSettingSubTab] = useState("menu"); // 'menu' | 'rbac' | 'agent_update' | 'storage' | 'periods' | 'time_control'
  const [authMode, setAuthMode] = useState("login"); // 'login' | 'register'
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Device & Data state
  const [deviceId, setDeviceId] = useState(() => localStorage.getItem("pc_device_id") || sessionStorage.getItem("pc_device_id") || "");
  const [deviceName, setDeviceName] = useState(() => localStorage.getItem("pc_device_name") || sessionStorage.getItem("pc_device_name") || "");
  const [allDevices, setAllDevices] = useState([]);

  // Status & Data
  const [status, setStatus] = useState({ is_online: false, last_seen_at: null });
  const [activeNav, setActiveNav] = useState("overview");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  const [screenshots, setScreenshots] = useState([]);
  const [rules, setRules] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [userActionLogs, setUserActionLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isTelegramModalOpen, setIsTelegramModalOpen] = useState(false);
  const [isFocusMode, setIsFocusMode] = useState(false);

  // Khôi phục trạng thái Focus Mode (Học bài) sau khi F5 bằng cách nội suy từ rules
  React.useEffect(() => {
    if (rules && rules.length > 0) {
      const focusTargets = ["facebook.com", "tiktok.com", "youtube.com", "leagueclient.exe"];
      const isFocusActive = focusTargets.some(target => 
        rules.some(r => r.target && r.target.toLowerCase() === target)
      );
      setIsFocusMode(isFocusActive);
    } else {
      setIsFocusMode(false);
    }
  }, [rules]);

  const prevScreenshotCountRef = useRef(0);
  const lastScreenshotIdRef = useRef(null);
  const waitingForScreenshotRef = useRef(false);
  const screenshotTimeoutRef = useRef(null);

  // Helper to add interactive real-time console log entries
  const addConsoleLog = (level, stream, msg) => {
    const timeStr = new Date().toLocaleTimeString();
    const newEntry = {
      id: `act-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      time: timeStr,
      level,
      stream,
      msg
    };
    setUserActionLogs((prev) => [newEntry, ...prev.slice(0, 49)]);
  };

  // Rule creation state
  const [newRuleTarget, setNewRuleTarget] = useState("");
  const [newRuleType, setNewRuleType] = useState("app");
  const [selectedImage, setSelectedImage] = useState(null);

  // Toggle Theme Class on Root Document
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  // Listen for unauthorized session expiration
  useEffect(() => {
    const handleUnauthorized = (e) => {
      handleLogout();
      setAuthError(e.detail || "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.");
    };

    window.addEventListener("pc:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("pc:unauthorized", handleUnauthorized);
  }, []);

  // Auth: Login or Register
  const handleAuth = async (e) => {
    if (e) e.preventDefault();
    if (!parentEmail || !parentPassword) return setAuthError("Vui lòng nhập Email và Mật khẩu.");
    setAuthLoading(true);
    setAuthError("");
    try {
      if (authMode === "register") {
        await api.registerParent(parentEmail, parentPassword);
      }
      // Standard JWT login
      const res = await api.login(parentEmail, parentPassword);
      if (res.data) {
        const storage = rememberMe ? localStorage : sessionStorage;
        if (res.data.access_token) {
          setAuthToken(res.data.access_token, rememberMe);
        }
        storage.setItem("pc_auth_email", parentEmail);
        const role = res.data.role || "admin";
        const sysAdmin = res.data.is_system_admin === true;
        const perms = res.data.permissions || {
          can_view_screenshots: sysAdmin || role === "admin",
          can_manage_rules: true,
          can_view_logs: true,
          can_remote_control: true,
          can_manage_users: sysAdmin || role === "admin"
        };
        storage.setItem("pc_user_role", role);
        storage.setItem("pc_user_permissions", JSON.stringify(perms));
        storage.setItem("pc_is_system_admin", sysAdmin ? "true" : "false");
        setUserRole(role);
        setUserPermissions(perms);
        setIsSystemAdmin(sysAdmin);
        setIsLoggedIn(true);
      }
    } catch (err) {
      setAuthError(err.message || "Đăng nhập thất bại. Kiểm tra lại thông tin.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    localStorage.removeItem("pc_auth_email");
    localStorage.removeItem("pc_device_id");
    localStorage.removeItem("pc_device_name");
    localStorage.removeItem("pc_user_role");
    localStorage.removeItem("pc_user_permissions");
    localStorage.removeItem("pc_is_system_admin");
    sessionStorage.removeItem("pc_auth_email");
    sessionStorage.removeItem("pc_device_id");
    sessionStorage.removeItem("pc_device_name");
    sessionStorage.removeItem("pc_user_role");
    sessionStorage.removeItem("pc_user_permissions");
    sessionStorage.removeItem("pc_is_system_admin");
    setIsSystemAdmin(false);
    setIsLoggedIn(false);
    setParentEmail("");
    setParentPassword("");
    setDeviceId("");
    setDeviceName("");
    setScreenshots([]);
    setRules([]);
    setLogs([]);
    setAlerts([]);
  };

  const handlePair = () => {
    handleLogout();
  };

  // Poll real API with Auto-Device Discovery
  useEffect(() => {
    if (!isLoggedIn) return;

    const fetchAllData = async () => {
      try {
        // 1. Auto-discover paired devices
        let currentDeviceId = deviceId;
        const devicesRes = await api.getDevices().catch((err) => {
          if (err.message && err.message.includes("hết hạn")) {
            setIsLoggedIn(false);
          }
          return null;
        });
        if (!devicesRes || !devicesRes.data) return;

        if (devicesRes.data.devices && devicesRes.data.devices.length > 0) {
          const devList = devicesRes.data.devices;
          setAllDevices(devList);

          const matchedDevice = devList.find(d => String(d.device_id) === String(currentDeviceId) || String(d.id) === String(currentDeviceId))
            || devList.find(d => d.is_online)
            || devList[0];

          if (matchedDevice) {
            if (!currentDeviceId) {
              currentDeviceId = matchedDevice.device_id;
              setDeviceId(currentDeviceId);
              localStorage.setItem("pc_device_id", currentDeviceId);
            }
            if (matchedDevice.device_name) {
              setDeviceName(matchedDevice.device_name);
              localStorage.setItem("pc_device_name", matchedDevice.device_name);
            }
          }
        }

        if (!currentDeviceId) return;

        // 2. Fetch Device Status
        const statusRes = await api.getDeviceStatus(currentDeviceId).catch(() => null);
        if (statusRes && statusRes.data) {
          setStatus(statusRes.data);
          if (statusRes.data.device_name) {
            setDeviceName(statusRes.data.device_name);
            localStorage.setItem("pc_device_name", statusRes.data.device_name);
          }
          if (statusRes.data.is_locked !== undefined) {
            setIsLocked(Boolean(statusRes.data.is_locked));
          }
        }

        // 3. Fetch Real Screenshots & Detect REAL New Images
        const shotsRes = await api.getScreenshots(currentDeviceId).catch(() => null);
        if (shotsRes && shotsRes.data && Array.isArray(shotsRes.data.screenshots)) {
          const newShots = shotsRes.data.screenshots;
          setScreenshots(newShots);

          const latestId = newShots[0]?.id || null;
          if (waitingForScreenshotRef.current && latestId && latestId !== lastScreenshotIdRef.current) {
            waitingForScreenshotRef.current = false;
            if (screenshotTimeoutRef.current) clearTimeout(screenshotTimeoutRef.current);
            const latest = newShots[0];
            addConsoleLog("SUCCESS", "MEDIA: SCREENSHOT", `Đã nhận thành công ảnh chụp màn hình mới từ Agent! (URL: ${latest.image_url})`);
            setMessage("⚡ Đã chụp và tải lên thành công ảnh màn hình mới nhất!");
            setTimeout(() => setMessage(""), 5000);
          }
          prevScreenshotCountRef.current = newShots.length;
        }

        // 4. Fetch Rules
        const rulesRes = await api.getRules(currentDeviceId).catch(() => null);
        if (rulesRes && rulesRes.data && Array.isArray(rulesRes.data.rules)) {
          setRules(rulesRes.data.rules);
        }

        // 5. Fetch Process Logs
        const logsRes = await api.getLogs?.(currentDeviceId)?.catch(() => null);
        if (logsRes && logsRes.data && Array.isArray(logsRes.data.logs)) {
          setLogs(logsRes.data.logs);
        }

        // 6. Fetch Alerts
        const alertsRes = await api.getAlerts?.(currentDeviceId)?.catch(() => null);
        if (alertsRes && alertsRes.data && Array.isArray(alertsRes.data.alerts)) {
          setAlerts(alertsRes.data.alerts);
        }
      } catch (e) {
        // Handle fetch errors gracefully
      }
    };

    fetchAllData();
    const interval = setInterval(fetchAllData, 3000);
    return () => clearInterval(interval);
  }, [deviceId, isLoggedIn]);

  // Remote Control Handlers
  const handleLock = async () => {
    try {
      await api.sendCommand(deviceId, "lock_screen", { reason: "Khóa màn hình từ Web Dashboard" });
      setIsLocked(true);
      setMessage("Đã gửi lệnh khóa màn hình tới thiết bị.");
      addConsoleLog("SUCCESS", "LUỒNG 1: WS", "Gửi lệnh: Lock Screen -> Device OK");
    } catch (err) {
      setMessage(`Lỗi gửi lệnh khóa: ${err.message}`);
      addConsoleLog("ERROR", "LUỒNG 1: WS", `Lỗi khóa màn hình: ${err.message}`);
    }
  };

  const handleUnlock = async () => {
    try {
      await api.sendCommand(deviceId, "unlock_screen", {});
      setIsLocked(false);
      setMessage("Đã gửi lệnh Mở khóa màn hình tới thiết bị.");
      addConsoleLog("SUCCESS", "LUỒNG 1: WS", "Gửi lệnh: Unlock Screen -> Device OK");
    } catch (err) {
      setMessage(`Lỗi gửi lệnh mở khóa: ${err.message}`);
      addConsoleLog("ERROR", "LUỒNG 1: WS", `Lỗi mở khóa màn hình: ${err.message}`);
    }
  };

  const handleToggleLock = () => {
    if (isLocked) {
      handleUnlock();
    } else {
      handleLock();
    }
  };

  const [showShutdownModal, setShowShutdownModal] = useState(false);
  const [shutdownReason, setShutdownReason] = useState("Đã hết giờ dùng máy tính");
  const [isShuttingDown, setIsShuttingDown] = useState(false);

  const handleShutdownDevice = async () => {
    if (!deviceId) return setMessage("Chưa có thiết bị nào được ghép nối!");
    setIsShuttingDown(true);
    try {
      addConsoleLog("INFO", "COMMAND: SHUTDOWN", `Phát lệnh Tắt Nguồn máy tính tới thiết bị ${deviceId}...`);
      const res = await api.shutdownDevice(deviceId, shutdownReason);
      if (res && res.data) {
        setMessage(`⚡ ${res.data.msg || "Đã gửi lệnh tắt máy từ xa thành công!"}`);
        addConsoleLog("SUCCESS", "LUỒNG 1: WS", `Đã gửi lệnh tắt nguồn tới thiết bị ${deviceId} OK`);
      } else {
        setMessage("⚠️ Đã gửi lệnh tắt máy tính tới thiết bị.");
      }
      setShowShutdownModal(false);
    } catch (err) {
      setMessage(`Lỗi gửi lệnh tắt máy: ${err.message}`);
      addConsoleLog("ERROR", "LUỒNG 1: WS", `Lỗi tắt máy từ xa: ${err.message}`);
    } finally {
      setIsShuttingDown(false);
    }
  };

  const handleTakeScreenshot = async () => {
    if (!deviceId) return setMessage("Chưa có thiết bị nào ghép nối!");
    addConsoleLog("INFO", "COMMAND: SCREENSHOT", `Phát lệnh Chụp Màn Hình (take_screenshot) tới thiết bị ${deviceId}...`);
    try {
      lastScreenshotIdRef.current = screenshots[0]?.id || null;
      waitingForScreenshotRef.current = true;

      await api.requestScreenshot(deviceId);
      setMessage("⏳ Đã gửi lệnh Chụp màn hình qua WebSocket. Đang chờ Agent chụp và tải ảnh lên...");
      addConsoleLog("SUCCESS", "LUỒNG 1: WS", `Đã gửi lệnh WebSocket 'take_screenshot' thành công. Đang chờ Agent tải ảnh lên...`);

      if (screenshotTimeoutRef.current) clearTimeout(screenshotTimeoutRef.current);
      screenshotTimeoutRef.current = setTimeout(() => {
        if (waitingForScreenshotRef.current) {
          waitingForScreenshotRef.current = false;
          setMessage("⚠️ Hết thời gian chờ 15s: Thiết bị chưa gửi lại ảnh mới.");
          setTimeout(() => setMessage(""), 5000);
        }
      }, 15000);

    } catch (e) {
      waitingForScreenshotRef.current = false;
      setMessage(`Không thể chụp màn hình: ${e.message || "Thiết bị Offline"}`);
      addConsoleLog("ERROR", "COMMAND: SCREENSHOT", `Không thể gửi lệnh chụp màn hình: ${e.message || "Thiết bị Offline"}`);
    }
  };

  const handleCheckVersion = async () => {
    if (!deviceId) return setMessage("Chưa có thiết bị nào được ghép nối!");
    try {
      setMessage("⏳ Đang kiểm tra phiên bản trên máy đích...");
      const res = await api.sendCommand(deviceId, "check_version");
      if (res.data && res.data.msg) {
        setMessage(res.data.msg);
      }
      setTimeout(() => setMessage(""), 5000);
    } catch (e) {
      setMessage(`Lỗi kiểm tra phiên bản: ${e.message || e}`);
      setTimeout(() => setMessage(""), 5000);
    }
  };

  const handleDeleteScreenshot = async (e, shotId) => {
    if (e) e.stopPropagation();
    if (!window.confirm("Bạn có chắc chắn muốn xóa ảnh chụp màn hình này khỏi hệ thống?")) return;
    try {
      const res = await api.deleteScreenshot(shotId);
      if (res.data) {
        if (res.data.screenshots) {
          setScreenshots(res.data.screenshots);
        } else {
          setScreenshots((prev) => prev.filter((s) => s.id !== shotId));
        }
        setMessage("Đã xóa ảnh chụp màn hình thành công!");
        addConsoleLog("SUCCESS", "MEDIA: SCREENSHOT", `Đã xóa ảnh chụp màn hình ID: ${shotId}`);
        setTimeout(() => setMessage(""), 4000);
      }
    } catch (err) {
      setMessage(`Lỗi xóa ảnh: ${err.message}`);
      addConsoleLog("ERROR", "MEDIA: SCREENSHOT", `Lỗi xóa ảnh: ${err.message}`);
    }
  };

  const handleDeleteAllScreenshots = async () => {
    if (!deviceId) return setMessage("Chưa chọn thiết bị!");
    if (!window.confirm(`Bạn có chắc chắn muốn xóa TOÀN BỘ ${screenshots.length} ảnh chụp màn hình của thiết bị này? Dữ liệu không thể khôi phục.`)) return;
    try {
      const res = await api.deleteAllScreenshots(deviceId);
      if (res.data) {
        setScreenshots([]);
        setMessage(`Đã xóa toàn bộ ${res.data.deleted_count || 0} ảnh chụp màn hình thành công!`);
        addConsoleLog("SUCCESS", "MEDIA: SCREENSHOT", `Đã xóa sạch toàn bộ ảnh màn hình của thiết bị ${deviceId}`);
        setTimeout(() => setMessage(""), 4000);
      }
    } catch (err) {
      setMessage(`Lỗi xóa toàn bộ ảnh: ${err.message}`);
      addConsoleLog("ERROR", "MEDIA: SCREENSHOT", `Lỗi xóa toàn bộ ảnh: ${err.message}`);
    }
  };

  // Rule Handlers
  const handleAddRule = async (e) => {
    e.preventDefault();
    if (!newRuleTarget || !deviceId) return;
    addConsoleLog("INFO", "RULE: CREATE", `Đang thêm quy tắc cấm mới: [${newRuleType.toUpperCase()}] ${newRuleTarget}`);
    try {
      const res = await api.createRule(deviceId, {
        device_id: deviceId,
        rule_type: newRuleType,
        target: newRuleTarget,
        is_banned: true
      });
      // Use server response to update rules list (includes all rules)
      if (res.data && Array.isArray(res.data.rules)) {
        setRules(res.data.rules);
      }
      setMessage(`Đã thêm quy tắc cấm: ${newRuleTarget}`);
      addConsoleLog("SUCCESS", "RULE: CREATE", `Đã thêm thành công quy tắc cấm: ${newRuleTarget}`);
    } catch (err) {
      setMessage(`Lỗi thêm quy tắc: ${err.message}`);
      addConsoleLog("ERROR", "RULE: CREATE", `Lỗi thêm quy tắc cấm: ${err.message}`);
    }
    setNewRuleTarget("");
  };

  const handleDeleteRule = async (ruleId) => {
    addConsoleLog("INFO", "RULE: DELETE", `Đang xóa quy tắc cấm ID: ${ruleId}`);
    try {
      const res = await api.deleteRule(ruleId);
      if (res.data && Array.isArray(res.data.rules)) {
        setRules(res.data.rules);
      } else {
        setRules(rules.filter((r) => r.id !== ruleId));
      }
      setMessage("Đã xóa quy tắc!");
      addConsoleLog("SUCCESS", "RULE: DELETE", `Đã xóa thành công quy tắc cấm ID: ${ruleId}`);
    } catch (err) {
      setMessage(`Lỗi xóa quy tắc: ${err.message}`);
      addConsoleLog("ERROR", "RULE: DELETE", `Lỗi xóa quy tắc: ${err.message}`);
    }
  };

  const handleToggleFocusMode = async (duration = 60) => {
    if (!deviceId) return setMessage("Chưa có thiết bị nào được ghép nối!");
    const nextState = !isFocusMode;
    setMessage(nextState ? `⏳ Đang kích hoạt Chế độ Học Bài (${duration} phút)...` : "⏳ Đang tắt Chế độ Học Bài...");
    try {
      const res = await api.toggleFocusMode(deviceId, nextState, duration);
      if (res && res.data) {
        setIsFocusMode(nextState);
        if (Array.isArray(res.data.rules)) {
          setRules(res.data.rules);
        }
        setMessage(nextState ? `🎯 Đã kích hoạt Chế độ Học Bài (${duration} phút)!` : "🟢 Đã tắt Chế độ Học Bài.");
        addConsoleLog("INFO", "FOCUS: MODE", nextState ? `Kích hoạt Chế độ Học Bài (${duration} phút)` : "Tắt Chế độ Học Bài");
        setTimeout(() => setMessage(""), 5000);
      }
    } catch (e) {
      setMessage(`Lỗi Chế độ Học Bài: ${e.message || e}`);
      setTimeout(() => setMessage(""), 5000);
    }
  };

  const handleToggleCatalogRule = async (item, active, ruleId) => {
    if (!deviceId) return setMessage("Chưa có thiết bị nào được ghép nối!");
    if (active && ruleId) {
      await handleDeleteRule(ruleId);
    } else {
      addConsoleLog("INFO", "RULE: CREATE", `Đang thêm quy tắc nhanh: [${item.type.toUpperCase()}] ${item.target}`);
      try {
        const res = await api.createRule(deviceId, {
          device_id: deviceId,
          rule_type: item.type,
          target: item.target,
          is_banned: true
        });
        if (res.data && Array.isArray(res.data.rules)) {
          setRules(res.data.rules);
        }
        setMessage(`Đã thêm quy tắc cấm: ${item.name} (${item.target})`);
        setTimeout(() => setMessage(""), 4000);
      } catch (err) {
        setMessage(`Lỗi thêm quy tắc: ${err.message}`);
      }
    }
  };


  // ============================================================
  // AUTH GATE: Show login/register form if not logged in
  // ============================================================
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-[#0a0f0d] flex items-center justify-center p-4 font-sans">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="w-4 h-4 rounded-full bg-[#064E3B] border border-[#F8E7C9]" />
              <span className="text-lg font-extrabold tracking-wider text-[#F8E7C9]">
                PARENTAL<span className="font-normal opacity-90">CONTROL</span>
              </span>
            </div>
            <p className="text-xs text-zinc-500">Đăng nhập để quản lý thiết bị con em</p>
          </div>

          <form onSubmit={handleAuth} className="bg-[#111a16] border border-emerald-900/40 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex gap-2 p-1 bg-[#0a0f0d] rounded-lg">
              <button
                type="button"
                onClick={() => setAuthMode("login")}
                className={`flex-1 py-2 text-xs font-bold rounded-md transition ${
                  authMode === "login" ? "bg-[#064E3B] text-[#F8E7C9]" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Đăng Nhập
              </button>
              <button
                type="button"
                onClick={() => setAuthMode("register")}
                className={`flex-1 py-2 text-xs font-bold rounded-md transition ${
                  authMode === "register" ? "bg-[#064E3B] text-[#F8E7C9]" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Đăng Ký Mới
              </button>
            </div>

            <input
              type="email"
              placeholder="Email phụ huynh"
              value={parentEmail}
              onChange={(e) => setParentEmail(e.target.value)}
              className="w-full p-3 text-sm font-bold rounded-lg border border-emerald-900/40 bg-[#0a0f0d] text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-600"
              required
            />
            <input
              type="password"
              placeholder="Mật khẩu"
              value={parentPassword}
              onChange={(e) => setParentPassword(e.target.value)}
              className="w-full p-3 text-sm font-bold rounded-lg border border-emerald-900/40 bg-[#0a0f0d] text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-emerald-600"
              required
            />

            <div className="flex items-center gap-2 px-1">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded border-emerald-900/40 bg-[#0a0f0d] text-[#064E3B] focus:ring-[#064E3B]"
              />
              <label htmlFor="rememberMe" className="text-xs text-zinc-400 font-medium cursor-pointer select-none">
                Ghi nhớ đăng nhập (60 ngày)
              </label>
            </div>

            {authError && (
              <div className="p-2.5 rounded-lg bg-rose-900/30 border border-rose-800/50 text-xs text-rose-300 font-bold">
                {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="w-full py-3 text-sm font-bold rounded-lg bg-[#064E3B] text-[#F8E7C9] hover:bg-[#065f46] transition disabled:opacity-50"
            >
              {authLoading ? "Đang xử lý..." : authMode === "login" ? "Đăng Nhập" : "Đăng Ký & Đăng Nhập"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-screen overflow-hidden flex flex-col font-sans transition-colors duration-300 ${styles.background}`}>
      
      {/* TOP HEADER NAVIGATION */}
      <header className={`sticky top-0 z-40 border-b backdrop-blur-md transition-colors flex-none ${styles.header}`}>
        <div className="max-w-7xl mx-auto px-3 sm:px-4 h-14 flex items-center justify-between gap-2 sm:gap-4">
          
          {/* Logo & Desktop Nav */}
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded-full bg-[#064E3B] border border-[#F8E7C9]" />
              <span className={`font-extrabold tracking-wider text-sm sm:text-base ${styles.textBold}`}>
                PARENTAL<span className="font-normal opacity-90">CONTROL</span>
              </span>
            </div>

            <nav className="hidden md:flex items-center gap-5 text-xs font-bold">
              <span onClick={() => setActiveNav("overview")} className={`cursor-pointer hover:opacity-100 transition ${styles.text}`}>Home</span>
              <span onClick={() => setActiveNav("system_logs")} className={`cursor-pointer hover:opacity-100 transition ${styles.text}`}>System Console</span>
              <span onClick={() => setActiveNav("screenshots")} className={`cursor-pointer hover:opacity-100 transition ${styles.text}`}>Screenshots</span>
              <span onClick={() => setActiveNav("rules")} className={`cursor-pointer hover:opacity-100 transition ${styles.text}`}>Rules</span>
              <span onClick={() => setActiveNav("logs")} className={`cursor-pointer hover:opacity-100 transition ${styles.text}`}>Logs</span>
            </nav>
          </div>

          {/* Search, Actions & Mobile Hamburger */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => setIsTelegramModalOpen(true)}
              className={`hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${styles.buttonPrimary}`}
              title="Cấu hình Telegram Bot"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Telegram Bot</span>
            </button>

            {/* System Admin Badge */}
            {isSystemAdmin && (
              <span className="hidden lg:flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-extrabold tracking-wider bg-amber-900/30 border border-amber-600/60 text-amber-300">
                <Shield className="w-3 h-3" />
                SYSTEM ADMIN
              </span>
            )}

            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className={`p-1.5 px-2.5 sm:px-3 rounded-lg text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
            >
              {theme === "dark" ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-[#F8E7C9]" />
                  <span className="hidden sm:inline text-[#F8E7C9]">Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-[#064E3B]" />
                  <span className="hidden sm:inline text-[#064E3B]">Dark</span>
                </>
              )}
            </button>

            <button
              onClick={handlePair}
              className={`hidden sm:flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg transition ${styles.buttonPrimary}`}
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Pair Device</span>
            </button>

            {/* Mobile Hamburger Toggle */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className={`md:hidden p-1.5 rounded-lg ${styles.buttonPrimary}`}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* MOBILE SLIDE-OVER DRAWER MENU */}
        {isMobileMenuOpen && (
          <div className={`md:hidden border-b p-4 space-y-3 shadow-xl ${styles.card}`}>
            <div className="space-y-1">
              {[
                { id: "overview", label: "Overview & Controls", icon: LayoutDashboard },
                ...(isSystemAdmin ? [{ id: "system_logs", label: "System Console Log Box", icon: Terminal }] : []),
                { id: "screenshots", label: "Screenshot Gallery", icon: Camera },
                { id: "rules", label: "Rules Management", icon: Shield },
                { id: "logs", label: "Process Activity Logs", icon: FileText },
              ].map((item) => {
                const isActive = activeNav === item.id;
                const IconComponent = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveNav(item.id);
                      setIsMobileMenuOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs font-bold rounded-lg flex items-center justify-between ${
                      isActive ? styles.navActive : styles.navInactive
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <IconComponent className="w-4 h-4" />
                      <span>{item.label}</span>
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="pt-2 flex gap-2">
              <button
                onClick={() => {
                  setIsTelegramModalOpen(true);
                  setIsMobileMenuOpen(false);
                }}
                className={`flex-1 py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 ${styles.buttonPrimary}`}
              >
                <Send className="w-3.5 h-3.5" />
                <span>Telegram Config</span>
              </button>
              <button
                onClick={handlePair}
                className={`flex-1 py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 ${styles.buttonPrimary}`}
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Pair Device</span>
              </button>
            </div>

            {/* TÀI KHOẢN & THIẾT BỊ (MOBILE) */}
            <div className="pt-2 mt-2 border-t border-[#064E3B]/20 dark:border-emerald-500/20 space-y-2">
              <div className={`p-2 rounded-md border ${styles.card}`}>
                <span className={`text-[10px] font-medium ${styles.textMuted}`}>Đăng nhập:</span>
                <div className={`text-xs font-bold truncate ${styles.textBold}`}>{parentEmail}</div>
              </div>
              {allDevices.length > 1 && (
                <select
                  value={deviceId}
                  onChange={(e) => {
                    const dev = allDevices.find(d => d.device_id === e.target.value);
                    setDeviceId(e.target.value);
                    setDeviceName(dev?.device_name || "Agent PC");
                    localStorage.setItem("pc_device_id", e.target.value);
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full p-2 text-xs font-bold rounded-md border focus:outline-none ${styles.input}`}
                >
                  {allDevices.map(d => (
                    <option key={d.device_id} value={d.device_id}>
                      {d.device_name} {d.is_online ? "🟢" : "⚫"}
                    </option>
                  ))}
                </select>
              )}
              <button
                onClick={handleLogout}
                className="w-full py-2 text-xs font-bold rounded-md bg-rose-900/40 border border-rose-800/50 text-rose-300 hover:bg-rose-900/60 transition"
              >
                Đăng Xuất
              </button>
            </div>
          </div>
        )}
      </header>

      {/* MAIN CONTAINER — RESPONSIVE GRID LAYOUT */}
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6 grid grid-cols-1 md:grid-cols-12 gap-6 sm:gap-8 flex-1 overflow-hidden w-full">

        {/* LEFT COLUMN: SIDEBAR NAVIGATION */}
        <aside className="hidden md:block md:col-span-3 space-y-6 overflow-y-auto h-full pr-1">
          
          {/* Section 1: Navigation Menu */}
          <div>
            <h4 className={`text-[11px] font-bold uppercase tracking-wider mb-2 px-3 ${styles.textBold}`}>
              SECTIONS
            </h4>
            <div className="space-y-1">
              {[
                { id: "overview", label: "Overview & Controls", icon: LayoutDashboard },
                ...(isSystemAdmin ? [{ id: "system_logs", label: "System Console Log Box", icon: Terminal }] : []),
                { id: "chat", label: "Trò Chuyện 2 Chiều", icon: MessageSquare },
                { id: "browser_history", label: "Lịch Sử Web", icon: Globe },
                // Screenshots: chỉ admin hoặc được cấp quyền
                ...(isSystemAdmin || userPermissions.can_view_screenshots ? [{ id: "screenshots", label: "Screenshot Gallery", icon: Camera }] : []),
                ...(userPermissions.can_manage_rules !== false ? [{ id: "rules", label: "Rules Management", icon: Shield }] : []),
                ...(userPermissions.can_view_logs !== false ? [{ id: "logs", label: "Process Activity Logs", icon: FileText }] : []),
                // Settings: chỉ system admin hoặc admin role
                ...((isSystemAdmin || userRole === "admin" || userPermissions.can_manage_users) ? [{ id: "rbac", label: "Cài Đặt Hệ Thống", icon: Settings }] : []),
              ].map((item) => {
                const isActive = activeNav === item.id;
                const IconComponent = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveNav(item.id)}
                    className={`w-full text-left px-3 py-2 text-xs font-bold rounded-lg flex items-center justify-between transition ${
                      isActive ? styles.navActive : styles.navInactive
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <IconComponent className="w-4 h-4 stroke-[1.75]" />
                      <span>{item.label}</span>
                    </span>
                    {isActive && <span className="w-1.5 h-1.5 rounded-full bg-[#F8E7C9]" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: Active Rule Discriminators */}
          <div>
            <h4 className={`text-[11px] font-bold uppercase tracking-wider mb-2 px-3 ${styles.textBold}`}>
              DISCRIMINATORS
            </h4>
            <div className="space-y-1 text-xs">
              <div className="px-3 py-1.5 rounded-md flex justify-between items-center">
                <span className={`flex items-center gap-2 font-bold ${styles.text}`}>
                  <AppWindow className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>App Ban Rules</span>
                </span>
                <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${styles.badge}`}>
                  {rules.filter(r => r.rule_type === 'app').length}
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-md flex justify-between items-center">
                <span className={`flex items-center gap-2 font-bold ${styles.text}`}>
                  <Globe className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>Web Ban Rules</span>
                </span>
                <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${styles.badge}`}>
                  {rules.filter(r => r.rule_type === 'web').length}
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-md flex justify-between items-center">
                <span className={`flex items-center gap-2 font-bold ${styles.text}`}>
                  <Clock className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>Time Rules</span>
                </span>
                <span className={`font-mono text-[10px] px-2 py-0.5 rounded ${styles.badge}`}>
                  {rules.filter(r => r.rule_type === 'time').length}
                </span>
              </div>
            </div>
          </div>

          {/* System Footer Info */}
          <div className={`p-3.5 rounded-xl border text-[11px] space-y-1 ${styles.card}`}>
            <div className={`font-extrabold ${styles.textBold}`}>Parental Control MVP v2.0</div>
            <div className={`font-medium ${styles.textMuted}`}>Architecture: Decoupled 3-Stream</div>
            <div className={`font-medium ${styles.textMuted}`}>Security: DPAPI + HMAC Fail-Closed</div>
          </div>

        </aside>

        {/* MIDDLE COLUMN: MAIN CONTENT */}
        <main className="md:col-span-6 space-y-6 overflow-y-auto h-full pr-1 pb-16 md:pb-6">

          {/* Action Notification Banner */}
          {message && (
            <div className={`p-3 rounded-lg border text-xs font-bold flex items-center justify-between ${styles.badgeMuted}`}>
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{message}</span>
              </span>
              <button onClick={() => setMessage("")} className="opacity-70 hover:opacity-100 font-bold ml-2">✕</button>
            </div>
          )}

          {/* COMPACT CONTROL WIDGET */}
          {userPermissions.can_remote_control !== false && (
            <div className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 ${styles.card}`}>
              
              {/* Lock Screen Switch Toggle */}
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${isLocked ? "bg-rose-900/30 border border-rose-800/50 text-rose-300" : "bg-[#064E3B]/20 border border-[#064E3B]/40 text-[#F8E7C9]"}`}>
                  {isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-extrabold ${styles.textBold}`}>Khóa Màn Hình</span>
                    <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded ${isLocked ? "bg-rose-900/60 text-rose-200" : "bg-[#064E3B] text-[#F8E7C9]"}`}>
                      {isLocked ? "ĐANG KHÓA (ON)" : "MỞ KHÓA (OFF)"}
                    </span>
                  </div>
                  <p className={`text-[10px] ${styles.textMuted}`}>Bật/Tắt màn hình khóa phủ đen từ xa</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Switch Toggle Button */}
                <button
                  onClick={handleToggleLock}
                  className={`w-12 h-6 rounded-full p-0.5 transition-colors duration-300 flex items-center ${
                    isLocked ? "bg-rose-600 justify-end" : "bg-zinc-700 justify-start"
                  }`}
                  title={isLocked ? "Tắt khóa màn hình" : "Bật khóa màn hình"}
                >
                  <span className="w-5 h-5 rounded-full bg-white shadow-md transform transition-transform" />
                </button>

                {/* Compact Instant Screenshot Button */}
                {(isSystemAdmin || userPermissions?.can_view_screenshots) && (
                  <button
                    onClick={handleTakeScreenshot}
                    className={`p-2 px-3 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${styles.buttonPrimary}`}
                    title="Chụp màn hình ngay lập tức"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Chụp Ảnh</span>
                  </button>
                )}
              </div>

            </div>
          )}

          {/* DYNAMIC TAB PANEL */}

          {/* TAB 1: OVERVIEW METRICS & HEALTH */}
          {(activeNav === "overview") && (
            <div className="space-y-4">

              {/* STAT CARDS ROW */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {/* Online Status */}
                <div className={`p-3.5 rounded-xl border flex flex-col gap-1.5 ${styles.card}`}>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.textMuted}`}>Trạng Thái</span>
                  <div className="flex items-center gap-2">
                    <span className={`relative flex h-2.5 w-2.5 shrink-0`}>
                      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status.is_online ? "bg-emerald-400" : "bg-rose-400"}`} />
                      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${status.is_online ? "bg-emerald-500" : "bg-rose-500"}`} />
                    </span>
                    <span className={`text-sm font-extrabold ${styles.textBold}`}>{status.is_online ? "Online" : "Offline"}</span>
                  </div>
                  <span className={`text-[10px] ${styles.textMuted}`}>
                    {status.last_seen_at ? `Cập nhật: ${new Date(status.last_seen_at).toLocaleTimeString()}` : "Chưa kết nối"}
                  </span>
                </div>

                {/* Screenshots Count */}
                <div className={`p-3.5 rounded-xl border flex flex-col gap-1.5 ${styles.card}`}>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.textMuted}`}>Ảnh Chụp</span>
                  <span className={`text-2xl font-extrabold ${styles.textBold}`}>{screenshots.length}</span>
                  <button
                    onClick={() => setActiveNav("screenshots")}
                    className={`text-[10px] font-bold text-left hover:underline ${styles.textMuted}`}
                  >Xem thư viện →</button>
                </div>

                {/* Rules Count */}
                <div className={`p-3.5 rounded-xl border flex flex-col gap-1.5 ${styles.card}`}>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.textMuted}`}>Quy Tắc</span>
                  <span className={`text-2xl font-extrabold ${styles.textBold}`}>{rules.length}</span>
                  <button
                    onClick={() => setActiveNav("rules")}
                    className={`text-[10px] font-bold text-left hover:underline ${styles.textMuted}`}
                  >Quản lý rules →</button>
                </div>

                {/* Logs Count */}
                <div className={`p-3.5 rounded-xl border flex flex-col gap-1.5 ${styles.card}`}>
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.textMuted}`}>Process Log</span>
                  <span className={`text-2xl font-extrabold ${styles.textBold}`}>{logs.length}</span>
                  <button
                    onClick={() => setActiveNav("logs")}
                    className={`text-[10px] font-bold text-left hover:underline ${styles.textMuted}`}
                  >Xem nhật ký →</button>
                </div>
              </div>

              {/* RULE BREAKDOWN */}
              <div className={`p-4 rounded-xl border space-y-3 ${styles.card}`}>
                <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>Phân Loại Quy Tắc Đang Kích Hoạt</h4>
                <div className="space-y-2">
                  {[
                    { label: "App Ban Rules", count: rules.filter(r => r.rule_type === "app").length, color: "bg-rose-500" },
                    { label: "Web Ban Rules", count: rules.filter(r => r.rule_type === "web").length, color: "bg-amber-500" },
                    { label: "Time Rules",    count: rules.filter(r => r.rule_type === "time").length, color: "bg-blue-500" },
                  ].map(({ label, count, color }) => (
                    <div key={label} className="flex items-center gap-3 text-xs">
                      <span className={`text-[10px] font-bold w-28 shrink-0 ${styles.textMuted}`}>{label}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${color} transition-all duration-500`}
                          style={{ width: rules.length > 0 ? `${(count / rules.length) * 100}%` : "0%" }}
                        />
                      </div>
                      <span className={`font-extrabold w-6 text-right ${styles.textBold}`}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* QUICK ACTIONS */}
              <div className={`p-4 rounded-xl border space-y-3 ${styles.card}`}>
                <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>Hành Động Nhanh</h4>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  <button
                    onClick={handleTakeScreenshot}
                    className={`p-3 rounded-lg border text-xs font-bold flex flex-col items-center gap-1.5 transition hover:border-[#064E3B] ${styles.card}`}
                  >
                    <Camera className="w-5 h-5 text-cyan-400" />
                    <span>Chụp Màn Hình</span>
                  </button>
                  <button
                    onClick={() => handleToggleFocusMode(60)}
                    className={`p-3 rounded-lg border text-xs font-bold flex flex-col items-center gap-1.5 transition ${
                      isFocusMode ? "bg-amber-950/60 border-amber-500 text-amber-300" : `${styles.card} hover:border-amber-500`
                    }`}
                  >
                    <Target className={`w-5 h-5 ${isFocusMode ? "text-amber-400 animate-pulse" : "text-amber-400"}`} />
                    <span>{isFocusMode ? "Tắt Học Bài" : "🎯 Học Bài (1h)"}</span>
                  </button>
                  <button
                    onClick={() => setActiveNav("system_logs")}
                    className={`p-3 rounded-lg border text-xs font-bold flex flex-col items-center gap-1.5 transition hover:border-[#064E3B] ${styles.card}`}
                  >
                    <Terminal className="w-5 h-5 text-emerald-400" />
                    <span>System Console</span>
                  </button>
                  <button
                    onClick={() => setActiveNav("rules")}
                    className={`p-3 rounded-lg border text-xs font-bold flex flex-col items-center gap-1.5 transition hover:border-[#064E3B] ${styles.card}`}
                  >
                    <Shield className="w-5 h-5 text-blue-400" />
                    <span>Quản Lý Rules</span>
                  </button>
                  <button
                    onClick={() => setShowShutdownModal(true)}
                    className={`p-3 rounded-lg border text-xs font-bold flex flex-col items-center gap-1.5 transition bg-rose-950/20 border-rose-800/40 text-rose-300 hover:bg-rose-900/40 hover:border-rose-600`}
                    title="Tắt nguồn thiết bị từ xa (Hẹn giờ 10s)"
                  >
                    <Power className="w-5 h-5 text-rose-400" />
                    <span>Tắt Máy Từ Xa</span>
                  </button>
                </div>
              </div>

              {/* SCREEN TIME TODAY STATS */}
              {deviceId && (
                <ScreenTimeTodayCard deviceId={deviceId} styles={styles} />
              )}

              {/* USAGE ANALYTICS & TRENDS */}
              {deviceId && (
                <UsageAnalyticsCard deviceId={deviceId} styles={styles} />
              )}


              {/* LATEST SCREENSHOTS PREVIEW */}
              {screenshots.length > 0 && (
                <div className={`p-4 rounded-xl border space-y-3 ${styles.card}`}>
                  <div className="flex items-center justify-between">
                    <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>Ảnh Chụp Gần Nhất</h4>
                    <button
                      onClick={() => setActiveNav("screenshots")}
                      className={`text-[10px] font-bold hover:underline ${styles.textMuted}`}
                    >Xem tất cả →</button>
                  </div>
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                    {screenshots.slice(0, 4).map((shot, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedImage(shot.image_url || shot.url)}
                        className="aspect-video rounded-lg overflow-hidden border border-zinc-700 hover:border-[#064E3B] transition"
                      >
                        <img
                          src={shot.image_url || shot.url}
                          alt="Screenshot"
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            if (!e.target.dataset.triedFallback) {
                              e.target.dataset.triedFallback = "true";
                              const p = (shot.image_url || shot.url || "");
                              e.target.src = p.includes("/static/") ? `/static/${p.split("/static/")[1]}` : p;
                            }
                          }}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* RECENT ALERTS */}
              {alerts.length > 0 && (
                <div className={`p-4 rounded-xl border space-y-3 ${styles.card}`}>
                  <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>Cảnh Báo Gần Nhất</h4>
                  <div className="space-y-1.5">
                    {alerts.slice(0, 5).map((alert, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs p-2 rounded-lg bg-rose-900/20 border border-rose-800/30">
                        <span className="text-rose-400 font-bold shrink-0">[{alert.alert_type || "ALERT"}]</span>
                        <span className={`${styles.textMuted} flex-1 truncate`}>{alert.message}</span>
                        <span className={`text-[9px] shrink-0 ${styles.textMuted}`}>
                          {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}


          {/* TAB 2: DEDICATED SYSTEM CONSOLE LOG BOX */}
          {(activeNav === "system_logs") && (
            <div className="space-y-6">
              <SystemConsoleLogBox theme={theme} realLogs={logs} alerts={alerts} status={status} userActionLogs={userActionLogs} />
            </div>
          )}


          {/* TAB 1: SCREENSHOTS GALLERY */}
          {(activeNav === "screenshots") && (
            <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
                  <Camera className="w-4 h-4 stroke-[1.75]" />
                  <span>Thư Viện Ảnh Chụp Màn Hình ({screenshots.length})</span>
                </h3>
                <div className="flex items-center gap-2">
                  {screenshots.length > 0 && (
                    <button
                      onClick={handleDeleteAllScreenshots}
                      className="px-2.5 py-1 text-xs font-bold rounded-lg bg-rose-600/20 border border-rose-500/40 text-rose-300 hover:bg-rose-600/30 flex items-center gap-1.5 transition active:scale-95"
                      title="Xóa tất cả ảnh của thiết bị này"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Xóa Tất Cả Ảnh</span>
                    </button>
                  )}
                  <span className={`text-[10px] ${styles.textBold}`}>Auto-refresh 5s</span>
                </div>
              </div>

              {screenshots.length === 0 ? (
                <div className={`text-center py-10 text-xs italic ${styles.textMuted}`}>
                  Chưa có ảnh chụp màn hình. Hãy bấm "Chụp Màn Hình" ở trên để ghi nhận khoảnh khắc.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {screenshots.map((shot) => {
                    const fullUrl = shot.image_url.startsWith("http")
                      ? shot.image_url
                      : `${api.baseUrl}${shot.image_url}`;
                    return (
                      <div
                        key={shot.id}
                        onClick={() => setSelectedImage(fullUrl)}
                        className={`group relative rounded-lg overflow-hidden border cursor-pointer transition hover:border-[#064E3B] ${styles.card}`}
                      >
                        <img
                          src={fullUrl}
                          alt="Screenshot"
                          onError={(e) => {
                            if (!e.target.dataset.triedFallback) {
                              e.target.dataset.triedFallback = "true";
                              e.target.src = shot.image_url.startsWith("/") ? shot.image_url : `/${shot.image_url}`;
                            }
                          }}
                          className="w-full h-40 object-contain bg-black/40 transition transform group-hover:scale-105"
                        />
                        {/* Hover Action: Delete Button */}
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition z-10">
                          <button
                            onClick={(e) => handleDeleteScreenshot(e, shot.id)}
                            className="p-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-700 text-white shadow-lg transition active:scale-90"
                            title="Xóa ảnh này"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="absolute inset-x-0 bottom-0 p-1.5 bg-black/85 text-[10px] font-mono text-[#F8E7C9] truncate text-center flex items-center justify-center gap-1">
                          <Clock className="w-3 h-3 opacity-80 text-[#F8E7C9]" />
                          <span className="text-[#F8E7C9]">{new Date(shot.timestamp).toLocaleString()}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: RULES MANAGEMENT */}
          {(activeNav === "rules") && (
            <div className={`p-4 sm:p-5 rounded-xl border space-y-5 ${styles.card}`}>
              <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
                <Shield className="w-4 h-4 stroke-[1.75]" />
                <span>Quản Lý Quy Tắc Cấm (Push tức thời)</span>
              </h3>

              {/* Form Add Rule */}
              <form onSubmit={handleAddRule} className={`p-3.5 rounded-lg border flex flex-col sm:flex-row gap-2 items-stretch sm:items-end ${styles.card}`}>
                <div>
                  <label className={`block text-[10px] font-bold uppercase mb-1 ${styles.textBold}`}>Loại Rule</label>
                  <select
                    value={newRuleType}
                    onChange={(e) => setNewRuleType(e.target.value)}
                    className={`w-full sm:w-auto text-xs p-2 rounded-md border focus:outline-none font-bold ${styles.input}`}
                  >
                    <option value="app">App (.exe)</option>
                    <option value="web">Web (Domain)</option>
                  </select>
                </div>
                <div className="flex-1 min-w-[140px]">
                  <label className={`block text-[10px] font-bold uppercase mb-1 ${styles.textBold}`}>Tên Tệp / Domain</label>
                  <input
                    type="text"
                    placeholder={newRuleType === "app" ? "e.g. game.exe" : "e.g. facebook.com"}
                    value={newRuleTarget}
                    onChange={(e) => setNewRuleTarget(e.target.value)}
                    className={`w-full text-xs p-2 rounded-md border focus:outline-none font-bold ${styles.input}`}
                  />
                </div>
                <button
                  type="submit"
                  className={`px-4 py-2 text-xs font-bold rounded-md transition flex items-center justify-center gap-1 ${styles.buttonPrimary}`}
                >
                  <Plus className="w-3.5 h-3.5 text-[#F8E7C9]" />
                  <span className="text-[#F8E7C9]">Thêm Rule</span>
                </button>
              </form>

              {/* QUICK RULES 1-CLICK CATALOG */}
              <QuickRulesCatalog
                currentRules={rules}
                onToggleRule={handleToggleCatalogRule}
                styles={styles}
              />

              {/* List Rules */}
              <div className="space-y-2">
                <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
                  Danh Sách Quy Tắc Đang Áp Dụng ({rules.filter(r => r.rule_type !== 'time').length})
                </h4>

                {rules.filter(r => r.rule_type !== 'time').length === 0 ? (
                  <p className={`text-xs italic text-center py-4 ${styles.textMuted}`}>Chưa có quy tắc cấm nào.</p>
                ) : (
                  rules.filter(r => r.rule_type !== 'time').map((rule) => (
                    <div key={rule.id} className={`p-2.5 rounded-lg border flex items-center justify-between text-xs ${styles.card}`}>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${styles.badge}`}>
                          {rule.rule_type}
                        </span>
                        <span className={`font-mono font-bold truncate max-w-[140px] sm:max-w-none ${styles.textBold}`}>{rule.target}</span>
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-[10px] font-bold text-rose-600 dark:text-rose-400 hover:text-rose-700 px-2 py-0.5 rounded border border-rose-800/40 hover:bg-rose-900/30 transition flex items-center gap-1"
                      >
                        <Trash2 className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                        <span>Xóa</span>
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB: PROCESS ACTIVITY LOGS (Real Data from Backend) */}
          {(activeNav === "logs") && userPermissions.can_view_logs !== false && (
            <div className={`p-4 sm:p-5 rounded-xl border space-y-3 ${styles.card}`}>
              <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
                <FileText className="w-4 h-4 stroke-[1.75]" />
                <span>Nhật Ký Hoạt Động Tiến Trình ({logs.length} bản ghi)</span>
              </h3>
              {logs.length === 0 ? (
                <p className={`text-xs italic text-center py-6 ${styles.textMuted}`}>Chưa có nhật ký hoạt động. Agent sẽ tự gửi log định kỳ khi chạy.</p>
              ) : (
                <div className="space-y-2 font-mono text-xs max-h-[400px] overflow-y-auto">
                  {logs.map((log) => (
                    <div key={log.id} className={`p-2.5 rounded-lg border flex justify-between items-center ${styles.card}`}>
                      <div>
                        <span className={`font-bold ${styles.textBold}`}>{log.process_name}</span>
                        <p className={`text-[11px] font-medium truncate max-w-[160px] sm:max-w-xs ${styles.textMuted}`}>{log.window_title || "—"}</p>
                      </div>
                      <span className={`text-[10px] font-bold whitespace-nowrap ${styles.textBold}`}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: BROWSER HISTORY LOG ENGINE */}
          {(activeNav === "browser_history") && (
            <BrowserHistoryView theme={theme} deviceId={deviceId} />
          )}

          {/* TAB: REAL-TIME TWO-WAY CHAT */}
          {(activeNav === "chat") && (
            <DeviceChatBox theme={theme} deviceId={deviceId} isOnline={status.is_online} />
          )}

          {/* TAB: SYSTEM SETTINGS & SUB-PAGE ROUTING */}
          {(activeNav === "rbac") && (userRole === "admin" || userPermissions.can_manage_users) && (
            <div className="space-y-4">
              
              {/* MASTER SETTINGS MENU (1-LINE ITEM ROWS) */}
              {settingSubTab === "menu" && (
                <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
                  <div className="flex items-center gap-3 pb-3 border-b border-opacity-20">
                    <div className="p-2.5 rounded-lg bg-[#064E3B]/20 border border-[#064E3B]/40 text-[#F8E7C9]">
                      <Settings className="w-5 h-5 stroke-[1.75]" />
                    </div>
                    <div>
                      <h2 className={`text-base font-extrabold ${styles.textBold}`}>
                        Cài Đặt Hệ Thống & Quản Lý
                      </h2>
                      <p className={`text-xs font-medium ${styles.textMuted}`}>
                        Chọn phần cài đặt bên dưới để điều chỉnh riêng từng danh mục.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2 pt-1">
                    {/* Row 1: Sub-Accounts & RBAC */}
                    <button
                      onClick={() => setSettingSubTab("rbac")}
                      className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition hover:border-[#064E3B] ${styles.card}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-[#064E3B]/20 text-[#F8E7C9]">
                          <Users className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <h4 className={`text-xs font-bold ${styles.textBold}`}>Phân Quyền & Tài Khoản Phụ (RBAC)</h4>
                          <p className={`text-[10px] ${styles.textMuted}`}>Tạo tài khoản gia đình và cấp quyền quản lý từng tính năng</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-zinc-500" />
                    </button>

                    {/* Row 2: Silent Auto-Updater */}
                    <button
                      onClick={() => setSettingSubTab("agent_update")}
                      className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition hover:border-[#064E3B] ${styles.card}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-emerald-900/30 text-emerald-300">
                          <Rocket className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <h4 className={`text-xs font-bold ${styles.textBold}`}>Cập Nhật Agent Từ Xa (Silent Auto-Updater)</h4>
                          <p className={`text-[10px] ${styles.textMuted}`}>Upload bản build `.zip` mới và phát lệnh nâng cấp ngầm toàn bộ Agent</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-zinc-500" />
                    </button>

                    {/* Row 3: Server Storage & Cleanup */}
                    <button
                      onClick={() => setSettingSubTab("storage")}
                      className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition hover:border-[#064E3B] ${styles.card}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-900/30 text-blue-300">
                          <HardDrive className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <h4 className={`text-xs font-bold ${styles.textBold}`}>Quản Lý Bộ Nhớ & Dọn Dẹp Server</h4>
                          <p className={`text-[10px] ${styles.textMuted}`}>Theo dõi dung lượng đĩa, nén SQLite DB và dọn dẹp log/ảnh chụp</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-zinc-500" />
                    </button>

                    {/* Row 4: Period Settings */}
                    <button
                      onClick={() => setSettingSubTab("periods")}
                      className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition hover:border-[#064E3B] ${styles.card}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-purple-900/30 text-purple-300">
                          <Activity className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <h4 className={`text-xs font-bold ${styles.textBold}`}>Cài Đặt Chu Kỳ (Screenshot & Heartbeat)</h4>
                          <p className={`text-[10px] ${styles.textMuted}`}>Điều chỉnh tần suất chụp màn hình và tần suất kiểm tra kết nối</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-zinc-500" />
                    </button>

                    {/* Row 5: Time Control */}
                    <button
                      onClick={() => setSettingSubTab("time_control")}
                      className={`w-full p-3.5 rounded-xl border flex items-center justify-between transition hover:border-[#064E3B] ${styles.card}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-amber-900/30 text-amber-300">
                          <Clock className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <h4 className={`text-xs font-bold ${styles.textBold}`}>Kiểm Soát Thời Gian Dùng Máy</h4>
                          <p className={`text-[10px] ${styles.textMuted}`}>Khung giờ được dùng máy, chặn & giới hạn thời gian web/ứng dụng</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-zinc-500" />
                    </button>
                  </div>
                </div>
              )}

              {/* DEDICATED SUB-PAGE: RBAC PERMISSIONS */}
              {settingSubTab === "rbac" && (
                <div className="space-y-4">
                  <button
                    onClick={() => setSettingSubTab("menu")}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Quay Lại Danh Sách Cài Đặt</span>
                  </button>
                  <AccountPermissionsSettings theme={theme} adminEmail={parentEmail} />
                </div>
              )}

              {/* DEDICATED SUB-PAGE: AGENT AUTO-UPDATER */}
              {settingSubTab === "agent_update" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setSettingSubTab("menu")}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
                    >
                      <ArrowLeft className="w-3.5 h-3.5" />
                      <span>Quay Lại Danh Sách Cài Đặt</span>
                    </button>
                    <button
                      onClick={handleCheckVersion}
                      className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonPrimary}`}
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Kiểm tra Phiên Bản Agent</span>
                    </button>
                  </div>
                  <AgentUpdateManagerCard theme={theme} />
                </div>
              )}

              {/* DEDICATED SUB-PAGE: STORAGE CLEANUP */}
              {settingSubTab === "storage" && (
                <div className="space-y-4">
                  <button
                    onClick={() => setSettingSubTab("menu")}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Quay Lại Danh Sách Cài Đặt</span>
                  </button>
                  <StorageManagementCard theme={theme} deviceId={deviceId} />
                </div>
              )}

              {/* DEDICATED SUB-PAGE: PERIOD SETTINGS */}
              {settingSubTab === "periods" && (
                <div className="space-y-4">
                  <button
                    onClick={() => setSettingSubTab("menu")}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Quay Lại Danh Sách Cài Đặt</span>
                  </button>
                  <PeriodSettingsCard theme={theme} deviceId={deviceId} />
                </div>
              )}

              {/* DEDICATED SUB-PAGE: TIME CONTROL */}
              {settingSubTab === "time_control" && (
                <div className="space-y-4">
                  <button
                    onClick={() => setSettingSubTab("menu")}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Quay Lại Danh Sách Cài Đặt</span>
                  </button>
                  <TimeControlSettingsCard theme={theme} deviceId={deviceId} />
                </div>
              )}

            </div>
          )}

        </main>

        {/* RIGHT COLUMN: INFO PANEL & QUICK STATUS */}
        <aside className="hidden md:block md:col-span-3 space-y-6 overflow-y-auto h-full pl-1">

          {/* CARD: DEVICE REAL-TIME STATUS */}
          <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
            <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
              ON THIS PAGE / DEVICE INFO
            </h4>

            {/* Status Indicator */}
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-[#064E3B]/10 border-[#064E3B]/40">
              <span className="relative flex h-3 w-3 shrink-0">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status.is_online ? "bg-[#064E3B] dark:bg-emerald-400" : "bg-rose-400"}`} />
                <span className={`relative inline-flex rounded-full h-3 w-3 ${status.is_online ? "bg-[#064E3B] dark:bg-emerald-500" : "bg-rose-500"}`} />
              </span>
              <div>
                <div className={`text-xs font-extrabold flex items-center gap-1.5 ${styles.textBold}`}>
                  <Monitor className="w-3.5 h-3.5 stroke-[1.75]" />
                  <span>{status.is_online ? "WS CONNECTED" : "OFFLINE"}</span>
                </div>
                <div className={`text-[10px] font-medium ${styles.textMuted}`}>
                  Heartbeat 15s interval
                </div>
              </div>
            </div>

            {/* Device Info Fields */}
            <div className="space-y-2 text-xs">
              <div className="flex justify-between border-b border-opacity-20 pb-1">
                <span className={`font-medium ${styles.textMuted}`}>Device Name</span>
                <span className={`font-bold ${styles.textBold}`}>{deviceName}</span>
              </div>
              <div className="flex justify-between border-b border-opacity-20 pb-1">
                <span className={`font-medium ${styles.textMuted}`}>Device ID</span>
                <span className={`font-mono font-bold text-[10px] truncate max-w-[110px] ${styles.textBold}`}>{deviceId}</span>
              </div>
              <div className="flex justify-between">
                <span className={`font-medium ${styles.textMuted}`}>Last Heartbeat</span>
                <span className={`text-[10px] font-mono font-bold ${styles.textBold}`}>
                  {status.last_seen_at ? new Date(status.last_seen_at).toLocaleTimeString() : "N/A"}
                </span>
              </div>
            </div>
          </div>

          {/* DEVICE SELECTOR & ACCOUNT CARD */}
          <div className={`p-4 sm:p-5 rounded-xl border space-y-3 ${styles.card}`}>
            <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
              TÀI KHOẢN & THIẾT BỊ
            </h4>
            <div className="space-y-2 text-xs">
              <div className={`p-2 rounded-md border ${styles.card}`}>
                <span className={`text-[10px] font-medium ${styles.textMuted}`}>Đăng nhập:</span>
                <div className={`font-bold truncate ${styles.textBold}`}>{parentEmail}</div>
              </div>
              {allDevices.length > 1 && (
                <select
                  value={deviceId}
                  onChange={(e) => {
                    const dev = allDevices.find(d => d.device_id === e.target.value);
                    setDeviceId(e.target.value);
                    setDeviceName(dev?.device_name || "Agent PC");
                    localStorage.setItem("pc_device_id", e.target.value);
                  }}
                  className={`w-full p-2 text-xs font-bold rounded-md border focus:outline-none ${styles.input}`}
                >
                  {allDevices.map(d => (
                    <option key={d.device_id} value={d.device_id}>
                      {d.device_name} {d.is_online ? "🟢" : "⚫"}
                    </option>
                  ))}
                </select>
              )}
              <button
                onClick={handleLogout}
                className="w-full py-2 sm:py-1.5 text-xs font-bold rounded-md bg-rose-900/40 border border-rose-800/50 text-rose-300 hover:bg-rose-900/60 transition"
              >
                Đăng Xuất
              </button>
            </div>
          </div>

        </aside>

      </div>

      {/* MOBILE FIXED BOTTOM NAVIGATION BAR */}
      <MobileBottomNav
        activeNav={activeNav}
        setActiveNav={setActiveNav}
        theme={theme}
      />

      {/* Telegram Config Modal */}
      <TelegramConfigModal
        isOpen={isTelegramModalOpen}
        onClose={() => setIsTelegramModalOpen(false)}
        theme={theme}
      />

      {/* Remote Shutdown Confirmation Modal */}
      {showShutdownModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="max-w-md w-full p-5 sm:p-6 rounded-2xl border border-rose-500/40 shadow-2xl space-y-4 bg-zinc-950 text-white animate-in fade-in zoom-in duration-200">
            <div className="flex items-center gap-3 text-rose-400 border-b border-rose-900/40 pb-3">
              <div className="p-2 rounded-xl bg-rose-950/60 border border-rose-700/50">
                <AlertTriangle className="w-6 h-6 text-rose-400 animate-pulse" />
              </div>
              <div>
                <h3 className="text-sm font-black uppercase tracking-wider text-rose-300">
                  Xác Nhận Tắt Nguồn Thiết Bị
                </h3>
                <p className="text-[11px] text-zinc-400">
                  Lệnh tắt máy tính từ xa (Hẹn giờ 10 giây)
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 text-xs text-rose-200/90 leading-relaxed space-y-2">
              <p>
                ⚠️ <b>LƯU Ý QUAN TRỌNG:</b> Sau khi gửi lệnh, máy tính của con sẽ đếm ngược <b>10 giây</b> và <b>TẮT NGUỒN HOÀN TOÀN</b>.
              </p>
              <p className="text-[11px] text-zinc-300 opacity-90">
                * Bạn chỉ có thể bật lại máy tính bằng cách nhấn trực tiếp nút nguồn vật lý trên thùng máy/laptop của con.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-zinc-300">Lý do tắt máy (Hiển thị cho con):</label>
              <input
                type="text"
                value={shutdownReason}
                onChange={(e) => setShutdownReason(e.target.value)}
                placeholder="Nhập lý do hoặc chọn nhanh bên dưới..."
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-xs focus:border-rose-500 outline-none text-zinc-100"
              />
              <div className="flex flex-wrap gap-1.5 pt-1">
                {["Đã hết giờ dùng máy tính", "Đến giờ đi ngủ", "Tắt máy nghỉ ngơi"].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setShutdownReason(preset)}
                    className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition"
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setShowShutdownModal(false)}
                disabled={isShuttingDown}
                className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-xs font-semibold text-zinc-300 transition"
              >
                Hủy Bỏ
              </button>
              <button
                type="button"
                onClick={handleShutdownDevice}
                disabled={isShuttingDown}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-rose-950/50"
              >
                <Power className="w-4 h-4" />
                <span>{isShuttingDown ? "Đang gửi lệnh..." : "Xác Nhận Tắt Máy"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lightbox Modal */}
      {selectedImage && (
        <div 
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-5xl max-h-full">
            <img
              src={selectedImage}
              alt="Enlarged screenshot"
              onError={(e) => {
                if (!e.target.dataset.triedFallback && selectedImage) {
                  e.target.dataset.triedFallback = "true";
                  const relativePath = selectedImage.includes("/static/")
                    ? "/static/" + selectedImage.split("/static/")[1]
                    : selectedImage;
                  e.target.src = relativePath.startsWith("/") ? relativePath : `/${relativePath}`;
                }
              }}
              className="max-w-full max-h-[90vh] object-contain rounded-xl border border-emerald-900 shadow-2xl"
            />
          </div>
        </div>
      )}

    </div>
  );
}
