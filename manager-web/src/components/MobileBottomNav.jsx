import React from "react";
import { LayoutDashboard, Terminal, Camera, Shield, FileText, Settings } from "lucide-react";

export default function MobileBottomNav({ activeNav, setActiveNav, theme = "dark" }) {
  const navItems = [
    { id: "overview",    label: "Home",     icon: LayoutDashboard },
    { id: "system_logs", label: "Console",  icon: Terminal },
    { id: "screenshots", label: "Photos",   icon: Camera },
    { id: "rules",       label: "Rules",    icon: Shield },
    { id: "logs",        label: "Logs",     icon: FileText },
    { id: "rbac",        label: "Settings", icon: Settings },
  ];


  return (
    <nav className={`md:hidden fixed bottom-0 inset-x-0 z-40 border-t backdrop-blur-lg transition-colors px-2 py-1.5 shadow-2xl ${
      theme === "dark"
        ? "bg-zinc-950/95 border-zinc-800 text-[#F4F2EC]"
        : "bg-[#F4F2EC]/95 border-[#DECC9F] text-[#0E3746]"
    }`}>
      <div className="flex items-center justify-around">
        {navItems.map((item) => {
          const isActive = activeNav === item.id;
          const IconComponent = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setActiveNav(item.id)}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg text-[10px] font-bold transition active:scale-95 ${
                isActive
                  ? "bg-[#0E3746] text-[#F4F2EC] shadow-sm"
                  : theme === "dark"
                    ? "text-[#F4F2EC]/70 hover:text-[#F4F2EC]"
                    : "text-[#0E3746]/70 hover:text-[#0E3746]"
              }`}
            >
              <IconComponent className="w-4 h-4 stroke-[1.75]" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
