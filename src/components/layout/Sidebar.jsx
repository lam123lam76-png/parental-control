'use client';
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

  return (
    <aside className="hidden lg:flex w-64 bg-black border-r border-zinc-800 p-4 flex-col justify-between shrink-0 sticky top-0 h-screen z-30">
      <div className="space-y-6">
        {/* BRAND HEADER */}
        <div className="flex items-center gap-2.5 pb-4 border-b border-zinc-800">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-100">
            <Shield className="w-4 h-4 text-zinc-100 stroke-[1.5]" />
          </div>
          <div>
            <h1 className="text-xs font-mono font-bold tracking-wider text-zinc-100 uppercase">PARENTAL CONTROL</h1>
            <p className="text-[10px] font-mono text-zinc-500">Geist SaaS Console</p>
          </div>
        </div>

        {/* NAVIGATION TABS WITH PURE STRING LABELS */}
        <nav className="space-y-1">
          {(safeTabList ?? []).map(tab => {
            if (!tab || !tab.id) return null
            const isActive = activeTab === tab.id
            const labelText = typeof tab.label === 'string' ? tab.label.replace(/<[^>]*>/g, '').trim() : 'Tab'
            return (
              <button
                key={tab.id}
                onClick={() => changeActiveTab && changeActiveTab(tab.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-zinc-100 text-black font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60'
                }`}
              >
                <span className={isActive ? 'text-black' : 'text-zinc-500 group-hover:text-zinc-200'}>
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
        <div className="p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 truncate">
            <UserCheck className="w-4 h-4 text-zinc-400 stroke-[1.5]" />
            <span className="truncate text-zinc-300 font-mono text-xs">{isAdmin ? 'Admin' : (userRole || 'Viewer')}</span>
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
