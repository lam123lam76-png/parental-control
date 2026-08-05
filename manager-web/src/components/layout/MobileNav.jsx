'use client';
import React from 'react'
import {
  LayoutDashboard,
  Calendar,
  AppWindow,
  Globe,
  Camera,
  History,
  Settings,
  MessageSquare
} from 'lucide-react'

export function MobileNav({ tabList = [], activeTab = 'overview', changeActiveTab }) {
  const getIcon = (id) => {
    switch (id) {
      case 'overview': return <LayoutDashboard className="w-5 h-5 stroke-[1.5]" />
      case 'usage': return <AppWindow className="w-5 h-5 stroke-[1.5]" />
      case 'schedules': return <Calendar className="w-5 h-5 stroke-[1.5]" />
      case 'chat': return <MessageSquare className="w-5 h-5 stroke-[1.5]" />
      case 'screenshots': return <Camera className="w-5 h-5 stroke-[1.5]" />
      case 'history': return <History className="w-5 h-5 stroke-[1.5]" />
      case 'black_list': return <Globe className="w-5 h-5 stroke-[1.5]" />
      case 'settings': return <Settings className="w-5 h-5 stroke-[1.5]" />
      default: return <LayoutDashboard className="w-5 h-5 stroke-[1.5]" />
    }
  }

  const safeTabList = Array.isArray(tabList) ? tabList : []

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-black/95 border-t border-zinc-800 py-2 px-2 flex items-center justify-around backdrop-blur-md">
      {(safeTabList ?? []).slice(0, 5).map(tab => {
        if (!tab || !tab.id) return null
        const isActive = activeTab === tab.id
        const labelText = typeof tab.label === 'string' ? tab.label.replace(/<[^>]*>/g, '').trim() : 'Tab'
        return (
          <button
            key={tab.id}
            onClick={() => changeActiveTab && changeActiveTab(tab.id)}
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-lg transition-colors ${
              isActive
                ? 'text-zinc-100 font-semibold'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <span>{getIcon(tab.id)}</span>
            <span className="text-[10px] font-mono tracking-tight truncate max-w-[60px]">
              {labelText}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
