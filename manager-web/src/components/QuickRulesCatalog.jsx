import React from "react";
import { Shield, ShieldAlert, Check, Plus, Trash2, Gamepad2, Globe, Sparkles } from "lucide-react";

export const CATALOG_ITEMS = [
  // Games
  { id: "riot", name: "Riot Client (LoL/Valorant)", target: "RiotClientServices.exe", type: "app", category: "game", icon: "🔴" },
  { id: "lol", name: "Liên Minh Huyền Thoại", target: "LeagueClient.exe", type: "app", category: "game", icon: "⚔️" },
  { id: "valorant", name: "Valorant", target: "Valorant.exe", type: "app", category: "game", icon: "🎯" },
  { id: "roblox", name: "Roblox", target: "RobloxPlayerBeta.exe", type: "app", category: "game", icon: "🧱" },
  { id: "minecraft", name: "Minecraft", target: "javaw.exe", type: "app", category: "game", icon: "⛏️" },
  { id: "steam", name: "Steam Store & Games", target: "steam.exe", type: "app", category: "game", icon: "🕹️" },
  { id: "garena", name: "Garena Client", target: "Garena.exe", type: "app", category: "game", icon: "🎯" },
  { id: "genshin", name: "Genshin Impact", target: "GenshinImpact.exe", type: "app", category: "game", icon: "✨" },
  { id: "discord", name: "Discord", target: "Discord.exe", type: "app", category: "game", icon: "💬" },
  // Social / Web
  { id: "tiktok", name: "TikTok", target: "tiktok.com", type: "web", category: "social", icon: "🎵" },
  { id: "facebook", name: "Facebook", target: "facebook.com", type: "web", category: "social", icon: "👥" },
  { id: "youtube", name: "YouTube", target: "youtube.com", type: "web", category: "social", icon: "▶️" },
  { id: "bilibili", name: "Bilibili", target: "bilibili.tv", type: "web", category: "social", icon: "📺" },
  { id: "netflix", name: "Netflix", target: "netflix.com", type: "web", category: "social", icon: "🎬" },
  { id: "twitch", name: "Twitch", target: "twitch.tv", type: "web", category: "social", icon: "🟣" },
];

export default function QuickRulesCatalog({ currentRules = [], onToggleRule, styles }) {
  const isRuleActive = (item) => {
    return currentRules.some(
      (r) => r.rule_type === item.type && r.target.toLowerCase() === item.target.toLowerCase()
    );
  };

  const getActiveRuleId = (item) => {
    const r = currentRules.find(
      (rule) => rule.rule_type === item.type && rule.target.toLowerCase() === item.target.toLowerCase()
    );
    return r ? r.id : null;
  };

  const games = CATALOG_ITEMS.filter((i) => i.category === "game");
  const socials = CATALOG_ITEMS.filter((i) => i.category === "social");

  return (
    <div className={`p-4 sm:p-5 rounded-xl border space-y-4 ${styles.card}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
            Danh Mục Chặn Nhanh (1 Chạm)
          </h4>
        </div>
        <span className={`text-[10px] ${styles.textMuted}`}>Gợi ý ứng dụng & website phổ biến</span>
      </div>

      {/* Games Category */}
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-400">
          <Gamepad2 className="w-3.5 h-3.5" />
          <span>Game & Nền Tảng Game</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {games.map((item) => {
            const active = isRuleActive(item);
            const ruleId = getActiveRuleId(item);
            return (
              <div
                key={item.id}
                className={`p-2.5 rounded-lg border flex items-center justify-between text-xs transition ${
                  active ? "bg-rose-950/20 border-rose-900/50" : styles.card
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <span className="text-lg shrink-0">{item.icon}</span>
                  <div className="flex flex-col truncate">
                    <span className={`font-bold truncate ${styles.textBold}`}>{item.name}</span>
                    <span className={`text-[10px] font-mono opacity-70 truncate ${styles.textMuted}`}>{item.target}</span>
                  </div>
                </div>
                <button
                  onClick={() => onToggleRule(item, active, ruleId)}
                  className={`shrink-0 ml-2 text-[10px] font-bold px-2.5 py-1 rounded border transition flex items-center gap-1 ${
                    active
                      ? "text-rose-400 border-rose-800/40 bg-rose-900/30 hover:bg-rose-900/50 hover:text-rose-300"
                      : "text-emerald-500 border-emerald-800/40 bg-emerald-900/20 hover:bg-emerald-900/40 hover:text-emerald-400"
                  }`}
                >
                  {active ? (
                    <>
                      <Trash2 className="w-3 h-3" />
                      <span>Đã Chặn</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-3 h-3" />
                      <span>Chặn</span>
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Socials & Media Category */}
      <div className="space-y-2 pt-2 border-t border-zinc-800/60">
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-blue-400">
          <Globe className="w-3.5 h-3.5" />
          <span>Mạng Xã Hội & Giải Trí Trực Tuyến</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {socials.map((item) => {
            const active = isRuleActive(item);
            const ruleId = getActiveRuleId(item);
            return (
              <div
                key={item.id}
                className={`p-2.5 rounded-lg border flex items-center justify-between text-xs transition ${
                  active ? "bg-rose-950/20 border-rose-900/50" : styles.card
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <span className="text-lg shrink-0">{item.icon}</span>
                  <div className="flex flex-col truncate">
                    <span className={`font-bold truncate ${styles.textBold}`}>{item.name}</span>
                    <span className={`text-[10px] font-mono opacity-70 truncate ${styles.textMuted}`}>{item.target}</span>
                  </div>
                </div>
                <button
                  onClick={() => onToggleRule(item, active, ruleId)}
                  className={`shrink-0 ml-2 text-[10px] font-bold px-2.5 py-1 rounded border transition flex items-center gap-1 ${
                    active
                      ? "text-rose-400 border-rose-800/40 bg-rose-900/30 hover:bg-rose-900/50 hover:text-rose-300"
                      : "text-emerald-500 border-emerald-800/40 bg-emerald-900/20 hover:bg-emerald-900/40 hover:text-emerald-400"
                  }`}
                >
                  {active ? (
                    <>
                      <Trash2 className="w-3 h-3" />
                      <span>Đã Chặn</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-3 h-3" />
                      <span>Chặn</span>
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}