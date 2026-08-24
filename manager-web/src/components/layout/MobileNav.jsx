'use client';
import React from 'react'
import {
  LayoutDashboard,
  CheckSquare,
  Calendar,
  MessageSquare,
  Sparkles,
  Activity,
  Camera,
  Settings,
  History,
  Globe,
  Shield
} from 'lucide-react'

export function MobileNav({ tabList = [], activeTab = 'overview', changeActiveTab }) {
  const getIcon = (id) => {
    switch (id) {
      case 'overview': return <LayoutDashboard className="w-5 h-5 stroke-[1.8]" />
      case 'todo': return <CheckSquare className="w-5 h-5 stroke-[1.8]" />
      case 'calendar': return <Calendar className="w-5 h-5 stroke-[1.8]" />
      case 'chat': return <MessageSquare className="w-5 h-5 stroke-[1.8]" />
      case 'ai_analysis': return <Sparkles className="w-5 h-5 text-indigo-400 stroke-[1.8]" />
      case 'app_usage': return <Activity className="w-5 h-5 stroke-[1.8]" />
      case 'screenshots': return <Camera className="w-5 h-5 stroke-[1.8]" />
      case 'config': return <Settings className="w-5 h-5 stroke-[1.8]" />
      case 'history': return <History className="w-5 h-5 stroke-[1.8]" />
      case 'black_list': return <Globe className="w-5 h-5 stroke-[1.8]" />
      default: return <Shield className="w-5 h-5 stroke-[1.8]" />
    }
  }

  const safeTabList = Array.isArray(tabList) ? tabList : []

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-black/95 border-t border-zinc-800 py-1.5 px-2 flex items-center gap-1 overflow-x-auto backdrop-blur-md selection:bg-zinc-800">
      {safeTabList.map(tab => {
        if (!tab || !tab.id) return null
        const isActive = activeTab === tab.id
        const labelText = typeof tab.label === 'string' ? tab.label.replace(/<[^>]*>/g, '').trim() : 'Tab'
        return (
          <button
            key={tab.id}
            onClick={() => changeActiveTab && changeActiveTab(tab.id)}
            className={`flex flex-col items-center justify-center gap-1 py-1.5 px-3 rounded-xl transition-all shrink-0 min-w-[64px] ${
              isActive
                ? 'bg-zinc-800/80 text-white font-bold border border-zinc-700/60 shadow'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
            }`}
          >
            <span>{getIcon(tab.id)}</span>
            <span className="text-[10px] font-medium tracking-tight truncate max-w-[72px]">
              {labelText}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
