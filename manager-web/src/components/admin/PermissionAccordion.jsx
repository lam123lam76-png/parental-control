'use client';
import React from 'react'
import { Save } from 'lucide-react'
import { Button } from '../ui/Button'

export function PermissionAccordion({
  customRoles = [],
  rolePermissions = {},
  tabList = [],
  onSetPermission,
  onSaveConfig
}) {
  const permOptions = [
    { value: 'full', label: 'Toàn quyền' },
    { value: 'read', label: 'Chỉ xem' },
    { value: 'none', label: 'Cấm truy cập' }
  ]

  const safeRoles = Array.isArray(customRoles) ? customRoles : []
  const safeTabs = Array.isArray(tabList) ? tabList : []
  const safePerms = rolePermissions && typeof rolePermissions === 'object' ? rolePermissions : {}

  return (
    <div className="lg:hidden flex flex-col gap-3">
      {(safeRoles ?? []).map(role => (
        <div key={role} className="p-3.5 bg-zinc-900/50 border border-zinc-900 rounded-xl space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
            <span className="font-mono text-xs font-bold text-zinc-100 uppercase">{role}</span>
            <span className="text-[10px] font-mono text-zinc-500">Phân quyền tab</span>
          </div>

          <div className="space-y-2">
            {(safeTabs ?? []).map(tab => {
              if (!tab || !tab.id) return null
              const currentPerm = safePerms?.[role]?.[tab.id] ?? 'full'
              return (
                <div key={tab.id} className="flex items-center justify-between text-xs py-1">
                  <span className="text-zinc-300 font-medium">{tab?.label ?? tab.id}</span>
                  <select
                    value={currentPerm}
                    onChange={(e) => onSetPermission && onSetPermission(role, tab.id, e.target.value)}
                    className="bg-zinc-900 border border-zinc-900 rounded-md px-2 py-1 text-xs font-mono text-zinc-200 outline-none"
                  >
                    {(permOptions ?? []).map(opt => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* MOBILE STICKY SAVE BAR */}
      <div className="sticky bottom-16 left-0 right-0 z-40 bg-zinc-900/95 border border-zinc-900 backdrop-blur-md rounded-xl p-3 flex items-center justify-between shadow-2xl mt-4">
        <span className="text-[11px] font-mono text-zinc-400">Lưu ma trận quyền</span>
        <Button variant="primary" size="sm" onClick={onSaveConfig}>
          <Save className="w-3.5 h-3.5 stroke-[1.5]" />
          <span>Lưu ngay</span>
        </Button>
      </div>
    </div>
  )
}
