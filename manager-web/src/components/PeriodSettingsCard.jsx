import { useState, useEffect } from "react";
import { Camera, Activity, Save, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "../lib/api";

const themeStyles = {
  dark: {
    card: "bg-zinc-900 border-zinc-800 text-[#F8E7C9]",
    input: "bg-zinc-950 border-zinc-800 text-[#F8E7C9] focus:border-[#064E3B]",
    textBold: "text-[#F8E7C9]",
    textMuted: "text-zinc-400",
    buttonPrimary: "bg-[#064E3B] text-[#F8E7C9] hover:bg-[#065f47]",
    buttonSecondary: "bg-transparent border-zinc-800 text-zinc-400 hover:border-[#064E3B] hover:text-[#F8E7C9]",
    badge: "bg-[#064E3B]/30 text-emerald-300 border border-zinc-800",
  },
  light: {
    card: "bg-white border-gray-200 text-gray-900",
    input: "bg-gray-50 border-gray-300 text-gray-900 focus:border-emerald-600",
    textBold: "text-gray-900",
    textMuted: "text-gray-500",
    buttonPrimary: "bg-emerald-700 text-white hover:bg-emerald-800",
    buttonSecondary: "bg-transparent border-gray-300 text-gray-600 hover:border-emerald-600 hover:text-gray-900",
    badge: "bg-emerald-100 text-emerald-700 border border-emerald-200",
  },
};

export default function PeriodSettingsCard({ theme = "dark", deviceId }) {
  const styles = themeStyles[theme] || themeStyles.dark;

  const [screenshotInterval, setScreenshotInterval] = useState(60);
  const [heartbeatInterval, setHeartbeatInterval] = useState(15);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success'|'error', text }

  // Load current settings from backend
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const json = await api.getPeriodSettings();
        const d = json.data || json;
        setScreenshotInterval(d.screenshot_interval_seconds ?? 60);
        setHeartbeatInterval(d.heartbeat_interval_seconds ?? 15);
      } catch {
        // Use defaults silently
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [deviceId]);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.updatePeriodSettings({
        screenshot_interval_seconds: Number(screenshotInterval),
        heartbeat_interval_seconds: Number(heartbeatInterval),
        device_id: deviceId || null,
      });
      setMessage({ type: "success", text: "Đã lưu cài đặt chu kỳ thành công!" });
    } catch (e) {
      setMessage({ type: "error", text: e.message || "Lưu thất bại, vui lòng thử lại." });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 4000);
    }
  };

  const intervalOptions = [
    { label: "5 giây", value: 5 },
    { label: "10 giây", value: 10 },
    { label: "15 giây", value: 15 },
    { label: "30 giây", value: 30 },
    { label: "1 phút", value: 60 },
    { label: "2 phút", value: 120 },
    { label: "5 phút", value: 300 },
    { label: "10 phút", value: 600 },
    { label: "15 phút", value: 900 },
    { label: "30 phút", value: 1800 },
  ];

  const heartbeatOptions = [
    { label: "5 giây", value: 5 },
    { label: "10 giây", value: 10 },
    { label: "15 giây", value: 15 },
    { label: "30 giây", value: 30 },
    { label: "1 phút", value: 60 },
  ];

  if (loading) {
    return (
      <div className={`p-5 rounded-xl border ${styles.card}`}>
        <div className="flex items-center gap-2 animate-pulse">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className={`text-xs ${styles.textMuted}`}>Đang tải cài đặt...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-4 sm:p-5 rounded-xl border space-y-5 ${styles.card}`}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-lg bg-purple-900/30 border border-purple-700/40 text-purple-300">
          <Activity className="w-5 h-5 stroke-[1.75]" />
        </div>
        <div>
          <h2 className={`text-base font-extrabold ${styles.textBold}`}>Cài Đặt Chu Kỳ</h2>
          <p className={`text-xs font-medium ${styles.textMuted}`}>
            Điều chỉnh tần suất chụp màn hình và kiểm tra kết nối.
          </p>
        </div>
      </div>

      {/* Screenshot Interval */}
      <div className={`p-4 rounded-xl border ${styles.card} space-y-3`}>
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-emerald-900/30 text-emerald-300">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <h4 className={`text-sm font-bold ${styles.textBold}`}>Chu Kỳ Chụp Ảnh Màn Hình</h4>
            <p className={`text-[11px] ${styles.textMuted}`}>
              Agent sẽ chụp màn hình theo chu kỳ này và gửi lên server.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {intervalOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setScreenshotInterval(opt.value)}
              className={`py-2 px-3 rounded-lg border text-xs font-bold transition ${
                screenshotInterval === opt.value
                  ? "bg-emerald-800/50 border-emerald-600 text-emerald-200"
                  : `${styles.buttonSecondary} border`
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 mt-1">
          <span className={`text-[11px] ${styles.textMuted}`}>Hoặc nhập thủ công (giây):</span>
          <input
            type="number"
            min={5}
            max={7200}
            value={screenshotInterval}
            onChange={(e) => setScreenshotInterval(Number(e.target.value))}
            className={`w-20 px-2 py-1 rounded-md border text-xs font-mono font-bold focus:outline-none ${styles.input}`}
          />
          <span className={`text-[11px] ${styles.textMuted}`}>giây</span>
        </div>

        <div className={`text-[11px] px-3 py-2 rounded-lg ${styles.badge}`}>
          ✔ Hiện tại: chụp mỗi{" "}
          <strong>
            {screenshotInterval < 60
              ? `${screenshotInterval} giây`
              : `${screenshotInterval / 60} phút`}
          </strong>
        </div>
      </div>

      {/* Heartbeat Interval */}
      <div className={`p-4 rounded-xl border ${styles.card} space-y-3`}>
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-blue-900/30 text-blue-300">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h4 className={`text-sm font-bold ${styles.textBold}`}>Chu Kỳ Heartbeat</h4>
            <p className={`text-[11px] ${styles.textMuted}`}>
              Agent gửi tín hiệu "còn sống" tới server theo chu kỳ này. Đặt ngắn để phát hiện mất kết nối nhanh hơn.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-2">
          {heartbeatOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setHeartbeatInterval(opt.value)}
              className={`py-2 px-1 rounded-lg border text-xs font-bold transition ${
                heartbeatInterval === opt.value
                  ? "bg-blue-800/50 border-blue-500 text-blue-200"
                  : `${styles.buttonSecondary} border`
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-[11px] ${styles.textMuted}`}>Hoặc nhập thủ công (giây):</span>
          <input
            type="number"
            min={5}
            max={300}
            value={heartbeatInterval}
            onChange={(e) => setHeartbeatInterval(Number(e.target.value))}
            className={`w-20 px-2 py-1 rounded-md border text-xs font-mono font-bold focus:outline-none ${styles.input}`}
          />
          <span className={`text-[11px] ${styles.textMuted}`}>giây</span>
        </div>

        <div className={`text-[11px] px-3 py-2 rounded-lg ${styles.badge}`}>
          ✔ Hiện tại: heartbeat mỗi <strong>{heartbeatInterval} giây</strong>
        </div>
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-bold ${
            message.type === "success"
              ? "bg-zinc-800/30 border-zinc-700/50 text-zinc-200 text-emerald-300"
              : "bg-rose-900/30 border-rose-700/50 text-rose-300"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          {message.text}
        </div>
      )}

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className={`w-full py-2.5 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 transition ${styles.buttonPrimary} disabled:opacity-60`}
      >
        {saving ? (
          <RefreshCw className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        {saving ? "Đang lưu..." : "Lưu Cài Đặt Chu Kỳ"}
      </button>
    </div>
  );
}
