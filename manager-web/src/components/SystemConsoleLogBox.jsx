import React, { useState, useEffect, useRef } from "react";
import { Terminal, Trash2, Pause, Play, Filter, CheckCircle2, AlertTriangle, XCircle, Info, Copy, Check } from "lucide-react";
import { getThemeStyles } from "../lib/theme";

export default function SystemConsoleLogBox({ theme = "dark", realLogs = [], alerts = [], status = {}, userActionLogs = [] }) {
  const styles = getThemeStyles(theme);
  const [filterLevel, setFilterLevel] = useState("ALL"); // 'ALL' | 'INFO' | 'SUCCESS' | 'WARN' | 'ERROR'
  const [isPaused, setIsPaused] = useState(false);
  const [copied, setCopied] = useState(false);
  const logContainerRef = useRef(null);

  // Construct real log stream entries from backend props
  const [logs, setLogs] = useState([]);
  const seenIdsRef = useRef(new Set());
  const lastOnlineStatusRef = useRef(null);

  useEffect(() => {
    if (isPaused) return;

    const newIncoming = [];

    // 0. User Actions & Interactive Events (Screenshot requested, received, lock/unlock, rule created/deleted)
    if (Array.isArray(userActionLogs)) {
      userActionLogs.forEach((action) => {
        if (!seenIdsRef.current.has(action.id)) {
          seenIdsRef.current.add(action.id);
          newIncoming.push(action);
        }
      });
    }

    // 1. Connection Status Entry (Only log when status ACTUALLY changes to prevent 15s spam)
    if (status && status.is_online !== undefined) {
      if (lastOnlineStatusRef.current !== status.is_online) {
        const isInitial = lastOnlineStatusRef.current === null;
        lastOnlineStatusRef.current = status.is_online;
        const statusId = `status-${status.is_online ? "on" : "off"}-${Date.now()}`;
        newIncoming.push({
          id: statusId,
          time: new Date().toLocaleTimeString(),
          level: status.is_online ? "SUCCESS" : "WARN",
          stream: "LUỒNG 1: WS",
          msg: status.is_online
            ? "WebSocket Connection Established & Active (Heartbeat OK)"
            : (isInitial ? "WebSocket Connection Offline — Agent Disconnected" : "WebSocket Connection Lost — Agent Disconnected")
        });
      }
    }

    // 2. Real Alerts (Luồng 2)
    if (Array.isArray(alerts)) {
      alerts.forEach((alert) => {
        const aId = `alert-${alert.id}`;
        if (!seenIdsRef.current.has(aId)) {
          seenIdsRef.current.add(aId);
          newIncoming.push({
            id: aId,
            time: alert.created_at ? new Date(alert.created_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
            level: alert.alert_type?.includes("banned") ? "WARN" : "ERROR",
            stream: "LUỒNG 2: ALERT",
            msg: `Alert [${alert.alert_type}]: ${alert.message}`
          });
        }
      });
    }

    // 3. Real Process Logs (Luồng 3)
    if (Array.isArray(realLogs)) {
      realLogs.forEach((log) => {
        const lId = `log-${log.id}`;
        if (!seenIdsRef.current.has(lId)) {
          seenIdsRef.current.add(lId);
          newIncoming.push({
            id: lId,
            time: log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
            level: "INFO",
            stream: "LUỒNG 3: BATCH",
            msg: `Process Activity: ${log.process_name} (${log.window_title || "No Window Title"})`
          });
        }
      });
    }

    if (newIncoming.length > 0) {
      setLogs((prev) => [...prev, ...newIncoming].slice(-200));
    }
  }, [realLogs, alerts, status, userActionLogs, isPaused]);

  // Auto-scroll log box to bottom
  useEffect(() => {
    if (logContainerRef.current && !isPaused) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isPaused]);

  const filteredLogs = logs.filter(
    (log) => filterLevel === "ALL" || log.level === filterLevel
  );

  const handleCopyLogs = () => {
    const text = filteredLogs.map((l) => `[${l.time}] [${l.level}] [${l.stream}] ${l.msg}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Compact Icon-only Badges without redundant text
  const getLevelBadge = (level) => {
    switch (level) {
      case "SUCCESS":
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" title="SUCCESS" />;
      case "WARN":
        return <AlertTriangle className="w-3.5 h-3.5 text-emerald-400 shrink-0" title="WARN" />;
      case "ERROR":
        return <XCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" title="ERROR" />;
      default:
        return <Info className="w-3.5 h-3.5 text-emerald-400 shrink-0" title="INFO" />;
    }
  };

  return (
    <div className="space-y-4">
      
      {/* HEADER CONTROLS */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 stroke-[1.75]" />
          <h3 className={`text-sm font-bold ${styles.textBold}`}>
            Nhật Ký Console Hệ Thống Trực Quan (System Log Box)
          </h3>
          <span className="flex h-2 w-2 relative ml-1">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isPaused ? "bg-emerald-400" : "bg-emerald-400"}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${isPaused ? "bg-emerald-500" : "bg-emerald-500"}`} />
          </span>
        </div>

        {/* LOG CONTROLS: Filter, Pause, Clear, Copy */}
        <div className="flex items-center flex-wrap gap-2 text-xs">
          {/* Level Filter Buttons */}
          <div className={`p-1 rounded-lg border flex items-center gap-1 ${styles.card}`}>
            <Filter className="w-3 h-3 ml-1 opacity-60" />
            {["ALL", "INFO", "SUCCESS", "WARN"].map((lvl) => (
              <button
                key={lvl}
                onClick={() => setFilterLevel(lvl)}
                className={`px-2 py-0.5 text-[10px] font-extrabold rounded transition ${
                  filterLevel === lvl ? styles.badge : "opacity-70 hover:opacity-100"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>

          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-1.5 px-2.5 rounded-lg border text-xs font-bold flex items-center gap-1 ${styles.buttonSecondary}`}
            title={isPaused ? "Tiếp tục chạy log" : "Tạm dừng log"}
          >
            {isPaused ? <Play className="w-3 h-3 text-emerald-500" /> : <Pause className="w-3 h-3 text-emerald-500" />}
            <span>{isPaused ? "Resume" : "Pause"}</span>
          </button>

          <button
            onClick={handleCopyLogs}
            className={`p-1.5 px-2.5 rounded-lg border text-xs font-bold flex items-center gap-1 ${styles.buttonSecondary}`}
          >
            {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? "Copied!" : "Copy"}</span>
          </button>

          <button
            onClick={() => setLogs([])}
            className={`p-1.5 px-2.5 rounded-lg border text-xs font-bold flex items-center gap-1 ${styles.buttonSecondary}`}
            title="Xóa sạch nhật ký"
          >
            <Trash2 className="w-3 h-3 text-emerald-500" />
            <span>Clear</span>
          </button>
        </div>
      </div>

      {/* CONSOLE LOG BOX CONTAINER */}
      <div className={`rounded-xl border shadow-xl overflow-hidden font-mono text-xs ${
        theme === "dark" ? "bg-zinc-950 border-zinc-800" : "bg-zinc-950 border-[#DECC9F] text-[#F8E7C9]"
      }`}>
        
        {/* Terminal Top Window Bar */}
        <div className="px-4 py-2 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between text-[11px] text-[#F8E7C9]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
            <span className="ml-2 font-bold opacity-80">ParentalControlSystem.log</span>
          </div>
          <div className="opacity-70 text-[10px]">
            {filteredLogs.length} Entries Logged
          </div>
        </div>

        {/* Console Output Log Stream — Plain Colored Text without Box Fill Shapes */}
        <div
          ref={logContainerRef}
          className="h-80 overflow-y-auto p-4 space-y-2.5 bg-zinc-950 text-[#F8E7C9] font-mono text-[11px] leading-relaxed"
        >
          {filteredLogs.length === 0 ? (
            <div className="text-center py-12 opacity-50 italic">
              Không có bản ghi nhật ký phù hợp với bộ lọc.
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-2 hover:bg-zinc-900 p-1.5 rounded transition text-[11px] leading-relaxed">
                <span className="opacity-50 shrink-0 text-[10px] pt-0.5">{log.time}</span>
                <div className="shrink-0 pt-0.5">{getLevelBadge(log.level)}</div>
                <span className="text-emerald-400 font-extrabold shrink-0 pt-0.5">
                  [{log.stream}]
                </span>
                <span className="flex-1 font-medium text-[#F8E7C9] break-words whitespace-pre-wrap leading-tight">
                  {log.msg}
                </span>
              </div>
            ))
          )}
        </div>

        {/* Terminal Bottom Status Bar */}
        <div className="px-4 py-1.5 bg-zinc-950 border-t border-zinc-800 flex justify-between items-center text-[10px] text-[#F8E7C9] opacity-80">
          <span>System Status: <span className="text-emerald-400 font-bold">OPERATIONAL</span></span>
          <span>WebSocket Stream 1 • Alert Stream 2 • Batch Stream 3</span>
        </div>

      </div>

    </div>
  );
}
