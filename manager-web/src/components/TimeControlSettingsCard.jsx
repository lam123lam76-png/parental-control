import { useState, useEffect } from "react";
import {
  Clock,
  Globe,
  AppWindow,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Lock,
  Unlock,
  Timer,
} from "lucide-react";
import { api } from "../lib/api";


const themeStyles = {
  dark: {
    card: "bg-[#0D1F17] border-[#064E3B]/50 text-[#F8E7C9]",
    input: "bg-[#0a1a12] border-[#064E3B]/60 text-[#F8E7C9] focus:border-[#064E3B]",
    textBold: "text-[#F8E7C9]",
    textMuted: "text-[#7A9E7E]",
    buttonPrimary: "bg-[#064E3B] text-[#F8E7C9] hover:bg-[#065f47]",
    buttonSecondary: "bg-transparent border-[#064E3B]/50 text-[#7A9E7E] hover:border-[#064E3B] hover:text-[#F8E7C9]",
    badgeGreen: "bg-[#064E3B]/30 text-emerald-300 border border-[#064E3B]/50",
    badgeRed: "bg-rose-900/20 text-rose-300 border border-rose-800/40",
    badgeYellow: "bg-amber-900/20 text-amber-300 border border-amber-800/40",
    tabActive: "bg-[#064E3B]/40 border-[#064E3B] text-[#F8E7C9]",
    tabInactive: "border-transparent text-[#7A9E7E] hover:text-[#F8E7C9]",
  },
  light: {
    card: "bg-white border-gray-200 text-gray-900",
    input: "bg-gray-50 border-gray-300 text-gray-900 focus:border-emerald-600",
    textBold: "text-gray-900",
    textMuted: "text-gray-500",
    buttonPrimary: "bg-emerald-700 text-white hover:bg-emerald-800",
    buttonSecondary: "bg-transparent border-gray-300 text-gray-600 hover:border-emerald-600 hover:text-gray-900",
    badgeGreen: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    badgeRed: "bg-rose-100 text-rose-700 border border-rose-200",
    badgeYellow: "bg-amber-100 text-amber-700 border border-amber-200",
    tabActive: "bg-emerald-100 border-emerald-500 text-emerald-800",
    tabInactive: "border-transparent text-gray-500 hover:text-gray-800",
  },
};

const DAYS_VI = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

function SectionMessage({ message }) {
  if (!message) return null;
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-bold ${
        message.type === "success"
          ? "bg-emerald-900/30 border-emerald-700/50 text-emerald-300"
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
  );
}

