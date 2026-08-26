'use client';
import React from 'react'
import { ShieldCheck, Save } from 'lucide-react'
import { Button } from '../ui/Button'

export function PermissionMatrix({
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
    <div className="space-y-6">
      {/* DESKTOP NEAT MATRIX TABLE */}
      <div className="hidden lg:block border border-zinc-800 rounded-xl overflow-hidden bg-black/40">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-500 font-mono text-[11px] uppercase tracking-wider bg-zinc-900/50">
              <th className="py-3 px-4 font-medium sticky left-0 bg-zinc-900 border-r border-zinc-800 w-52">Chức Năng / Tab</th>
              {(safeRoles ?? []).map(role => (
                <th key={role} className="py-3 px-4 font-medium text-center border-r border-zinc-800/80">
                  {role}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60">
            {(safeTabs ?? []).map(tab => {
              if (!tab || !tab.id) return null
              return (
                <tr key={tab.id} className="hover:bg-zinc-900/60 transition-colors">
                  <td className="py-2.5 px-4 font-semibold text-zinc-200 sticky left-0 bg-black/90 border-r border-zinc-800">
                    {tab?.label ?? tab.id}
                  </td>
                  {(safeRoles ?? []).map(role => {
                    const currentPerm = safePerms?.[role]?.[tab.id] ?? 'full'
                    return (
                      <td key={`${role}_${tab.id}`} className="py-2.5 px-4 text-center border-r border-zinc-800/60">
                        <select
                          value={currentPerm}
                          onChange={(e) => onSetPermission && onSetPermission(role, tab.id, e.target.value)}
                          className="bg-zinc-900 border border-zinc-900 rounded-md px-2.5 py-1 text-xs font-mono text-zinc-200 outline-none focus:border-zinc-600 transition"
                        >
                          {(permOptions ?? []).map(opt => (
                            <option key={opt.value} value={opt.value} className="bg-zinc-900 text-zinc-200">
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* VERCEL STICKY WHITE ACTION BAR */}
      <div className="sticky bottom-4 left-0 right-0 z-40 bg-zinc-900/90 border border-zinc-900 backdrop-blur-md rounded-xl p-3 flex items-center justify-between shadow-2xl">
        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <ShieldCheck className="w-4 h-4 text-zinc-200 stroke-[1.5]" />
          <span>Quyền hạn sẽ được áp dụng ngay sau khi lưu.</span>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={onSaveConfig}
        >
          <Save className="w-4 h-4 stroke-[1.5]" />
          <span>Lưu Cấu Hình Ma Trận</span>
        </Button>
      </div>
    </div>
  )
}
