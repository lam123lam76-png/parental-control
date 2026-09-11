import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { fmtDur } from "../lib/utils";
import { Clock, Laptop, Globe, RefreshCw, AlertTriangle } from "lucide-react";

const HAIRLINE = "shadow-[0_-1px_0_rgba(14,55,70,0.10)] dark:shadow-[0_-1px_0_rgba(255,255,255,0.08)]";

export default function ScreenTimeTodayCard({ deviceId, styles }) {
  const [screenTime, setScreenTime] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  const fetchScreenTime = async () => {
    if (!deviceId) return;
    setLoading(true);
    setLoadError("");
    try {
      const res = await api.getTodayScreenTime(deviceId);
      if (res && res.data) {
        setScreenTime(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch today's screen time:", e);
      setScreenTime(null);
      setLoadError("Không tải được thời lượng sử dụng hôm nay.");
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
    return loadError ? (
      <div className={`p-4 sm:p-5 rounded-xl space-y-2 ${styles.card}`}>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary" />
          <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Thời lượng sử dụng trong ngày
          </h4>
        </div>
        <div className={`p-3 rounded-lg text-xs font-bold flex items-center gap-2.5 ${styles.inset}`}>
          <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
          <span className={`flex-1 ${styles.text}`}>{loadError}</span>
          <button
            type="button"
            onClick={fetchScreenTime}
            disabled={loading}
            className={`px-3 py-1.5 rounded-md text-xs font-bold transition shrink-0 ${styles.buttonSecondary}`}
          >
            Thử lại
          </button>
        </div>
      </div>
    ) : null;
  }

  const {
    total_screen_minutes = 0,
    top_apps_today = [],
    top_sites_today = [],
    hourly_breakdown = [],
  } = screenTime;

  const totalSeconds = Math.round((Number(total_screen_minutes) || 0) * 60);
  const isHeavyUse = total_screen_minutes > 180;
  const maxHourMinutes = Math.max(...hourly_breakdown.map((h) => h.minutes || 0), 1);
  const hasHourlyData = hourly_breakdown.some((h) => (h.minutes || 0) > 0);

  return (
    <div className={`p-4 sm:p-5 rounded-xl space-y-4 ${styles.card}`}>
      {/* Header */}
      <div className={`flex items-center justify-between gap-3 pb-3 ${HAIRLINE}`}>
        <div className="flex items-center gap-2 min-w-0">
          <div className={`p-1.5 rounded-lg shrink-0 ${styles.inset} ${styles.text}`}>
            <Clock className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
              Thời lượng sử dụng trong ngày
            </h4>
            <p className={`text-[10px] ${styles.textMuted}`}>
              Thống kê thời gian hoạt động thực tế của máy tính hôm nay
            </p>
          </div>
        </div>
        <button
          onClick={fetchScreenTime}
          disabled={loading}
          className={`p-1.5 rounded-lg text-xs transition shrink-0 ${styles.buttonSecondary}`}
          title="Làm mới thời lượng hôm nay"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Hero Stat: Total Screen Time Today — same shape language as its two siblings */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className={`p-3.5 rounded-lg flex flex-col justify-between gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.metricLabel}`}>
            Tổng giờ dùng hôm nay
          </span>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-black ${styles.metricValue}`}>{fmtDur(totalSeconds)}</span>
            <span className={`text-xs ${styles.textMuted}`}>({total_screen_minutes} phút)</span>
          </div>
          <span
            className={`inline-flex w-fit items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded ${
              isHeavyUse
                ? "bg-amber-500/15 text-amber-700 dark:text-amber-300"
                : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isHeavyUse ? "bg-amber-500" : "bg-emerald-500"}`} />
            {isHeavyUse ? "Đã dùng trên 3 tiếng" : "Trong mức an toàn"}
          </span>
        </div>

        <div className={`p-3.5 rounded-lg flex flex-col justify-between gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>
            Ứng dụng dùng nhiều nhất
          </span>
          <div className="flex items-center gap-2">
            <Laptop className="w-4 h-4 text-primary shrink-0" />
            <span className={`text-sm font-bold truncate ${styles.textBold}`}>
              {top_apps_today[0] ? top_apps_today[0].name : "Chưa có dữ liệu"}
            </span>
          </div>
          <span className={`text-xs font-semibold ${styles.text}`}>
            {top_apps_today[0]
              ? `${top_apps_today[0].formatted} (${top_apps_today[0].percentage}%)`
              : "—"}
          </span>
        </div>

        <div className={`p-3.5 rounded-lg flex flex-col justify-between gap-1 ${styles.inset}`}>
          <span className={`text-[10px] font-bold uppercase ${styles.metricLabel}`}>
            Trang web xem nhiều nhất
          </span>
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary shrink-0" />
            <span className={`text-sm font-bold truncate ${styles.textBold}`}>
              {top_sites_today[0] ? top_sites_today[0].domain : "Chưa có dữ liệu"}
            </span>
          </div>
          <span className={`text-xs font-semibold ${styles.text}`}>
            {top_sites_today[0]
              ? `${top_sites_today[0].formatted} (${top_sites_today[0].percentage}%)`
              : "—"}
          </span>
        </div>
      </div>

      {/* Breakdown: Apps & Websites */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Applications Today */}
        <div className={`p-3.5 rounded-lg space-y-2.5 ${styles.inset}`}>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-primary min-w-0">
              <Laptop className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">Top ứng dụng hôm nay</span>
            </div>
            <span className={`text-[10px] shrink-0 ${styles.textMuted}`}>{top_apps_today.length} ứng dụng</span>
          </div>

          {top_apps_today.length === 0 ? (
            <p className={`text-xs italic py-2 text-center ${styles.textMuted}`}>Chưa có dữ liệu ứng dụng hôm nay.</p>
          ) : (
            <div className="space-y-2 pt-1">
              {top_apps_today.slice(0, 5).map((app, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className={`font-semibold truncate ${styles.text}`} title={app.name}>
                      {app.name}
                    </span>
                    <span className={`font-mono text-xs font-bold shrink-0 ${styles.text}`}>
                      {app.formatted}
                    </span>
                  </div>
                  <div className={`w-full h-1.5 rounded-full overflow-hidden ${styles.inset}`}>
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
                      style={{ width: `${app.percentage || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Websites Today */}
        <div className={`p-3.5 rounded-lg space-y-2.5 ${styles.inset}`}>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-primary min-w-0">
              <Globe className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">Top trang web hôm nay</span>
            </div>
            <span className={`text-[10px] shrink-0 ${styles.textMuted}`}>{top_sites_today.length} trang web</span>
          </div>

          {top_sites_today.length === 0 ? (
            <p className={`text-xs italic py-2 text-center ${styles.textMuted}`}>Chưa có dữ liệu duyệt web hôm nay.</p>
          ) : (
            <div className="space-y-2 pt-1">
              {top_sites_today.slice(0, 5).map((site, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className={`font-semibold truncate ${styles.text}`} title={site.domain}>
                      {site.domain}
                    </span>
                    <span className={`font-mono text-xs font-bold shrink-0 ${styles.text}`}>
                      {site.formatted}
                    </span>
                  </div>
                  <div className={`w-full h-1.5 rounded-full overflow-hidden ${styles.inset}`}>
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
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
      <div className={`space-y-2 pt-3 ${HAIRLINE}`}>
        <div className="flex items-center justify-between gap-3">
          <span className={`text-xs font-bold ${styles.textBold}`}>
            Phân bố hoạt động theo từng giờ trong ngày (0h – 23h)
          </span>
          <span className={`text-[10px] shrink-0 ${styles.textMuted}`}>Mỗi cột là 1 giờ</span>
        </div>

        {!hasHourlyData ? (
          // Previously this drew 24 dark grey stubs that looked like broken placeholders.
          <p className={`text-xs italic py-6 text-center ${styles.textMuted}`}>
            Hôm nay chưa ghi nhận hoạt động nào.
          </p>
        ) : (
          <div className="grid grid-cols-12 sm:grid-cols-24 gap-1 pt-2 items-end h-16">
            {hourly_breakdown.map((item, idx) => {
              const hasActivity = (item.minutes || 0) > 0;
              const heightPct = hasActivity ? Math.max(6, Math.round((item.minutes / maxHourMinutes) * 100)) : 0;
              return (
                <div key={idx} className="flex flex-col items-center gap-1 group relative h-full justify-end">
                  {hasActivity && (
                    <div
                      className="w-full rounded-t bg-primary transition-all duration-300"
                      style={{ height: `${heightPct}%` }}
                      title={`${item.hour}: ${item.minutes} phút`}
                    />
                  )}
                  <span className={`text-[8px] font-mono hidden sm:inline ${styles.textMuted}`}>
                    {idx % 3 === 0 ? item.hour.split(":")[0] : ""}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
