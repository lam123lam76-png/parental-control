import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { HardDrive, Database, Camera, Globe, AlertTriangle, FileText, Trash2, RefreshCw, CheckCircle2, Calendar, CheckSquare, Square, Sparkles, Image as ImageIcon, ExternalLink, ChevronRight } from "lucide-react";

export default function StorageManagementCard({ theme = "dark", deviceId = "" }) {
  const styles = getThemeStyles(theme);

  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [cleanLoading, setCleanLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Storage Category Selection: 'all' | 'screenshots' | 'web' | 'logs' | 'processes'
  const [activeCategory, setActiveCategory] = useState("all");

  // Time Grouping Filter: 'day' | 'week' | 'month'
  const [periodType, setPeriodType] = useState("day");

  // Loaded Real Data Hub Items
  const [realItems, setRealItems] = useState([]);

  // Checkbox selections: period keys selected for bulk delete
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [selectedItemIds, setSelectedItemIds] = useState([]);

  const fetchMetricsAndItems = async () => {
    setLoading(true);
    try {
      // 1. Fetch Metrics
      const resM = await api.getStorageMetrics();
      if (resM.data) {
        setMetrics(resM.data);
      }

      // 2. Fetch Real Data Items
      let currentDevId = deviceId;
      if (!currentDevId) {
        const devsRes = await api.getDevices();
        if (devsRes.data && devsRes.data.devices && devsRes.data.devices.length > 0) {
          currentDevId = devsRes.data.devices[0].device_id;
        }
      }

      const allFetchedItems = [];

      if (currentDevId) {
        // Screenshots
        try {
          const sRes = await api.getScreenshots(currentDevId);
          if (sRes.data && Array.isArray(sRes.data.screenshots)) {
            sRes.data.screenshots.forEach((s) => {
              allFetchedItems.push({
                category: "screenshots",
                id: s.id,
                timestamp: s.timestamp,
                url: s.image_url,
                title: "Ảnh chụp màn hình"
              });
            });
          }
        } catch (e) { console.warn("Fetch screenshots error:", e); }

        // Web History
        try {
          const wRes = await api.getBrowserHistory(currentDevId, 150);
          if (wRes.data && Array.isArray(wRes.data.history)) {
            wRes.data.history.forEach((w) => {
              allFetchedItems.push({
                category: "web",
                id: w.id,
                timestamp: w.timestamp,
                url: w.url,
                title: w.page_title || w.url,
                browser: w.browser_name
              });
            });
          }
        } catch (e) { console.warn("Fetch browser history error:", e); }

        // Alerts / System Logs
        try {
          const aRes = await api.getAlerts(currentDevId, 150);
          if (aRes.data && Array.isArray(aRes.data.alerts)) {
            aRes.data.alerts.forEach((a) => {
              allFetchedItems.push({
                category: "logs",
                id: a.id,
                timestamp: a.created_at,
                title: a.message,
                alert_type: a.alert_type
              });
            });
          }
        } catch (e) { console.warn("Fetch alerts error:", e); }

        // Process Activity Logs
        try {
          const pRes = await api.getLogs(currentDevId, 150);
          if (pRes.data && Array.isArray(pRes.data.logs)) {
            pRes.data.logs.forEach((p) => {
              allFetchedItems.push({
                category: "processes",
                id: p.id,
                timestamp: p.timestamp,
                title: p.process_name,
                subtitle: p.window_title
              });
            });
          }
        } catch (e) { console.warn("Fetch process logs error:", e); }
      }

      setRealItems(allFetchedItems);
    } catch (err) {
      setMessage(`Không thể tải dữ liệu tập trung: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetricsAndItems();
  }, [deviceId]);

  // Compute period group key for timestamp string
  const getPeriodKey = (tsStr) => {
    if (!tsStr) return "2026-08-11";
    const dt = new Date(tsStr);
    if (isNaN(dt.getTime())) return "2026-08-11";

    const yyyy = dt.getFullYear();
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const dd = String(dt.getDate()).padStart(2, '0');

    if (periodType === "day") {
      return `${yyyy}-${mm}-${dd}`;
    } else if (periodType === "week") {
      const firstDay = new Date(yyyy, 0, 1);
      const pastDays = (dt - firstDay) / 86400000;
      const weekNum = Math.ceil((pastDays + firstDay.getDay() + 1) / 7);
      return `${yyyy}-W${String(weekNum).padStart(2, '0')}`;
    } else if (periodType === "month") {
      return `${yyyy}-${mm}`;
    }
    return `${yyyy}-${mm}-${dd}`;
  };

  // Group real items by period key
  const getGroupedData = () => {
    const filtered = activeCategory === "all"
      ? realItems
      : realItems.filter((i) => i.category === activeCategory);

    // Sort descending
    filtered.sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));

    const groupsDict = {};

    filtered.forEach((item) => {
      const pKey = getPeriodKey(item.timestamp);
      if (!groupsDict[pKey]) {
        let label = pKey;
        if (periodType === "day") {
          const parts = pKey.split("-");
          label = `Ngày ${parts[2]}/${parts[1]}/${parts[0]}`;
        } else if (periodType === "week") {
          const parts = pKey.split("-W");
          label = `Tuần ${parts[1]}/${parts[0]}`;
        } else if (periodType === "month") {
          const parts = pKey.split("-");
          label = `Tháng ${parts[1]}/${parts[0]}`;
        }
        groupsDict[pKey] = { key: pKey, label, items: [] };
      }
      groupsDict[pKey].items.push(item);
    });

    return Object.values(groupsDict);
  };

  const groupedData = getGroupedData();

  const handleTogglePeriodGroup = (periodKey, groupItems) => {
    const isSelected = selectedPeriods.includes(periodKey);
    const itemIdsInGroup = groupItems.map((i) => i.id);

    if (isSelected) {
      setSelectedPeriods((prev) => prev.filter((k) => k !== periodKey));
      setSelectedItemIds((prev) => prev.filter((id) => !itemIdsInGroup.includes(id)));
    } else {
      setSelectedPeriods((prev) => [...prev, periodKey]);
      setSelectedItemIds((prev) => [...new Set([...prev, ...itemIdsInGroup])]);
    }
  };

  const handleToggleItem = (itemId, periodKey) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  const handleSelectAllAll = () => {
    if (selectedPeriods.length === groupedData.length && groupedData.length > 0) {
      setSelectedPeriods([]);
      setSelectedItemIds([]);
    } else {
      const allKeys = groupedData.map((g) => g.key);
      const allIds = groupedData.flatMap((g) => g.items.map((i) => i.id));
      setSelectedPeriods(allKeys);
      setSelectedItemIds(allIds);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedPeriods.length === 0 && selectedItemIds.length === 0) return;

    const totalToDelete = selectedItemIds.length || selectedPeriods.length;
    const catLabel =
      activeCategory === "all" ? "Toàn bộ dữ liệu" :
      activeCategory === "screenshots" ? "Ảnh chụp màn hình" :
      activeCategory === "web" ? "Dữ liệu duyệt web" :
      activeCategory === "logs" ? "Log hệ thống" : "Nhật ký tiến trình";

    if (!window.confirm(`Bạn có chắc chắn muốn chuyển ${totalToDelete} mục đã chọn thuộc nhóm "${catLabel}" vào Thùng Rác? File và bản ghi sẽ được chuyển vào Thùng rác (hoặc dọn dẹp).`)) return;

    setCleanLoading(true);
    setMessage("");
    try {
      // Determine periods to clean
      let periodsToSend = [...selectedPeriods];
      if (periodsToSend.length === 0 && selectedItemIds.length > 0) {
        const derivedPeriods = new Set();
        realItems.forEach((item) => {
          if (selectedItemIds.includes(item.id)) {
            derivedPeriods.add(getPeriodKey(item.timestamp));
          }
        });
        periodsToSend = Array.from(derivedPeriods);
      }

      if (periodsToSend.length === 0) {
        periodsToSend = [getPeriodKey(new Date().toISOString())];
      }
      
      const itemIdsToSend = selectedItemIds.length > 0 ? selectedItemIds : null;

      const res = await api.cleanStorageByPeriod(activeCategory, periodsToSend, periodType, itemIdsToSend);
      if (res.data) {
        setMessage(res.data.msg || `Đã dọn dẹp thành công! Giải phóng ${res.data.freed_mb} MB.`);
        setSelectedPeriods([]);
        setSelectedItemIds([]);
        await fetchMetricsAndItems();
      }
    } catch (err) {
      setMessage(`Lỗi dọn dẹp bộ nhớ: ${err.message}`);
    } finally {
      setCleanLoading(false);
    }
  };

  const shots = metrics?.screenshots || { count: 0, total_mb: 0 };

  return (
    <div className={`p-4 sm:p-5 rounded-xl space-y-5 font-sans ${styles.card}`}>
      
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-lg ${styles.card} ${styles.text}`}>
            <HardDrive className="w-5 h-5 stroke-[1.75]" />
          </div>
          <div>
            <h3 className={`text-sm font-bold ${styles.textBold}`}>
              Module quản lý bộ nhớ &amp; dữ liệu tập trung (Storage &amp; Data Hub)
            </h3>
            
          </div>
        </div>

        <button
          onClick={fetchMetricsAndItems}
          disabled={loading}
          className={`p-2 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
          title="Làm mới dữ liệu"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Làm Mới</span>
        </button>
      </div>

      {message && (
        <div className={`p-3 rounded-lg text-xs font-bold flex items-center gap-2 ${styles.inset} ${styles.text}`}>
          <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* CLOUD STORAGE SUMMARY */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className={`font-bold ${styles.textBold}`}>
            Dung lượng lưu trữ đám mây (Cloud Storage)
          </span>
          <span className={`font-mono ${styles.metricValue}`}>
            {shots.total_mb} MB — Ảnh chụp màn hình
          </span>
        </div>
        <div className={`text-xs ${styles.textMuted}`}>
          Hệ thống lưu trữ trên đám mây (Supabase Storage). Không còn ổ đĩa vật lý cục bộ.
        </div>
      </div>

      {/* 5 STORAGE CATEGORY CARDS GRID */}
      <div>
        <label className={`text-xs font-bold uppercase tracking-wider block mb-2 ${styles.textMuted}`}>
          Phân loại nhóm dữ liệu (chọn danh mục để xem &amp; dọn dẹp)
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 text-xs">

          {/* Category 0: All Categories */}
          <button
            type="button"
            onClick={() => { setActiveCategory("all"); setSelectedPeriods([]); setSelectedItemIds([]); }}
            className={`p-3 rounded-xl text-left flex items-start gap-2.5 transition ${
              activeCategory === "all"
                ? styles.chipActive
                : styles.chip
            }`}
          >
            <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div>
              <div className={`text-[10px] font-extrabold uppercase ${styles.metricLabel}`}>Toàn bộ dữ liệu</div>
              <div className={`text-xs ${styles.metricValue}`}>
                {realItems.length} mục thực
              </div>
              <div className={`text-[10px] font-mono ${styles.metricLabel}`}>
                Tất cả 4 nhóm
              </div>
            </div>
          </button>
          
          {/* Category 1: Screenshots */}
          <button
            type="button"
            onClick={() => { setActiveCategory("screenshots"); setSelectedPeriods([]); setSelectedItemIds([]); }}
            className={`p-3 rounded-xl text-left flex items-start gap-2.5 transition ${
              activeCategory === "screenshots"
                ? styles.chipActive
                : styles.chip
            }`}
          >
            <Camera className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div>
              <div className={`text-[10px] font-extrabold uppercase ${styles.metricLabel}`}>Ảnh chụp màn hình</div>
              <div className={`text-xs ${styles.metricValue}`}>
                {metrics?.screenshots?.count ?? 0} ảnh
              </div>
              <div className={`text-[10px] font-mono ${styles.metricLabel}`}>
                {metrics?.screenshots?.total_mb ?? 0} MB
              </div>
            </div>
          </button>

          {/* Category 2: Web Browsing */}
          <button
            type="button"
            onClick={() => { setActiveCategory("web"); setSelectedPeriods([]); setSelectedItemIds([]); }}
            className={`p-3 rounded-xl text-left flex items-start gap-2.5 transition ${
              activeCategory === "web"
                ? styles.chipActive
                : styles.chip
            }`}
          >
            <Globe className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div>
              <div className={`text-[10px] font-extrabold uppercase ${styles.metricLabel}`}>Dữ liệu duyệt web</div>
              <div className={`text-xs ${styles.metricValue}`}>
                {metrics?.web?.count ?? 0} URL
              </div>
              <div className={`text-[10px] font-mono ${styles.metricLabel}`}>
                {metrics?.web?.total_mb ?? 0} MB
              </div>
            </div>
          </button>

          {/* Category 3: System Logs */}
          <button
            type="button"
            onClick={() => { setActiveCategory("logs"); setSelectedPeriods([]); setSelectedItemIds([]); }}
            className={`p-3 rounded-xl text-left flex items-start gap-2.5 transition ${
              activeCategory === "logs"
                ? styles.chipActive
                : styles.chip
            }`}
          >
            <AlertTriangle className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div>
              <div className={`text-[10px] font-extrabold uppercase ${styles.metricLabel}`}>Log hệ thống / cảnh báo</div>
              <div className={`text-xs ${styles.metricValue}`}>
                {metrics?.logs?.count ?? 0} báo động
              </div>
              <div className={`text-[10px] font-mono ${styles.metricLabel}`}>
                {metrics?.logs?.total_mb ?? 0} MB
              </div>
            </div>
          </button>

          {/* Category 4: Process Activity Logs */}
          <button
            type="button"
            onClick={() => { setActiveCategory("processes"); setSelectedPeriods([]); setSelectedItemIds([]); }}
            className={`p-3 rounded-xl text-left flex items-start gap-2.5 transition ${
              activeCategory === "processes"
                ? styles.chipActive
                : styles.chip
            }`}
          >
            <FileText className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <div>
              <div className={`text-[10px] font-extrabold uppercase ${styles.metricLabel}`}>Nhật ký tiến trình</div>
              <div className={`text-xs ${styles.metricValue}`}>
                {metrics?.processes?.count ?? 0} bản ghi
              </div>
              <div className={`text-[10px] font-mono ${styles.metricLabel}`}>
                {metrics?.processes?.total_mb ?? 0} MB
              </div>
            </div>
          </button>

        </div>
      </div>

      {/* RECYCLE BIN BANNER */}
      <div className={`p-3 rounded-lg flex items-center gap-2.5 text-xs ${styles.inset}`}>
        <Trash2 className="w-4 h-4 text-rose-400 shrink-0" />
        <span className={styles.textMuted}>
          <strong className={styles.text}>Thùng rác:</strong> File ảnh (Supabase Storage) và bản ghi đã xóa được sao lưu tạm. Hệ thống tự động dọn dẹp vĩnh viễn dữ liệu quá <strong className="text-primary">7 ngày</strong>.
        </span>
      </div>

      {/* TIME GROUPING FILTER & REAL ITEM RENDERING */}
      <div className="pt-3 border-t border-opacity-20 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          
          {/* Time Filter Tabs */}
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-bold mr-1 ${styles.textMuted}`}>Gom nhóm theo:</span>
            {[
              { id: "day", label: "Ngày" },
              { id: "week", label: "Tuần" },
              { id: "month", label: "Tháng" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => { setPeriodType(t.id); setSelectedPeriods([]); setSelectedItemIds([]); }}
                className={`px-3 py-1 text-xs font-bold rounded-md transition ${
                  periodType === t.id
                    ? styles.chipActive
                    : styles.chip
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Select All Checkbox */}
          <button
            type="button"
            onClick={handleSelectAllAll}
            className={`text-xs font-bold flex items-center gap-1.5 ${styles.text} hover:underline`}
          >
            {selectedPeriods.length === groupedData.length && groupedData.length > 0 ? (
              <CheckSquare className="w-4 h-4 text-primary" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span>Chọn tất cả ({groupedData.length} mốc)</span>
          </button>

          {/* Header Bulk Delete — icon-only, dùng chung handleBulkDelete */}
          <button
            type="button"
            onClick={handleBulkDelete}
            disabled={cleanLoading || (selectedPeriods.length === 0 && selectedItemIds.length === 0)}
            title="Xóa các mục đã chọn"
            aria-label="Xóa các mục đã chọn"
            className={`py-2 px-2.5 text-xs font-bold rounded-lg transition flex items-center gap-2 ${
              selectedItemIds.length > 0 || selectedPeriods.length > 0
                ? styles.buttonDanger
                : styles.buttonSecondary
            } disabled:opacity-40`}
          >
            <Trash2 className="w-4 h-4" />
          </button>

        </div>

        {/* REAL ITEMS GROUPED BY DATE HEADERS */}
        {groupedData.length === 0 ? (
          <div className={`text-center py-12 space-y-2 border border-dashed border-[#0E3746]/20 dark:border-zinc-800 rounded-xl ${styles.inset}`}>
            <HardDrive className={`w-8 h-8 mx-auto ${styles.textMuted}`} />
            <p className={`text-xs italic ${styles.textMuted}`}>
              Không có dữ liệu thực tế nào trong danh mục này.
            </p>
          </div>
        ) : (
          <div className="space-y-5">
            {groupedData.map((group) => {
              const isGroupSelected = selectedPeriods.includes(group.key);

              return (
                <div key={group.key} className="space-y-3">
                  
                  {/* DATE GROUP HEADER */}
                  <div
                    onClick={() => handleTogglePeriodGroup(group.key, group.items)}
                    className={`p-3 rounded-lg flex items-center justify-between cursor-pointer transition ${
                      isGroupSelected ? styles.rowSelected : styles.row
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {isGroupSelected ? (
                        <CheckSquare className="w-4 h-4 text-primary shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 opacity-50 shrink-0" />
                      )}
                      <Calendar className={`w-4 h-4 ${styles.text}`} />
                      <span className={`text-xs font-extrabold ${styles.text}`}>{group.label}</span>
                    </div>

                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${styles.badge}`}>
                      {group.items.length} bản ghi thực
                    </span>
                  </div>

                  {/* REAL DATA ITEMS CONTAINER */}
                  {activeCategory === "screenshots" ? (
                    /* SCREENSHOT THUMBNAIL GRID */
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pl-4">
                      {group.items.map((item) => {
                        const isItemSelected = selectedItemIds.includes(item.id);
                        return (
                          <div
                            key={item.id}
                            onClick={() => handleToggleItem(item.id, group.key)}
                            className={`relative rounded-lg overflow-hidden cursor-pointer transition group ${
                              isItemSelected ? styles.rowSelected : `${styles.row} ${styles.rowHover}`
                            }`}
                          >
                            <img
                              src={item.url}
                              alt="Screenshot"
                              className="w-full h-24 object-cover"
                              onError={(e) => { e.target.src = "https://via.placeholder.com/300x180?text=Screenshot"; }}
                            />
                            <div className="absolute top-1 left-1 bg-black/70 rounded p-0.5">
                              {isItemSelected ? <CheckSquare className="w-4 h-4 text-primary" /> : <Square className="w-4 h-4 text-white" />}
                            </div>
                            <div className="absolute bottom-0 inset-x-0 p-1 bg-black/80 text-[10px] font-mono text-zinc-200 truncate">
                              {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "—"}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    /* LIST ITEM ROWS FOR WEB / LOGS / PROCESSES / ALL */
                    <div className="space-y-1.5 pl-2 sm:pl-4">
                      {group.items.map((item) => {
                        const isItemSelected = selectedItemIds.includes(item.id);
                        return (
                          <div
                            key={item.id}
                            onClick={() => handleToggleItem(item.id, group.key)}
                            className={`p-2.5 rounded-lg flex items-center justify-between text-xs cursor-pointer transition ${
                              isItemSelected ? styles.rowSelected : `${styles.row} ${styles.rowHover}`
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0 pr-2">
                              {isItemSelected ? (
                                <CheckSquare className="w-4 h-4 text-primary shrink-0" />
                              ) : (
                                <Square className="w-4 h-4 opacity-50 shrink-0" />
                              )}

                              {/* Icon Badge */}
                              {item.category === "web" && <Globe className="w-4 h-4 text-primary shrink-0" />}
                              {item.category === "logs" && <AlertTriangle className="w-4 h-4 text-primary shrink-0" />}
                              {item.category === "processes" && <FileText className="w-4 h-4 text-primary shrink-0" />}
                              {item.category === "screenshots" && <Camera className="w-4 h-4 text-primary shrink-0" />}

                              <div className="min-w-0">
                                <div className={`font-bold truncate flex items-center gap-2 ${styles.text}`}>
                                  <span>{item.title}</span>
                                  {item.category === "all" && (
                                    <span className={`text-[10px] uppercase px-1.5 py-0.2 rounded font-mono ${styles.badgeMuted}`}>
                                      {item.category}
                                    </span>
                                  )}
                                </div>
                                {item.url && (
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="text-xs text-primary hover:underline truncate block"
                                  >
                                    {item.url}
                                  </a>
                                )}
                                {item.subtitle && (
                                  <p className={`text-[10px] truncate ${styles.textMuted}`}>{item.subtitle}</p>
                                )}
                              </div>
                            </div>

                            <span className={`text-[10px] font-mono shrink-0 font-bold ${styles.textMuted}`}>
                              {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "—"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}

        {/* BULK DELETE ACTION BUTTON */}
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={handleBulkDelete}
            disabled={cleanLoading || (selectedPeriods.length === 0 && selectedItemIds.length === 0)}
            className={`py-2.5 px-5 text-xs font-bold rounded-lg transition flex items-center gap-2 ${
              selectedItemIds.length > 0 || selectedPeriods.length > 0
                ? styles.buttonDanger
                : styles.buttonSecondary
            } disabled:opacity-40`}
          >
            <Trash2 className="w-4 h-4" />
            <span>Xóa {selectedItemIds.length || selectedPeriods.length} mục đã chọn (bulk delete)</span>
          </button>
        </div>

      </div>

    </div>
  );
}


