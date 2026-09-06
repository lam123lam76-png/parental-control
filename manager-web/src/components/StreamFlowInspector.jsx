import React, { useState, useEffect } from "react";
import { Zap, AlertTriangle, Truck, RefreshCw, CheckCircle2, ShieldCheck, Activity } from "lucide-react";
import { getThemeStyles } from "../lib/theme";
import { api } from "../lib/api";

export default function StreamFlowInspector({ theme = "dark", deviceId }) {
  const styles = getThemeStyles(theme);
  const [isOnline, setIsOnline] = useState(false);
  const [lastSeen, setLastSeen] = useState("Chưa có");
  const [alertsCount, setAlertsCount] = useState(0);
  const [recentLogsCount, setRecentLogsCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");

  const fetchLiveTelemetry = async () => {
    try {
      if (deviceId) {
        // 1. Device status
        const resStatus = await api.getDeviceStatus(deviceId).catch(() => null);
        if (resStatus) {
          const d = resStatus.data || resStatus;
          setIsOnline(Boolean(d.is_online));
          if (d.last_seen_at) setLastSeen(d.last_seen_at);
        }

        // 2. Alerts
        const resAlerts = await api.getDeviceAlerts(deviceId, 10).catch(() => null);
        if (resAlerts) {
          const list = resAlerts.data?.alerts || resAlerts.alerts || [];
          setAlertsCount(list.length);
        }

        // 3. Process logs
        const resLogs = await api.getDeviceLogs(deviceId, 50).catch(() => null);
        if (resLogs) {
          const list = resLogs.data?.logs || resLogs.logs || [];
          setRecentLogsCount(list.length);
        }
      }
    } catch {}
  };

  useEffect(() => {
    fetchLiveTelemetry();
    const interval = setInterval(fetchLiveTelemetry, 10000);
    return () => clearInterval(interval);
  }, [deviceId]);

  const handleManualSync = async () => {
    setIsSyncing(true);
    setSyncMsg("");
    try {
      if (deviceId) {
        await api.sendDeviceCommand(deviceId, "refresh_rules");
        setSyncMsg("Đã gửi tín hiệu đồng bộ tức thời tới Agent!");
      } else {
        setSyncMsg("Vui lòng chọn thiết bị trước khi đồng bộ.");
      }
    } catch {
      setSyncMsg("Thiết bị hiện đang offline hoặc lỗi kết nối.");
    } finally {
      setIsSyncing(false);
      fetchLiveTelemetry();
      setTimeout(() => setSyncMsg(""), 5000);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* SECTION HEADER */}
      <div className="flex items-center justify-between">
        <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.text}`}>
          <Activity className="w-4 h-4 stroke-[1.75]" />
          <span>Bảng Giám Sát Trực Quan 3 Luồng Thông Tin (Decoupled 3-Stream Flow)</span>
        </h3>
        <span className={`text-[10px] px-2 py-0.5 rounded ${styles.badge}`}>
          Live Telemetry
        </span>
      </div>

      {/* 3 STREAM VISUAL CARDS GRID */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* LUỒNG 1: TUYẾN SINH TỬ (CLOUD POLLING 5s) */}
        <div className={`p-5 rounded-xl border flex flex-col justify-between relative overflow-hidden ${styles.card}`}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] uppercase px-2 py-0.5 rounded ${styles.badge}`}>
                Luồng 1: Tuyến Sinh Tử
              </span>
              <span className="flex h-2.5 w-2.5 relative">
                {isOnline ? (
                  <>
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
                  </>
                ) : (
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary" />
                )}
              </span>
            </div>

            <div>
              <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
                <Zap className="w-4 h-4 text-primary stroke-[1.75]" />
                <span>Cloud Polling Channel (5s)</span>
              </h4>
              
            </div>

            <div className={`space-y-1.5 text-xs font-mono ${styles.text}`}>
              <div className="flex justify-between">
                <span className="font-semibold">Trạng Thái Kênh:</span>
                <span className={isOnline ? "text-primary font-bold" : "text-rose-400 font-bold"}>
                  {isOnline ? "Trực Tuyến (Online)" : "Ngoại Tuyến (Offline)"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Lần Cuối Thấy:</span>
                <span className={styles.textBold}>{lastSeen}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Nhịp Tim Mặc Định:</span>
                <span className={styles.textBold}>15 Giây</span>
              </div>
            </div>
          </div>

          <div className={`mt-4 pt-3 border-t border-opacity-20 text-[10px] font-mono flex items-center gap-1 ${styles.textBold}`}>
            <CheckCircle2 className="w-3 h-3" />
            <span>{isOnline ? "Agent đang online (polling 5s)" : "Chờ Agent kết nối lại..."}</span>
          </div>
        </div>

        {/* LUỒNG 2: TUYẾN BÁO ĐỘNG (HTTP ALERT QUEUE) */}
        <div className={`p-5 rounded-xl border flex flex-col justify-between relative overflow-hidden ${styles.card}`}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] uppercase px-2 py-0.5 rounded ${styles.badge}`}>
                Luồng 2: Tuyến Báo Động
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-primary" />
            </div>

            <div>
              <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
                <AlertTriangle className="w-4 h-4 text-primary stroke-[1.75]" />
                <span>HTTP Fast-Track Alert Queue</span>
              </h4>
              
            </div>

            <div className={`space-y-1.5 text-xs font-mono ${styles.text}`}>
              <div className="flex justify-between">
                <span className="font-semibold">Mức Ưu Tiên:</span>
                <span className={styles.textBold}>Cao Nhất (Tức Thời)</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Thời Gian Gửi Lại:</span>
                <span className={styles.textBold}>3 Giây / Lần</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Cảnh Báo Gần Nhất:</span>
                <span className={styles.textBold}>{alertsCount} Cảnh Báo</span>
              </div>
            </div>
          </div>

          <div className={`mt-4 pt-3 border-t border-opacity-20 text-[10px] font-mono flex items-center gap-1 ${styles.textBold}`}>
            <ShieldCheck className="w-3 h-3 text-primary" />
            <span>Tuyến Báo Động độc lập với kênh polling</span>
          </div>
        </div>

        {/* LUỒNG 3: TUYẾN XE TẢI (BATCH LOG UPLOAD) */}
        <div className={`p-5 rounded-xl border flex flex-col justify-between relative overflow-hidden ${styles.card}`}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className={`text-[10px] uppercase px-2 py-0.5 rounded ${styles.badge}`}>
                Luồng 3: Tuyến Xe Tải
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-primary" />
            </div>

            <div>
              <h4 className={`text-xs font-bold flex items-center gap-1.5 ${styles.textBold}`}>
                <Truck className="w-4 h-4 text-primary stroke-[1.75]" />
                <span>Batch Process Log Upload</span>
              </h4>
              
            </div>

            <div className={`space-y-1.5 text-xs font-mono ${styles.text}`}>
              <div className="flex justify-between">
                <span className="font-semibold">Chu Kỳ Batch:</span>
                <span className={styles.textBold}>300s (5 phút)</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Bản Ghi Gần Nhất:</span>
                <span className={styles.textBold}>{recentLogsCount} Nhật ký</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Cơ Chế:</span>
                <span className={styles.textBold}>Tự Động & Không Nghẽn</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-opacity-20 space-y-2">
            {syncMsg && <div className={`text-[10px] font-mono ${styles.textBold}`}>{syncMsg}</div>}
            <button
              onClick={handleManualSync}
              disabled={isSyncing}
              className={`w-full py-1.5 text-xs font-bold rounded flex items-center justify-center gap-1.5 ${styles.buttonPrimary}`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin" : ""}`} />
              <span>{isSyncing ? "Đang gửi tín hiệu..." : "Kích Hoạt Đồng Bộ Ngay"}</span>
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}

