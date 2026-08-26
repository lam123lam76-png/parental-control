import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { Cpu, Rocket, CheckCircle2, Package, RefreshCw, Sparkles } from "lucide-react";

export default function AgentUpdateManagerCard({ theme = "dark" }) {
  const styles = getThemeStyles(theme);

  const [versionInfo, setVersionInfo] = useState(null);
  const [newVersion, setNewVersion] = useState("v0002");
  const [packing, setPacking] = useState(false);
  const [isPacked, setIsPacked] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [message, setMessage] = useState("");

  const suggestNextVersion = (currVer) => {
    if (!currVer) return "v0002";
    const match = currVer.match(/v(\d+)/i);
    if (match) {
      const nextNum = parseInt(match[1], 10) + 1;
      return `v${String(nextNum).padStart(4, "0")}`;
    }
    return "v0002";
  };

  const fetchVersion = async () => {
    try {
      const res = await api.getAgentVersion();
      if (res && res.data) {
        setVersionInfo(res.data);
        const suggested = suggestNextVersion(res.data.version);
        setNewVersion(suggested);
      }
    } catch (err) {
      console.warn("Could not fetch version:", err);
    }
  };

  useEffect(() => {
    fetchVersion();
  }, []);

  // STEP 1: PACK ZIP VIA SYSTEM BATCH SCRIPT
  const handlePackZip = async () => {
    if (!newVersion) return setMessage("Vui lòng nhập định dạng số phiên bản (Ví dụ: v0002)!");

    setPacking(true);
    setMessage("");
    try {
      const res = await api.packAgentZip(newVersion);
      if (res && res.data) {
        setIsPacked(true);
        setMessage(`📦 Đã đóng gói thành công file zip cho phiên bản ${newVersion}! Nút 'Phát Hành' đã sẵn sàng.`);
      } else {
        setMessage(`❌ Lỗi đóng gói: ${res?.error || "Không thể thực thi script đóng gói."}`);
      }
    } catch (err) {
      setMessage(`❌ Lỗi đóng gói batch: ${err.message}`);
    } finally {
      setPacking(false);
    }
  };

  // STEP 2: PUBLISH & DEPLOY TO AGENTS VIA WEBSOCKET
  const handlePublishAndDeploy = async () => {
    if (!isPacked) return setMessage("Vui lòng thực hiện Bước 1: Đóng gói File Zip trước!");
    if (!window.confirm(`Xác nhận phát hành và gửi lệnh cập nhật ngầm phiên bản ${newVersion} tới tất cả máy đích Agent?`)) return;

    setDeploying(true);
    setMessage("");
    try {
      const res = await api.forceUpdateAllDevices();
      if (res && res.data) {
        setMessage(`🚀 ĐÃ PHÁT HÀNH THÀNH CÔNG! Đã gửi lệnh nâng cấp ${newVersion} tới ${res.data.notified_devices} máy Agent đang trực tuyến. Sau khi cài đặt hoàn tất, máy đích sẽ tự báo thành công!`);
        fetchVersion();
      } else {
        setMessage(`❌ Lỗi phát hành: ${res?.error || "Không thể gửi lệnh."}`);
      }
    } catch (err) {
      setMessage(`❌ Lỗi phát hành cập nhật: ${err.message}`);
    } finally {
      setDeploying(false);
    }
  };

  return (
    <div className={`p-4 sm:p-6 rounded-xl border space-y-6 font-sans ${styles.card}`}>
      
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800 border-l-2 border-l-[#064E3B] text-[#F8E7C9]">
            <Cpu className="w-5 h-5 stroke-[1.75]" />
          </div>
          <div>
            <h3 className={`text-sm font-extrabold ${styles.textBold}`}>
              Quy Trình Đóng Gói & Cập Nhật Agent Từ Xa
            </h3>
            <p className={`text-xs font-medium ${styles.textMuted}`}>
              Đóng gói tự động qua script hệ thống và phát hành cưỡng chế tới máy đích.
            </p>
          </div>
        </div>

        <button
          onClick={fetchVersion}
          className={`p-2 rounded-lg border text-xs font-bold flex items-center gap-1.5 transition ${styles.buttonSecondary}`}
          title="Tải lại phiên bản hiện tại"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* NOTIFICATION BANNER */}
      {message && (
        <div className={`p-3.5 rounded-lg border text-xs font-bold flex items-center gap-2.5 ${message.includes("❌") ? "bg-rose-900/30 border-rose-800/50 text-rose-300" : "bg-[#064E3B]/25 border-zinc-800 text-[#F8E7C9]"}`}>
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="flex-1">{message}</span>
        </div>
      )}

      {/* CURRENT VERSION DISPLAY */}
      <div className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${styles.card}`}>
        <div>
          <div className={`text-[10px] font-bold uppercase ${styles.textMuted}`}>PHIÊN BẢN ĐANG PHÁT HÀNH TRÊN SERVER</div>
          <div className="text-base font-extrabold text-[#F8E7C9] flex items-center gap-2.5 mt-0.5">
            <span>Phiên Bản Hiện Tại: <span className="text-emerald-400">{versionInfo?.version || "v0001"}</span></span>
            <span className="px-2 py-0.5 rounded bg-[#064E3B] text-[#F8E7C9] text-[10px] font-bold tracking-wider">ACTIVE</span>
          </div>
        </div>

        <div className="text-right">
          <div className={`text-[10px] font-bold ${styles.textMuted}`}>Đường Dẫn Gói Nâng Cấp:</div>
          <div className="text-xs font-mono text-[#F8E7C9] bg-black/40 px-2.5 py-1 rounded border border-white/10 mt-1">
            {versionInfo?.download_url || "/static/updates/agent-update.zip"}
          </div>
        </div>
      </div>

      {/* STEP-BY-STEP WORKFLOW FORM */}
      <div className="space-y-5 pt-3 border-t border-white/10">
        
        {/* INPUT: VERSION NUMBER WITH AUTO SUGGESTION */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
              1. CHỌN/ĐIỀN SỐ PHIÊN BẢN MỚI
            </label>
            <span className="text-[10px] text-emerald-400 font-bold flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Gợi ý tiếp theo: {suggestNextVersion(versionInfo?.version)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Định dạng: v0001, v0002 (Lột xác: v1001)"
              value={newVersion}
              onChange={(e) => {
                setNewVersion(e.target.value);
                setIsPacked(false);
              }}
              className={`flex-1 p-3 text-sm font-bold font-mono rounded-xl border focus:outline-none ${styles.input}`}
            />
            <button
              type="button"
              onClick={() => {
                const sug = suggestNextVersion(versionInfo?.version);
                setNewVersion(sug);
                setIsPacked(false);
              }}
              className={`px-3.5 py-3 rounded-xl border text-xs font-bold transition ${styles.buttonSecondary}`}
              title="Dùng phiên bản gợi ý"
            >
              Gợi Ý Tiếp Theo
            </button>
          </div>
          <p className={`text-[11px] ${styles.textMuted}`}>
            Ghi chú: Bản vá thông thường sử dụng chuỗi tăng dần: <span className="font-mono text-emerald-400 font-bold">v0001 → v0002 → v0003</span>. Đột phá phiên bản lớn sử dụng: <span className="font-mono text-amber-400 font-bold">v1001</span>.
          </p>
        </div>

        {/* WORKFLOW BUTTONS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          
          {/* STEP 1: PACK ZIP BUTTON */}
          <button
            type="button"
            onClick={handlePackZip}
            disabled={packing || !newVersion}
            className={`p-4 rounded-xl border font-bold text-xs flex items-center justify-center gap-2.5 transition shadow-lg ${
              isPacked
                ? "bg-emerald-900/40 border-emerald-500/70 text-emerald-300"
                : newVersion
                ? "bg-[#064E3B] border-emerald-400 text-[#F8E7C9] hover:bg-[#064E3B]/80 hover:scale-[1.01]"
                : "bg-zinc-800/50 border-zinc-700 text-zinc-500 opacity-50 cursor-not-allowed"
            }`}
          >
            <Package className={`w-4 h-4 ${packing ? "animate-bounce" : ""}`} />
            <span>{packing ? "Đang chạy script đóng gói build..." : isPacked ? "✅ Đã Đóng Gói File Zip" : "📦 1. Đóng Gói File Zip"}</span>
          </button>

          {/* STEP 2: PUBLISH & DEPLOY BUTTON */}
          <button
            type="button"
            onClick={handlePublishAndDeploy}
            disabled={deploying || !isPacked}
            className={`p-4 rounded-xl border font-bold text-xs flex items-center justify-center gap-2.5 transition shadow-lg ${
              isPacked
                ? "bg-gradient-to-r from-emerald-600 to-teal-600 border-emerald-300 text-white hover:brightness-110 hover:scale-[1.01] animate-pulse"
                : "bg-zinc-800/50 border-zinc-700 text-zinc-500 opacity-50 cursor-not-allowed"
            }`}
          >
            <Rocket className={`w-4 h-4 ${deploying ? "animate-spin" : ""}`} />
            <span>{deploying ? "Đang gửi lệnh cập nhật tới Agent..." : "🚀 2. Phát Hành & Cài Cập Nhật Trên Agent"}</span>
          </button>

        </div>

      </div>

    </div>
  );
}
