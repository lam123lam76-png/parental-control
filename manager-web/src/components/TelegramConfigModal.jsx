import React, { useState, useEffect } from "react";
import { Send, CheckCircle2, AlertCircle, Save, X } from "lucide-react";
import { api } from "../lib/api";

export default function TelegramConfigModal({ isOpen, onClose, theme = "dark" }) {
  const [botToken, setBotToken] = useState("8754890738:AAEGB2dZCXJzlQ-Bzk1zwN3n2HLxAyj8imA");
  const [chatId, setChatId] = useState("1326412172");
  const [statusMsg, setStatusMsg] = useState("");
  const [isError, setIsError] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const loadConfig = async () => {
      try {
        const res = await api.getTelegramConfig().catch(() => null);
        if (res && res.data) {
          if (res.data.bot_token) setBotToken(res.data.bot_token);
          if (res.data.chat_id) setChatId(res.data.chat_id);
        }
      } catch (e) {
        // Fallback to default
      }
    };
    loadConfig();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    if (!botToken || !chatId) {
      setIsError(true);
      setStatusMsg("Vui lòng nhập đầy đủ Telegram Bot Token và Chat ID.");
      return;
    }
    setLoading(true);
    setStatusMsg("");
    try {
      const res = await api.saveTelegramConfig(botToken, chatId);
      setIsError(false);
      setStatusMsg(res.data?.msg || "Đã lưu cấu hình Telegram thành công!");
    } catch (err) {
      setIsError(true);
      setStatusMsg(err.message || "Lỗi lưu cấu hình Telegram.");
    } finally {
      setLoading(false);
    }
  };

  const handleTestSend = async (e) => {
    if (e) e.preventDefault();
    if (!botToken || !chatId) {
      setIsError(true);
      setStatusMsg("Vui lòng nhập đầy đủ Telegram Bot Token và Chat ID.");
      return;
    }
    setLoading(true);
    setStatusMsg("");
    try {
      const res = await api.sendTelegramTest(botToken, chatId);
      setIsError(false);
      setStatusMsg(res.data?.msg || "⚡ Đã gửi tin nhắn thông báo thử nghiệm tới Telegram!");
    } catch (err) {
      setIsError(true);
      setStatusMsg(err.message || "Lỗi gửi thông báo thử nghiệm Telegram.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div className={`max-w-md w-full p-6 rounded-xl border shadow-2xl space-y-4 ${
        theme === "dark" ? "bg-zinc-900 border-zinc-900 text-[#F4F2EC]" : "bg-[#FFFFFF] border-[#DECC9F] text-[#0E3746]"
      }`}>
        <div className="flex justify-between items-center border-b pb-3 border-opacity-20">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Send className="w-4 h-4 stroke-[1.75]" />
            <span>Cấu Hình Thông Báo Telegram Bot</span>
          </h3>
          <button onClick={onClose} className="opacity-70 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>

        {statusMsg && (
          <div className={`p-2.5 rounded text-xs font-bold flex items-center gap-2 ${
            isError ? "bg-rose-900/30 border border-rose-800 text-rose-300" : "bg-[#0E3746]/20 border border-[#0E3746] text-[#F4F2EC]"
          }`}>
            {isError ? <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" /> : <CheckCircle2 className="w-4 h-4 shrink-0 text-primary" />}
            <span>{statusMsg}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-3 text-xs">
          <div>
            <label className="block font-bold uppercase text-[10px] opacity-75 mb-1">Telegram Bot Token</label>
            <input
              type="text"
              placeholder="e.g., 8754890738:AAEGB2dZCXJzlQ-Bzk1zwN3n2HLxAyj8imA"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
              className={`w-full p-2 rounded-md border focus:outline-none font-mono text-xs ${
                theme === "dark" ? "bg-zinc-950 border-zinc-800 text-[#F4F2EC]" : "bg-[#F4F2EC]/40 border-[#DECC9F] text-[#0E3746]"
              }`}
            />
          </div>

          <div>
            <label className="block font-bold uppercase text-[10px] opacity-75 mb-1">
              Telegram Chat ID Phụ Huynh 
              <span className="normal-case opacity-60 ml-1">(Phân cách nhiều ID bằng dấu phẩy)</span>
            </label>
            <input
              type="text"
              placeholder="e.g., 1326412172, 987654321"
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              className={`w-full p-2 rounded-md border focus:outline-none font-mono text-xs ${
                theme === "dark" ? "bg-zinc-950 border-zinc-800 text-[#F4F2EC]" : "bg-[#F4F2EC]/40 border-[#DECC9F] text-[#0E3746]"
              }`}
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={loading}
              className="px-3 py-1.5 rounded border border-[#0E3746] opacity-90 hover:opacity-100 font-bold flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Lưu Cấu Hình</span>
            </button>
            <button
              type="button"
              onClick={handleTestSend}
              disabled={loading}
              className="px-4 py-1.5 bg-[#0E3746] text-[#F4F2EC] font-bold rounded hover:opacity-90 shadow-sm active:scale-[0.98] flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{loading ? "Đang xử lý..." : "Gửi Thử Nghiệm"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
