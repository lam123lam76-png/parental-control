import React from "react";
import { Plus, Trash2 } from "lucide-react";

export const CATALOG_ITEMS = [
  // Games
  { id: "riot", name: "Riot Client (LoL/Valorant)", target: "RiotClientServices.exe", type: "app", category: "game" },
  { id: "lol", name: "Liên Minh Huyền Thoại", target: "LeagueClient.exe", type: "app", category: "game" },
  { id: "valorant", name: "Valorant", target: "Valorant.exe", type: "app", category: "game" },
  { id: "roblox", name: "Roblox", target: "RobloxPlayerBeta.exe", type: "app", category: "game" },
  { id: "minecraft", name: "Minecraft", target: "javaw.exe", type: "app", category: "game" },
  { id: "steam", name: "Steam Store & Games", target: "steam.exe", type: "app", category: "game" },
  { id: "garena", name: "Garena Client", target: "Garena.exe", type: "app", category: "game" },
  { id: "genshin", name: "Genshin Impact", target: "GenshinImpact.exe", type: "app", category: "game" },
  { id: "discord", name: "Discord", target: "Discord.exe", type: "app", category: "game" },
  // Social / Web
  { id: "tiktok", name: "TikTok", target: "tiktok.com", type: "web", category: "social" },
  { id: "facebook", name: "Facebook", target: "facebook.com", type: "web", category: "social" },
  { id: "youtube", name: "YouTube", target: "youtube.com", type: "web", category: "social" },
  { id: "bilibili", name: "Bilibili", target: "bilibili.tv", type: "web", category: "social" },
  { id: "netflix", name: "Netflix", target: "netflix.com", type: "web", category: "social" },
  { id: "twitch", name: "Twitch", target: "twitch.tv", type: "web", category: "social" },
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
        <h4 className={`text-xs font-bold uppercase tracking-wider ${styles.textBold}`}>
          Danh Mục Chặn Nhanh (1 Chạm)
        </h4>
      </div>

      {/* Games Category */}
      <div className="space-y-2">
        <div className="text-xs font-bold text-primary">
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
                  active ? "bg-primary/20 border-primary/50" : styles.card
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <div className="flex flex-col truncate">
                    <span className={`font-bold truncate ${styles.textBold}`}>{item.name}</span>
                    <span className={`text-[10px] font-mono opacity-70 truncate ${styles.textMuted}`}>{item.target}</span>
                  </div>
                </div>
                <button
                  onClick={() => onToggleRule(item, active, ruleId)}
                  className={`shrink-0 ml-2 text-[10px] font-bold px-2.5 py-1 rounded border transition flex items-center gap-1 ${
                    active
                      ? "text-primary border-primary/40 bg-primary/30 hover:bg-primary/50 hover:text-primary"
                      : styles.buttonSecondary
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
        <div className="text-xs font-bold text-primary">
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
                  active ? "bg-primary/20 border-primary/50" : styles.card
                }`}
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  
                  <div className="flex flex-col truncate">
                    <span className={`font-bold truncate ${styles.textBold}`}>{item.name}</span>
                    <span className={`text-[10px] font-mono opacity-70 truncate ${styles.textMuted}`}>{item.target}</span>
                  </div>
                </div>
                <button
                  onClick={() => onToggleRule(item, active, ruleId)}
                  className={`shrink-0 ml-2 text-[10px] font-bold px-2.5 py-1 rounded border transition flex items-center gap-1 ${
                    active
                      ? "text-primary border-primary/40 bg-primary/30 hover:bg-primary/50 hover:text-primary"
                      : styles.buttonSecondary
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
