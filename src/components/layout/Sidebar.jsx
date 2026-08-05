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
      case 'overview': return <LayoutDashboard className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'usage': return <AppWindow className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'schedules': return <Calendar className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'chat': return <MessageSquare className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'screenshots': return <Camera className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'history': return <History className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'black_list': return <Globe className="w-4 h-4 stroke-[1.5] shrink-0" />
      case 'settings': return <Settings className="w-4 h-4 stroke-[1.5] shrink-0" />
      default: return <Shield className="w-4 h-4 stroke-[1.5] shrink-0" />
    }
  }

  const safeTabList = Array.isArray(tabList) ? tabList : []

  return (
    <aside className="hidden lg:flex w-64 bg-black border-r border-zinc-800/80 p-3 flex-col justify-between shrink-0 sticky top-0 h-screen z-30 select-none">
      <div className="space-y-4">
        {/* BRAND HEADER (THU GỌN - BỎ LOGO KHUNG VUÔNG) */}
        <div className="px-3 py-2 border-b border-zinc-800/80">
          <h1 className="text-xs font-bold text-zinc-100 tracking-wider uppercase font-mono">PARENTAL CONTROL</h1>
          <p className="text-[10px] text-zinc-500 font-mono mt-0.5">Geist SaaS Console</p>
        </div>

        {/* NAVIGATION TABS (GIÓNG HÀNG THẲNG LỀ TRÁI 100%) */}
        <nav className="flex flex-col space-y-1 w-full">
          {(safeTabList ?? []).map(tab => {
            if (!tab || !tab.id) return null
            const isActive = activeTab === tab.id
            const rawLabel = typeof tab.label === 'string' ? tab.label.replace(/<[^>]*>/g, '').trim() : 'Tab'
            const displayLabel = rawLabel.includes('Google Sheet') ? 'Thời gian biểu' : rawLabel

            return (
              <button
                key={tab.id}
                onClick={() => changeActiveTab && changeActiveTab(tab.id)}
                className={`w-full flex items-center justify-start text-left px-3 py-2 text-xs font-medium rounded-md transition-colors gap-2.5 ${
                  isActive
                    ? 'bg-zinc-100 text-black font-semibold shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60'
                }`}
              >
                <span className={isActive ? 'text-black' : 'text-zinc-400'}>
                  {getIcon(tab.id)}
                </span>
                <span className="truncate">{displayLabel}</span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* USER ROLE FOOTER */}
      <div className="pt-3 border-t border-zinc-800/80">
        <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 truncate">
            <UserCheck className="w-4 h-4 text-zinc-400 stroke-[1.5] shrink-0" />
            <span className="truncate text-zinc-300 font-mono text-xs">{isAdmin ? 'Admin' : (userRole || 'Viewer')}</span>
          </div>
          {setShowRoleModal && (
            <button
              onClick={() => setShowRoleModal(true)}
              className="p-1 hover:bg-zinc-900 rounded text-zinc-500 hover:text-zinc-200 transition"
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
