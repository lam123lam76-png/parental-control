import React, { useState, useEffect, useRef } from "react";
import { api } from "../lib/api";
import { getThemeStyles } from "../lib/theme";
import { MessageSquare, Send, User, Bot, Volume2, RefreshCw } from "lucide-react";

export default function DeviceChatBox({ theme = "dark", deviceId = "", isOnline = false }) {
  const styles = getThemeStyles(theme);

  const [chats, setChats] = useState([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  const chatEndRef = useRef(null);
  const prevChatsCountRef = useRef(0);

  const fetchChatHistory = async () => {
    if (!deviceId) return;
    try {
      const res = await api.getChatHistory(deviceId);
      if (res.data && Array.isArray(res.data.chats)) {
        const newChats = res.data.chats;
        // Check if new child message arrived
        if (newChats.length > prevChatsCountRef.current) {
          const lastMsg = newChats[newChats.length - 1];
          if (lastMsg && lastMsg.sender === "child") {
            playChimeSound();
          }
        }
        prevChatsCountRef.current = newChats.length;
        setChats(newChats);
      }
    } catch (err) {
      console.error("Error fetching chat history:", err);
    }
  };

  useEffect(() => {
    fetchChatHistory();
    const interval = setInterval(fetchChatHistory, 2500); // 2.5s polling loop
    return () => clearInterval(interval);
  }, [deviceId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats]);

  const playChimeSound = () => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (e) {
      console.warn("Audio chime disabled or unsupported:", e);
    }
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || !deviceId) return;
    const msgToSend = inputText.trim();
    setInputText("");
    setSending(true);

    // Optimistic UI insert
    const tempId = `temp-${Date.now()}`;
    const tempMsg = { id: tempId, sender: "admin", message: msgToSend, timestamp: new Date().toISOString() };
    setChats((prev) => [...prev, tempMsg]);

    try {
      await api.sendChatMessage(deviceId, msgToSend);
      fetchChatHistory();
    } catch (err) {
      alert(`Lỗi gửi tin nhắn: ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={`p-4 sm:p-5 rounded-xl border flex flex-col h-[480px] font-sans ${styles.card}`}>
      
      {/* HEADER */}
      <div className="flex items-center justify-between pb-3 border-b border-opacity-20 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-zinc-900/70 border border-zinc-900 border-l-2 border-l-[#064E3B] text-[#F8E7C9]">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className={`text-sm font-extrabold flex items-center gap-2 ${styles.textBold}`}>
              <span>Trò Chuyện 2 Chiều Real-Time</span>
              <span className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`} />
            </h3>
            <p className={`text-[11px] ${styles.textMuted}`}>
              {isOnline ? "Thiết bị đang online — Tin nhắn nhận tức thì" : "Thiết bị offline — Tin nhắn lưu trong DB"}
            </p>
          </div>
        </div>

        <button
          onClick={fetchChatHistory}
          className={`p-1.5 rounded-lg border ${styles.buttonSecondary}`}
          title="Tải lại trò chuyện"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* MESSAGES CONTAINER */}
      <div className="flex-1 overflow-y-auto py-3 space-y-3 font-sans text-xs">
        {chats.length === 0 ? (
          <div className="text-center py-12 space-y-2">
            <MessageSquare className="w-8 h-8 text-zinc-600 mx-auto" />
            <p className={`text-xs italic ${styles.textMuted}`}>
              Chưa có tin nhắn nào. Hãy gửi tin nhắn đầu tiên tới thiết bị!
            </p>
          </div>
        ) : (
          chats.map((c) => {
            const isAdmin = c.sender === "admin";
            return (
              <div
                key={c.id}
                className={`flex items-end gap-2 ${isAdmin ? "justify-end" : "justify-start"}`}
              >
                {!isAdmin && (
                  <div className="px-2 py-0.5 rounded-full bg-emerald-900/40 border border-emerald-700/50 flex items-center justify-center text-emerald-300 text-[10px] font-bold shrink-0">
                    Máy Con
                  </div>
                )}

                <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 space-y-1 ${
                  isAdmin
                    ? "bg-[#064E3B] text-[#F8E7C9] rounded-br-none border border-[#064E3B]"
                    : "bg-emerald-950/60 text-zinc-100 rounded-bl-none border border-emerald-900/50"
                }`}>
                  <div className="font-bold text-xs break-words">{c.message}</div>
                  <div className={`text-[9px] text-right font-medium opacity-70`}>
                    {c.timestamp ? new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "—"}
                  </div>
                </div>

                {isAdmin && (
                  <div className="px-2 py-0.5 rounded-full bg-[#064E3B]/40 border border-zinc-800 flex items-center justify-center text-[#F8E7C9] text-[10px] font-bold shrink-0">
                    Bạn
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={chatEndRef} />
      </div>

      {/* INPUT FORM */}
      <form onSubmit={handleSendMessage} className="pt-3 border-t border-opacity-20 flex gap-2 shrink-0">
        <input
          type="text"
          placeholder="Nhập tin nhắn gửi tới thiết bị..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className={`flex-1 p-2.5 text-xs font-bold rounded-lg border focus:outline-none ${styles.input}`}
        />
        <button
          type="submit"
          disabled={sending || !inputText.trim()}
          className={`px-4 py-2.5 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${styles.buttonPrimary} disabled:opacity-50`}
        >
          <Send className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Gửi</span>
        </button>
      </form>

    </div>
  );
}
