import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { Globe, Search, RefreshCw, AlertTriangle, ExternalLink, ShieldAlert, Clock, Filter } from "lucide-react";

// Sensitive keywords list for automatic flagging
const SENSITIVE_KEYWORDS = [
  "adult", "sex", "porn", "gambling", "casino", "bet", "cờ bạc", "cá cược",
  "18+", "hentai", "hack", "cheat", "bạo lực", "darkweb", "weapons", "drugs"
];

export default function BrowserHistoryView({ theme = "dark", deviceId = "" }) {
  const styles = getThemeStyles(theme);

  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedBrowser, setSelectedBrowser] = useState("all");
  const [message, setMessage] = useState("");

  const fetchHistory = async () => {
    if (!deviceId) return;
    setLoading(true);
    try {
      const res = await api.getBrowserHistory(deviceId, 150, search, selectedBrowser);
      if (res.data && Array.isArray(res.data.history)) {
        setHistory(res.data.history);
      }
    } catch (err) {
      setMessage(`Không thể tải lịch sử trình duyệt: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [deviceId, selectedBrowser]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchHistory();
  };

  const isSensitive = (title = "", url = "") => {
    const text = `${title} ${url}`.toLowerCase();
    return SENSITIVE_KEYWORDS.some((kw) => text.includes(kw));
  };

  const getBrowserBadgeColor = (name = "") => {
    const lower = name.toLowerCase();
    if (lower.includes("chrome")) return "bg-blue-900/30 border-blue-800/50 text-blue-300";
    if (lower.includes("edge")) return "bg-teal-900/30 border-teal-800/50 text-teal-300";
    if (lower.includes("brave")) return "bg-orange-900/30 border-orange-800/50 text-orange-300";
    if (lower.includes("cốc cốc") || lower.includes("coccoc")) return "bg-emerald-900/30 border-emerald-800/50 text-emerald-300";
    if (lower.includes("firefox")) return "bg-amber-900/30 border-amber-800/50 text-amber-300";
    return "bg-zinc-800 border-zinc-700 text-zinc-300";
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* HEADER CARD */}
      <div className={`p-4 sm:p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${styles.card}`}>
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800 border-l-2 border-l-[#064E3B] text-[#F8E7C9]">
            <Globe className="w-5 h-5 stroke-[1.75]" />
          </div>
          <div>
            <h2 className={`text-base font-extrabold ${styles.textBold}`}>
              Lịch Sử Truy Cập Trình Duyệt (Browser History Log Engine)
            </h2>
            <p className={`text-xs font-medium ${styles.textMuted}`}>
              Thu thập nhật ký mở trang web từ Chrome, Edge, Brave, Cốc Cốc, Firefox với tính năng cảnh báo từ khóa nhạy cảm.
            </p>
          </div>
        </div>

        <button
          onClick={fetchHistory}
          disabled={loading}
          className={`p-2 px-3 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Cập Nhật</span>
        </button>
      </div>

      {/* SEARCH BAR & BROWSER FILTERS */}
      <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-zinc-500" />
            <input
              type="text"
              placeholder="Tìm kiếm theo tiêu đề trang hoặc địa chỉ URL..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={`w-full pl-9 pr-3 py-2.5 text-xs font-bold rounded-lg border focus:outline-none ${styles.input}`}
            />
          </div>
          <button
            type="submit"
            className={`py-2.5 px-4 text-xs font-bold rounded-lg transition ${styles.buttonPrimary}`}
          >
            Tìm Kiếm
          </button>
        </form>

        {/* Browser Filter Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`text-[11px] font-bold uppercase tracking-wider flex items-center gap-1 mr-1 ${styles.textMuted}`}>
            <Filter className="w-3 h-3" /> Lọc Trình Duyệt:
          </span>
          {["all", "Chrome", "Edge", "Brave", "Cốc Cốc", "Firefox"].map((b) => (
            <button
              key={b}
              onClick={() => setSelectedBrowser(b)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-bold transition ${
                selectedBrowser === b
                  ? "bg-[#064E3B] border-[#F8E7C9] text-[#F8E7C9]"
                  : styles.card + " opacity-70 hover:opacity-100"
              }`}
            >
              {b === "all" ? "Tất Cả Trình Duyệt" : b}
            </button>
          ))}
        </div>
      </div>

      {/* HISTORY TIMELINE TABLE */}
      <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
        <div className="flex items-center justify-between">
          <h3 className={`text-sm font-bold flex items-center gap-2 ${styles.textBold}`}>
            <Clock className="w-4 h-4 text-emerald-400" />
            <span>Nhật Ký Trang Web Đã Mở ({history.length} mục)</span>
          </h3>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-10 space-y-2">
            <Globe className="w-8 h-8 text-zinc-600 mx-auto" />
            <p className={`text-xs italic ${styles.textMuted}`}>
              Chưa ghi nhận lịch sử trình duyệt nào. Mở web trên máy con để theo dõi.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5 font-mono text-xs">
            {history.map((item) => {
              const sensitive = isSensitive(item.page_title, item.url);
              return (
                <div
                  key={item.id}
                  className={`p-3 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition ${
                    sensitive ? "bg-rose-950/20 border-rose-800/60" : styles.card
                  }`}
                >
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="p-2 rounded-lg bg-zinc-800/50 text-emerald-400 shrink-0 mt-0.5">
                      <Globe className="w-4 h-4" />
                    </div>

                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${getBrowserBadgeColor(item.browser_name)}`}>
                          {item.browser_name}
                        </span>

                        {sensitive && (
                          <span className="px-2 py-0.5 rounded bg-rose-900/60 border border-rose-700 text-rose-200 text-[10px] font-extrabold flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3 text-rose-300" />
                            <span>⚠️ NHẠY CẢM</span>
                          </span>
                        )}

                        <span className={`text-[11px] font-extrabold truncate ${styles.textBold}`}>
                          {item.page_title || "Trang không tiêu đề"}
                        </span>
                      </div>

                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1 truncate max-w-full"
                        >
                          <span className="truncate">{item.url}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="text-[10px] font-bold text-zinc-400 shrink-0 self-end sm:self-center">
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
