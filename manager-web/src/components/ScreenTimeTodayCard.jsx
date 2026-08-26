import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Clock, Laptop, Globe, RefreshCw, Sparkles, Activity, AlertCircle } from "lucide-react";

export default function ScreenTimeTodayCard({ deviceId, styles }) {
  const [screenTime, setScreenTime] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchScreenTime = async () => {
    if (!deviceId) return;
    setLoading(true);
    try {
      const res = await api.getTodayScreenTime(deviceId);
      if (res && res.data) {
        setScreenTime(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch today's screen time:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScreenTime();
    const interval = setInterval(fetchScreenTime, 30000);
    return () => clearInterval(interval);
  }, [deviceId]);

  if (!screenTime) {
    return null;
  }

  const {
    formatted_total_time,
    total_screen_minutes,
    top_apps_today = [],
    top_sites_today = [],
    hourly_breakdown = [],
  } = screenTime;

  const maxHourMinutes = Math.max(...hourly_breakdown.map((h) => h.minutes || 0), 1);

  return (
    <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-zinc-800/50 text-zinc-300 border border-zinc-700">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
              Thời Lượng Sử Dụng Trong Ngày (Screen Time Today)
            </h4>
            <p className={`text-[10px] ${styles.textMuted}`}>
              Thống kê thời gian hoạt động thực tế của máy tính hôm nay
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchScreenTime}
            disabled={loading}
            className={`p-1.5 rounded-lg text-xs transition hover:bg-zinc-800 ${styles.textMuted}`}
            title="Làm mới thời lượng hôm nay"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Hero Stat: Total Screen Time Today */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-lg border bg-zinc-900/50 border-zinc-800 flex flex-col justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            Tổng Giờ Dùng Hôm Nay
          </span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-black text-emerald-300">
              {formatted_total_time || "0m"}
            </span>
            <span className="text-xs text-emerald-400/70">
              ({total_screen_minutes} phút)
            </span>
          </div>
          <span className="text-[10px] text-zinc-400 mt-1">
            {total_screen_minutes > 180 ? "⚠️ Đã dùng trên 3 tiếng" : "🟢 Thời lượng trong mức an toàn"}
          </span>
        </div>

        <div className={`p-3.5 rounded-lg border flex flex-col justify-between ${styles.card}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>
            Ứng Dụng Dùng Nhiều Nhất
          </span>
          <div className="flex items-center gap-2 mt-1">
            <Laptop className="w-4 h-4 text-blue-400 shrink-0" />
            <span className={`text-sm font-bold truncate ${styles.textBold}`}>
              {top_apps_today[0] ? top_apps_today[0].name : "Chưa có dữ liệu"}
            </span>
          </div>
          <span className="text-[11px] font-semibold text-blue-400 mt-1">
            {top_apps_today[0] ? `${top_apps_today[0].formatted} (${top_apps_today[0].percentage}%)` : "0m"}
          </span>
        </div>

        <div className={`p-3.5 rounded-lg border flex flex-col justify-between ${styles.card}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>
            Trang Web Xem Nhiều Nhất
          </span>
          <div className="flex items-center gap-2 mt-1">
            <Globe className="w-4 h-4 text-amber-400 shrink-0" />
            <span className={`text-sm font-bold truncate ${styles.textBold}`}>
              {top_sites_today[0] ? top_sites_today[0].domain : "Chưa có dữ liệu"}
            </span>
          </div>
          <span className="text-[11px] font-semibold text-amber-400 mt-1">
            {top_sites_today[0] ? `${top_sites_today[0].formatted} (${top_sites_today[0].percentage}%)` : "0m"}
          </span>
        </div>
      </div>

      {/* Breakdown: Apps & Websites */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        {/* Top Applications Today */}
        <div className={`p-3.5 rounded-lg border space-y-2.5 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold text-blue-400">
              <Laptop className="w-3.5 h-3.5" />
              <span>Top Ứng Dụng Hôm Nay</span>
            </div>
            <span className={`text-[10px] ${styles.textMuted}`}>{top_apps_today.length} ứng dụng</span>
          </div>

          {top_apps_today.length === 0 ? (
            <p className={`text-xs italic py-2 text-center ${styles.textMuted}`}>Chưa có dữ liệu ứng dụng hôm nay</p>
          ) : (
            <div className="space-y-2 pt-1">
              {top_apps_today.slice(0, 5).map((app, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className={`font-semibold truncate max-w-[180px] ${styles.textBold}`} title={app.name}>
                      {app.name}
                    </span>
                    <span className="font-mono text-[11px] text-blue-400 font-bold">
                      {app.formatted}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${app.percentage || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Websites Today */}
        <div className={`p-3.5 rounded-lg border space-y-2.5 ${styles.card}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400">
              <Globe className="w-3.5 h-3.5" />
              <span>Top Trang Web Hôm Nay</span>
            </div>
            <span className={`text-[10px] ${styles.textMuted}`}>{top_sites_today.length} trang web</span>
          </div>

          {top_sites_today.length === 0 ? (
            <p className={`text-xs italic py-2 text-center ${styles.textMuted}`}>Chưa có lịch sử duyệt web hôm nay</p>
          ) : (
            <div className="space-y-2 pt-1">
              {top_sites_today.slice(0, 5).map((site, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className={`font-semibold truncate max-w-[180px] ${styles.textBold}`} title={site.domain}>
                      {site.domain}
                    </span>
                    <span className="font-mono text-[11px] text-amber-400 font-bold">
                      {site.formatted}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-500 rounded-full transition-all duration-500"
                      style={{ width: `${site.percentage || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Hourly Activity Bar (24 Hours Timeline) */}
      <div className="space-y-2 pt-2 border-t border-zinc-800/60">
        <div className="flex items-center justify-between">
          <span className={`text-[11px] font-bold ${styles.textBold}`}>
            Phân Bố Hoạt Động Theo Từng Giờ Trong Ngày (0h - 23h)
          </span>
          <span className={`text-[10px] ${styles.textMuted}`}>Mỗi cột đại diện cho 1 giờ</span>
        </div>

        <div className="grid grid-cols-12 sm:grid-cols-24 gap-1 pt-2 items-end h-16">
          {hourly_breakdown.map((item, idx) => {
            const heightPct = Math.max(8, Math.round((item.minutes / maxHourMinutes) * 100));
            const hasActivity = item.minutes > 0;
            return (
              <div key={idx} className="flex flex-col items-center gap-1 group relative h-full justify-end">
                <div
                  className={`w-full rounded-t transition-all duration-300 ${
                    hasActivity ? "bg-emerald-500 hover:bg-emerald-400" : "bg-zinc-800/50"
                  }`}
                  style={{ height: `${hasActivity ? heightPct : 8}%` }}
                  title={`${item.hour}: ${item.minutes} phút`}
                />
                <span className="text-[8px] text-zinc-500 font-mono hidden sm:inline">
                  {idx % 3 === 0 ? item.hour.split(":")[0] : ""}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