// ─── Sub-section 1: Allowed Hours ────────────────────────────────────────────
function AllowedHoursSection({ styles, deviceId }) {
  const [schedules, setSchedules] = useState([]);
  const [originalSchedulesStr, setOriginalSchedulesStr] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const json = await api.getAllowedHours(deviceId);
        const serverSchedules = json.data?.schedules || [];
        setOriginalSchedulesStr(JSON.stringify(serverSchedules));
        
        const draft = localStorage.getItem(`pc_draft_hours_${deviceId}`);
        if (draft) {
          setSchedules(JSON.parse(draft));
          setMessage({ type: "error", text: "Đang hiển thị bản nháp chưa lưu (lần trước bị gián đoạn)." });
        } else {
          setSchedules(serverSchedules);
        }
      } catch {}
    };
    if (deviceId !== undefined) load();
  }, [deviceId]);

  useEffect(() => {
    if (schedules.length > 0 && deviceId !== undefined) {
      localStorage.setItem(`pc_draft_hours_${deviceId}`, JSON.stringify(schedules));
    }
  }, [schedules, deviceId]);

  const toggleDay = (idx, day) => {
    setSchedules((prev) =>
      prev.map((s, i) =>
        i === idx
          ? { ...s, days: s.days.includes(day) ? s.days.filter((d) => d !== day) : [...s.days, day].sort() }
          : s
      )
    );
  };

  const updateField = (idx, field, value) => {
    setSchedules((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)));
  };

  const addSchedule = () => {
    setSchedules((prev) => [...prev, { days: [], start: "08:00", end: "20:00" }]);
  };

  const removeSchedule = (idx) => {
    setSchedules((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const currentJson = await api.getAllowedHours(deviceId);
      const currentSchedulesStr = JSON.stringify(currentJson.data?.schedules || []);
      if (originalSchedulesStr && currentSchedulesStr !== originalSchedulesStr) {
        if (!window.confirm("CẢNH BÁO: Quản trị viên khác vừa thay đổi Khung Giờ! Bạn có chắc chắn muốn ghi đè?")) {
          setSaving(false);
          return;
        }
      }

      await api.updateAllowedHours(deviceId || null, schedules);
      setOriginalSchedulesStr(JSON.stringify(schedules));
      localStorage.removeItem(`pc_draft_hours_${deviceId}`);
      setMessage({ type: "success", text: "Đã lưu khung giờ cho phép!" });
    } catch (e) {
      setMessage({ type: "error", text: e.message || "Lưu thất bại." });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 4000);
    }
  };

  return (
    <div className={`p-4 rounded-xl border space-y-3 ${styles.card}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-emerald-900/30 text-emerald-300">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h4 className={`text-sm font-bold ${styles.textBold}`}>Khung Giờ Được Dùng Máy</h4>
            <p className={`text-[11px] ${styles.textMuted}`}>
              Ngoài khung giờ này, máy tính sẽ bị khóa tự động.
            </p>
          </div>
        </div>
        <button
          onClick={addSchedule}
          className={`p-1.5 rounded-lg border text-xs font-bold flex items-center gap-1 transition ${styles.buttonSecondary}`}
        >
          <Plus className="w-3.5 h-3.5" />
          Thêm
        </button>
      </div>

      <div className="space-y-3">
        {schedules.map((s, idx) => (
          <div key={idx} className={`p-3 rounded-lg border space-y-2.5 ${styles.card}`}>
            {/* Day Selector */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {DAYS_VI.map((d, di) => (
                <button
                  key={di}
                  onClick={() => toggleDay(idx, di)}
                  className={`w-9 h-8 rounded-lg text-xs font-bold border transition ${
                    s.days.includes(di)
                      ? "bg-emerald-800/60 border-emerald-500 text-emerald-200"
                      : `${styles.buttonSecondary} border`
                  }`}
                >
                  {d}
                </button>
              ))}
              <button
                onClick={() => removeSchedule(idx)}
                className="ml-auto p-1.5 rounded-lg border border-rose-800/40 text-rose-400 hover:bg-rose-900/20 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Time Range */}
            <div className="flex items-center gap-2">
              <label className={`text-[11px] font-medium ${styles.textMuted} w-10`}>Từ:</label>
              <input
                type="time"
                value={s.start}
                onChange={(e) => updateField(idx, "start", e.target.value)}
                className={`px-2 py-1 rounded-md border text-xs font-mono font-bold focus:outline-none ${styles.input}`}
              />
              <label className={`text-[11px] font-medium ${styles.textMuted} w-10`}>Đến:</label>
              <input
                type="time"
                value={s.end}
                onChange={(e) => updateField(idx, "end", e.target.value)}
                className={`px-2 py-1 rounded-md border text-xs font-mono font-bold focus:outline-none ${styles.input}`}
              />
            </div>
          </div>
        ))}
      </div>

      <SectionMessage message={message} />

      <button
        onClick={handleSave}
        disabled={saving}
        className={`w-full py-2 rounded-lg text-xs font-extrabold flex items-center justify-center gap-2 transition ${styles.buttonPrimary} disabled:opacity-60`}
      >
        {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
        {saving ? "Đang lưu..." : "Lưu Khung Giờ"}
      </button>
    </div>
  );
}

// ─── Sub-section 2: App / Web Restrictions ───────────────────────────────────
function AppWebRestrictionsSection({ styles, deviceId }) {
  const [rules, setRules] = useState([]);
  const [originalRulesStr, setOriginalRulesStr] = useState(null);
  const [newTarget, setNewTarget] = useState("");
  const [newType, setNewType] = useState("web"); // 'web' | 'app'
  const [newMode, setNewMode] = useState("ban"); // 'ban' | 'allow' | 'limit'
  const [newLimit, setNewLimit] = useState(60);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const json = await api.getRestrictions(deviceId);
        const serverRules = json.data?.rules || json.rules || [];
        setOriginalRulesStr(JSON.stringify(serverRules));

        const draft = localStorage.getItem(`pc_draft_rules_${deviceId}`);
        if (draft) {
          setRules(JSON.parse(draft));
          setMessage({ type: "error", text: "Đang hiển thị bản nháp chưa lưu (lần trước bị gián đoạn)." });
        } else {
          setRules(serverRules);
        }
      } catch {}
    };
    if (deviceId !== undefined) load();
  }, [deviceId]);

  useEffect(() => {
    if (rules.length > 0 && deviceId !== undefined) {
      localStorage.setItem(`pc_draft_rules_${deviceId}`, JSON.stringify(rules));
    }
  }, [rules, deviceId]);

  const addRule = () => {
    if (!newTarget.trim()) return;
    const rule = {
      id: Date.now(),
      type: newType,
      target: newTarget.trim(),
      mode: newMode,
      daily_limit_minutes: newMode === "limit" ? newLimit : null,
    };
    setRules((prev) => [rule, ...prev]);
    setNewTarget("");
  };

  const removeRule = (id) => setRules((prev) => prev.filter((r) => r.id !== id));

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const currentJson = await api.getRestrictions(deviceId);
      const currentRulesStr = JSON.stringify(currentJson.data?.rules || currentJson.rules || []);
      if (originalRulesStr && currentRulesStr !== originalRulesStr) {
        if (!window.confirm("CẢNH BÁO: Danh sách giới hạn đã bị thay đổi bởi Quản trị viên khác! Bạn có muốn ghi đè?")) {
          setSaving(false);
          return;
        }
      }

      await api.updateRestrictions(deviceId || null, rules);
      setOriginalRulesStr(JSON.stringify(rules));
      localStorage.removeItem(`pc_draft_rules_${deviceId}`);
      setMessage({ type: "success", text: "Đã lưu danh sách giới hạn!" });
    } catch (e) {
      setMessage({ type: "error", text: e.message || "Lưu thất bại." });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 4000);
    }
  };

  const modeBadge = (mode) => {
    if (mode === "ban") return { cls: styles.badgeRed, icon: <Lock className="w-3 h-3" />, label: "Chặn" };
    if (mode === "allow") return { cls: styles.badgeGreen, icon: <Unlock className="w-3 h-3" />, label: "Cho phép" };
    return { cls: styles.badgeYellow, icon: <Timer className="w-3 h-3" />, label: "Giới hạn thời gian" };
  };

  return (
    <div className={`p-4 rounded-xl border space-y-4 ${styles.card}`}>
      <div className="flex items-center gap-2.5">
        <div className="p-1.5 rounded-md bg-rose-900/30 text-rose-300">
          <Lock className="w-4 h-4" />
        </div>
        <div>
          <h4 className={`text-sm font-bold ${styles.textBold}`}>Web & Ứng Dụng Bị Giới Hạn</h4>
          <p className={`text-[11px] ${styles.textMuted}`}>
            Chặn, cho phép, hoặc đặt giới hạn thời gian dùng mỗi ngày.
          </p>
        </div>
      </div>

      {/* Add Rule Form */}
      <div className={`p-3 rounded-xl border space-y-3 ${styles.card}`}>
        <p className={`text-[11px] font-bold uppercase tracking-wider ${styles.textMuted}`}>Thêm quy tắc mới</p>

        {/* Type Toggle */}
        <div className="flex gap-2">
          {[
            { val: "web", icon: Globe, label: "Website" },
            { val: "app", icon: AppWindow, label: "Ứng dụng" },
          ].map(({ val, icon: Icon, label }) => (
            <button
              key={val}
              onClick={() => setNewType(val)}
              className={`flex-1 py-1.5 rounded-lg border text-xs font-bold flex items-center justify-center gap-1.5 transition ${
                newType === val
                  ? val === "web"
                    ? "bg-blue-900/40 border-blue-500 text-blue-200"
                    : "bg-purple-900/40 border-purple-500 text-purple-200"
                  : `${styles.buttonSecondary} border`
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Target Input */}
        <input
          value={newTarget}
          onChange={(e) => setNewTarget(e.target.value)}
          placeholder={newType === "web" ? "youtube.com, facebook.com..." : "chrome.exe, game.exe..."}
          className={`w-full px-3 py-2 rounded-lg border text-xs font-mono focus:outline-none ${styles.input}`}
          onKeyDown={(e) => e.key === "Enter" && addRule()}
        />

        {/* Mode Selector */}
        <div className="flex gap-2">
          {[
            { val: "ban", label: "Chặn hoàn toàn", cls: "bg-rose-900/40 border-rose-500 text-rose-200" },
            { val: "allow", label: "Chỉ cho phép", cls: "bg-emerald-900/40 border-emerald-500 text-emerald-200" },
            { val: "limit", label: "Giới hạn thời gian", cls: "bg-amber-900/40 border-amber-500 text-amber-200" },
          ].map(({ val, label, cls }) => (
            <button
              key={val}
              onClick={() => setNewMode(val)}
              className={`flex-1 py-1.5 rounded-lg border text-[10px] font-bold transition ${
                newMode === val ? cls : `${styles.buttonSecondary} border`
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Daily limit (only when 'limit' mode) */}
        {newMode === "limit" && (
          <div className="flex items-center gap-2">
            <span className={`text-[11px] ${styles.textMuted}`}>Giới hạn:</span>
            <input
              type="number"
              min={1}
              max={480}
              value={newLimit}
              onChange={(e) => setNewLimit(Number(e.target.value))}
              className={`w-20 px-2 py-1 rounded-md border text-xs font-mono font-bold focus:outline-none ${styles.input}`}
            />
            <span className={`text-[11px] ${styles.textMuted}`}>phút/ngày</span>
          </div>
        )}

        <button
          onClick={addRule}
          disabled={!newTarget.trim()}
          className={`w-full py-2 rounded-lg text-xs font-extrabold flex items-center justify-center gap-1.5 transition ${styles.buttonPrimary} disabled:opacity-40`}
        >
          <Plus className="w-3.5 h-3.5" />
          Thêm Quy Tắc
        </button>
      </div>

      {/* Rule List */}
      <div className="space-y-2">
        {rules.length === 0 ? (
          <div className={`text-center py-6 text-xs ${styles.textMuted}`}>
            Chưa có quy tắc nào. Thêm quy tắc ở trên.
          </div>
        ) : (
          rules.map((r) => {
            const { cls, icon, label } = modeBadge(r.mode);
            return (
              <div
                key={r.id}
                className={`flex items-center justify-between p-2.5 rounded-lg border ${styles.card}`}
              >
                <div className="flex items-center gap-2">
                  <div className={`p-1 rounded-md ${r.type === "web" ? "bg-blue-900/30 text-blue-300" : "bg-purple-900/30 text-purple-300"}`}>
                    {r.type === "web" ? <Globe className="w-3.5 h-3.5" /> : <AppWindow className="w-3.5 h-3.5" />}
                  </div>
                  <div>
                    <div className={`text-xs font-bold ${styles.textBold}`}>{r.target}</div>
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold ${cls}`}>
                        {icon}
                        {label}
                        {r.mode === "limit" && r.daily_limit_minutes && ` · ${r.daily_limit_minutes} phút/ngày`}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => removeRule(r.id)}
                  className="p-1.5 rounded-lg border border-rose-800/40 text-rose-400 hover:bg-rose-900/20 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      <SectionMessage message={message} />

      <button
        onClick={handleSave}
        disabled={saving}
        className={`w-full py-2.5 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 transition ${styles.buttonPrimary} disabled:opacity-60`}
      >
        {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        {saving ? "Đang lưu..." : "Lưu Danh Sách Giới Hạn"}
      </button>
    </div>
  );
}

// ─── Main Export ──────────────────────────────────────────────────────────────
export default function TimeControlSettingsCard({ theme = "dark", deviceId }) {
  const styles = themeStyles[theme] || themeStyles.dark;
  const [activeTab, setActiveTab] = useState("hours"); // 'hours' | 'restrictions'

  const tabs = [
    { id: "hours", label: "Khung Giờ Dùng Máy", icon: Clock },
    { id: "restrictions", label: "Giới Hạn Web & App", icon: Lock },
  ];

  return (
    <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-lg bg-amber-900/30 border border-amber-700/40 text-amber-300">
          <Clock className="w-5 h-5 stroke-[1.75]" />
        </div>
        <div>
          <h2 className={`text-base font-extrabold ${styles.textBold}`}>Kiểm Soát Thời Gian</h2>
          <p className={`text-xs font-medium ${styles.textMuted}`}>
            Giới hạn giờ dùng máy và kiểm soát truy cập web / ứng dụng.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#064E3B]/30">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-bold border-b-2 transition ${
              activeTab === id ? styles.tabActive : styles.tabInactive
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "hours" && <AllowedHoursSection styles={styles} deviceId={deviceId} />}
      {activeTab === "restrictions" && <AppWebRestrictionsSection styles={styles} deviceId={deviceId} />}
    </div>
  );
}
