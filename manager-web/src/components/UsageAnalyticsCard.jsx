import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { BarChart3, TrendingUp, TrendingDown, Clock, Laptop, Globe, RefreshCw } from "lucide-react";

// Format a duration in seconds to "Xh Ym" / "Ym" / "Xs" (usage time).
function fmtDur(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rem = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  if (m > 0) return `${m}m ${String(rem).padStart(2, "0")}s`;
  return `${s}s`;
}

export default function UsageAnalyticsCard({ deviceId, styles }) {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchAnalytics = async () => {
    if (!deviceId) return;
    setLoading(true);
    try {
      const res = await api.getDeviceAnalytics(deviceId);
      if (res && res.data) {
        setAnalytics(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch usage analytics:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [deviceId]);

  if (!analytics) {
    return null;
  }

  const isTrendUp = analytics.trend_percentage > 0;
  const maxDaily = Math.max(...(analytics.daily_trend?.map((d) => d.count) || [1]), 1);
  const maxApp = Math.max(...(analytics.top_apps?.map((a) => a.count) || [1]), 1);

  return (
    <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Phân Tích Xu Hướng Sử Dụng (7 Ngày Qua)
          </h4>
        </div>
        <button
          onClick={fetchAnalytics}
          disabled={loading}
          className={`p-1.5 rounded-lg text-xs transition hover:bg-zinc-800 ${styles.textMuted}`}
          title="Làm mới thống kê"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Overview Stat Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className={`p-3 rounded-lg border flex flex-col gap-1 ${styles.card}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>Tổng Thời Lượng Tuần</span>
          <div className="flex items-baseline gap-2">
            <span className={`text-xl font-extrabold ${styles.textBold}`}>{fmtDur(analytics.total_seconds_week)}</span>
            <span className="text-[10px] opacity-70">sử dụng</span>
          </div>
        </div>

        <div className={`p-3 rounded-lg border flex flex-col gap-1 ${styles.card}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>So Với Tuần Trước</span>
          <div className="flex items-center gap-1.5">
            {isTrendUp ? (
              <>
                <TrendingUp className="w-4 h-4 text-primary" />
                <span className="text-sm font-bold text-primary">+{analytics.trend_percentage}%</span>
                <span className="text-[10px] text-primary/70">(Dùng nhiều hơn)</span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-primary" />
                <span className="text-sm font-bold text-primary">{analytics.trend_percentage}%</span>
                <span className="text-[10px] text-primary/70">(Giảm thời gian)</span>
              </>
            )}
          </div>
        </div>

        <div className={`p-3 rounded-lg border flex flex-col gap-1 ${styles.card}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>Trạng Thái Sử Dụng</span>
          <span className="text-xs font-bold text-primary">
            {analytics.total_seconds_week > 30 * 3600 ? "⚠️ Cần chú ý thời lượng" : "🟢 Mức độ sử dụng điều độ"}
          </span>
        </div>
      </div>

      {/* 7-Day Activity Chart Bar */}
      <div className="space-y-2 pt-2 border-t border-zinc-800/60">
        <span className={`text-xs font-bold ${styles.textBold}`}>Phân bố thời lượng theo ngày (Thứ 2 - CN)</span>
        <div className="grid grid-cols-7 gap-1.5 pt-2">
          {analytics.daily_trend?.map((item, idx) => {
            const heightPct = Math.max(8, Math.round((item.count / maxDaily) * 100));
            return (
              <div key={idx} className="flex flex-col items-center gap-1.5">
                <span className="text-[10px] font-mono opacity-70">{fmtDur(item.count)}</span>
                <div className="w-full h-16 bg-zinc-800/80 rounded-md flex items-end p-1 overflow-hidden">
                  <div
                    className="w-full bg-gradient-to-t from-primary to-primary rounded transition-all duration-500"
                    style={{ height: `${heightPct}%` }}
                  />
                </div>
                <span className="text-[10px] font-bold truncate max-w-full">{item.day}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 5 Apps & Top 5 Domains Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-zinc-800/60">
        {/* Top Apps */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
            <Laptop className="w-3.5 h-3.5" />
            <span>Top 5 Ứng Dụng Dùng Nhiều Thời Gian Nhất</span>
          </div>
          <div className="space-y-1.5">
            {analytics.top_apps?.length === 0 ? (
              <p className="text-xs italic opacity-60">Chưa có dữ liệu ứng dụng.</p>
            ) : (
              analytics.top_apps?.map((app, idx) => (
                <div key={idx} className="space-y-0.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="truncate max-w-[160px]">{app.name}</span>
                    <span className="text-[10px] opacity-70">{fmtDur(app.count)}</span>
                  </div>
                  <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${(app.count / maxApp) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Domains */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
            <Globe className="w-3.5 h-3.5" />
            <span>Top 5 Trang Web Truy Cập Nhiều Nhất</span>
          </div>
          <div className="space-y-1.5">
            {analytics.top_sites?.length === 0 ? (
              <p className="text-xs italic opacity-60">Chưa có dữ liệu duyệt web.</p>
            ) : (
              analytics.top_sites?.map((site, idx) => (
                <div key={idx} className="p-1.5 rounded bg-zinc-900/60 border border-zinc-900/60 flex items-center justify-between text-xs">
                  <span className="font-mono text-primary truncate max-w-[170px]">{site.domain}</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    {site.count} lượt
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
