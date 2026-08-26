'use client'
import React from 'react'
import {
  Shield,
  LayoutDashboard,
  Calendar,
  AppWindow,
  Globe,
  Camera,
  History,
  Settings,
  UserCheck,
  Lock,
  MessageSquare
} from 'lucide-react'

export function Sidebar({
  tabList = [],
  activeTab = 'overview',
  changeActiveTab,
  isAdmin = false,
  userRole = 'Viewer',
  setShowRoleModal
}) {
  const getIcon = (id) => {
    switch (id) {
      case 'overview': return <LayoutDashboard className="w-4 h-4 stroke-[1.5]" />
      case 'usage': return <AppWindow className="w-4 h-4 stroke-[1.5]" />
      case 'schedules': return <Calendar className="w-4 h-4 stroke-[1.5]" />
      case 'chat': return <MessageSquare className="w-4 h-4 stroke-[1.5]" />
      case 'screenshots': return <Camera className="w-4 h-4 stroke-[1.5]" />
      case 'history': return <History className="w-4 h-4 stroke-[1.5]" />
      case 'black_list': return <Globe className="w-4 h-4 stroke-[1.5]" />
      case 'settings': return <Settings className="w-4 h-4 stroke-[1.5]" />
      default: return <Shield className="w-4 h-4 stroke-[1.5]" />
    }
  }

  const safeTabList = Array.isArray(tabList) ? tabList : []

  // Normalize label: strip any leaked HTML + rename specific item
  const getLabel = (tab) => {
    let text = typeof tab.label === 'string'
      ? tab.label.replace(/<[^>]*>/g, '').trim()
      : 'Tab'
    if (text === 'Lịch học (Google Sheet)') return 'Thời gian biểu'
    return text
  }

  return (
    <aside className="hidden lg:flex fixed top-0 left-0 bottom-0 h-screen w-64 bg-black border-r border-zinc-800 p-4 flex-col justify-between shrink-0 overflow-y-auto z-30">
      <div className="space-y-6">
        {/* BRAND HEADER — text only, no logo box */}
        <div className="pb-4 border-b border-zinc-800">
          <h1 className="text-xs font-bold text-zinc-100 tracking-wider uppercase">
            PARENTAL CONTROL
          </h1>
          <p className="text-[10px] text-zinc-500 font-mono">
            Geist SaaS Console
          </p>
        </div>

        {/* NAVIGATION — full-width, left-aligned, tight spacing */}
        <nav className="flex flex-col space-y-1 w-full px-2">
          {safeTabList.map((tab) => {
            if (!tab || !tab.id) return null
            const isActive = activeTab === tab.id
            const labelText = getLabel(tab)

            return (
              <button
                key={tab.id}
                onClick={() => changeActiveTab && changeActiveTab(tab.id)}
                className={`w-full flex items-center justify-start text-left gap-2.5 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-zinc-100 text-black font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60'
                }`}
              >
                <span className={isActive ? 'text-black' : 'text-zinc-500'}>
                  {getIcon(tab.id)}
                </span>
                <span className="truncate">{labelText}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* USER ROLE FOOTER */}
      <div className="pt-4 border-t border-zinc-800 space-y-2">
        <div className="p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-900 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 truncate">
            <UserCheck className="w-4 h-4 text-zinc-400 stroke-[1.5]" />
            <span className="truncate text-zinc-300 font-mono text-xs">
              {isAdmin ? 'Admin' : (userRole || 'Viewer')}
            </span>
          </div>
          {setShowRoleModal && (
            <button
              onClick={() => setShowRoleModal(true)}
              className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-zinc-200 transition"
              title="Đổi tư cách"
            >
              <Lock className="w-3.5 h-3.5 stroke-[1.5]" />
            </button>
          )}
        </div>
      </div>
    </aside>
  )
}
