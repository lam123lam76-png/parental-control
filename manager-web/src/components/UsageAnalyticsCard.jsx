import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { fmtDur } from "../lib/utils";
import { BarChart3, TrendingUp, TrendingDown, Laptop, Globe, RefreshCw, AlertTriangle } from "lucide-react";

const HAIRLINE = "shadow-[0_-1px_0_rgba(14,55,70,0.10)] dark:shadow-[0_-1px_0_rgba(255,255,255,0.08)]";

export default function UsageAnalyticsCard({ deviceId, styles }) {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  const fetchAnalytics = async () => {
    if (!deviceId) return;
    setLoading(true);
    setLoadError("");
    try {
      const res = await api.getDeviceAnalytics(deviceId);
      if (res && res.data) {
        setAnalytics(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch usage analytics:", e);
      setAnalytics(null);
      setLoadError("Không tải được số liệu sử dụng.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [deviceId]);

  if (!analytics) {
    // Show the failure instead of rendering nothing (silent blank card).
    return loadError ? (
      <div className={`p-4 sm:p-5 rounded-xl space-y-2 ${styles.card}`}>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Phân tích xu hướng sử dụng (7 ngày qua)
          </h4>
        </div>
        <div className={`p-3 rounded-lg text-xs font-bold flex items-center gap-2.5 ${styles.inset}`}>
          <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
          <span className={`flex-1 ${styles.text}`}>{loadError}</span>
          <button
            type="button"
            onClick={fetchAnalytics}
            disabled={loading}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition shrink-0 ${styles.buttonSecondary}`}
          >
            Thử lại
          </button>
        </div>
      </div>
    ) : null;
  }

  const isTrendUp = analytics.trend_percentage > 0;
  const maxDaily = Math.max(...(analytics.daily_trend?.map((d) => d.count) || [0]), 1);
  const hasDailyData = (analytics.daily_trend || []).some((d) => (d.count || 0) > 0);
  const maxApp = Math.max(...(analytics.top_apps?.map((a) => a.count) || [0]), 1);
  const isHeavyUse = (analytics.total_seconds_week || 0) > 30 * 3600;

  return (
    <div className={`p-4 sm:p-5 rounded-xl space-y-4 ${styles.card}`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <BarChart3 className="w-4 h-4 text-primary shrink-0" />
          <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Phân tích xu hướng sử dụng (7 ngày qua)
          </h4>
        </div>
        <button
          onClick={fetchAnalytics}
          disabled={loading}
          className={`p-1.5 rounded-lg text-xs transition shrink-0 ${styles.buttonSecondary}`}
          title="Làm mới thống kê"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Overview Stat Metrics — inset tiles so they read as a level below the card */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className={`p-3 rounded-lg flex flex-col gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>Tổng thời lượng tuần</span>
          <div className="flex items-baseline gap-2">
            <span className={`text-xl font-extrabold ${styles.metricValue}`}>{fmtDur(analytics.total_seconds_week)}</span>
            <span className={`text-[10px] ${styles.textMuted}`}>sử dụng</span>
          </div>
        </div>

        <div className={`p-3 rounded-lg flex flex-col gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>So với tuần trước</span>
          <div className="flex items-center gap-1.5">
            {isTrendUp ? (
              <>
                <TrendingUp className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                <span className="text-sm font-bold text-amber-700 dark:text-amber-300">+{analytics.trend_percentage}%</span>
                <span className={`text-[10px] ${styles.textMuted}`}>(nhiều hơn)</span>
              </>
            ) : (
              <>
                <TrendingDown className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span className="text-sm font-bold text-emerald-700 dark:text-emerald-300">{analytics.trend_percentage}%</span>
                <span className={`text-[10px] ${styles.textMuted}`}>(ít hơn)</span>
              </>
            )}
          </div>
        </div>

        <div className={`p-3 rounded-lg flex flex-col gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>Trạng thái sử dụng</span>
          <span
            className={`inline-flex w-fit items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded ${
              isHeavyUse
                ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isHeavyUse ? "bg-amber-500" : "bg-emerald-500"}`} />
            {isHeavyUse ? "Cần chú ý thời lượng" : "Mức sử dụng điều độ"}
          </span>
        </div>
      </div>

      {/* 7-Day Activity Chart Bar */}
      <div className={`space-y-2 pt-3 ${HAIRLINE}`}>
        <span className={`text-xs font-bold ${styles.textBold}`}>Phân bố thời lượng theo ngày (Thứ 2 – Chủ Nhật)</span>
        {!hasDailyData ? (
          <p className={`text-xs italic py-6 text-center ${styles.textMuted}`}>
            Chưa có dữ liệu sử dụng trong 7 ngày qua.
          </p>
        ) : (
          <div className="grid grid-cols-7 gap-1.5 pt-2">
            {analytics.daily_trend?.map((item, idx) => {
              const hasValue = (item.count || 0) > 0;
              // A zero day must NOT draw a bar (it used to render a fake 8% bar).
              const heightPct = hasValue ? Math.max(6, Math.round((item.count / maxDaily) * 100)) : 0;
              return (
                <div key={idx} className="flex flex-col items-center gap-1.5">
                  <span className={`text-[10px] font-mono ${hasValue ? styles.text : styles.textMuted}`}>{fmtDur(item.count)}</span>
                  <div className={`w-full h-16 rounded-md flex items-end overflow-hidden ${styles.inset}`}>
                    {hasValue && (
                      <div
                        className="w-full bg-primary rounded-t transition-all duration-500"
                        style={{ height: `${heightPct}%` }}
                        title={`${item.day}: ${fmtDur(item.count)}`}
                      />
                    )}
                  </div>
                  <span className={`text-[10px] font-bold truncate max-w-full ${styles.text}`}>{item.day}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Top 5 Apps & Top 5 Domains Grid — short, single-line headings so both columns align */}
      <div className={`grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 ${HAIRLINE}`}>
        {/* Top Apps */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
            <Laptop className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Top 5 ứng dụng (7 ngày)</span>
          </div>
          <div className="space-y-1.5">
            {analytics.top_apps?.length === 0 ? (
              <p className={`text-xs italic ${styles.textMuted}`}>Chưa có dữ liệu ứng dụng trong 7 ngày qua.</p>
            ) : (
              analytics.top_apps?.map((app, idx) => (
                <div key={idx} className="space-y-0.5">
                  <div className="flex items-center justify-between gap-2 text-xs font-mono">
                    <span className={`truncate ${styles.text}`}>{app.name}</span>
                    <span className={`text-[10px] shrink-0 ${styles.textMuted}`}>{fmtDur(app.count)}</span>
                  </div>
                  <div className={`h-1 rounded-full overflow-hidden ${styles.inset}`}>
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
            <Globe className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Top 5 trang web (7 ngày)</span>
          </div>
          <div className="space-y-1.5">
            {analytics.top_sites?.length === 0 ? (
              <p className={`text-xs italic ${styles.textMuted}`}>Chưa có dữ liệu duyệt web trong 7 ngày qua.</p>
            ) : (
              analytics.top_sites?.map((site, idx) => (
                <div key={idx} className={`p-1.5 rounded flex items-center justify-between gap-2 text-xs ${styles.row}`}>
                  <span className="font-mono text-primary truncate">{site.domain}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${styles.badgeMuted}`}>
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
