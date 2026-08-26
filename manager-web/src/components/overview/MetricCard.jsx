'use client';
import React from 'react'
import { StatusBadge } from '../ui/StatusBadge'

export function MetricCard({
  title,
  icon: Icon,
  status,
  statusLabel,
  mainValue,
  subValue,
  footerLeft,
  footerRight,
  actionButton
}) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-900 rounded-xl p-4 flex flex-col justify-between hover:border-zinc-700/80 transition-all duration-200 group">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-mono font-medium text-zinc-500 uppercase tracking-wider">{title}</span>
        {Icon && <Icon className="w-4 h-4 text-zinc-500 stroke-[1.5] group-hover:text-zinc-300 transition-colors" />}
      </div>

      {/* BODY */}
      <div className="space-y-1 my-1">
        {status ? (
          <StatusBadge status={status} label={statusLabel} />
        ) : (
          <div className="text-xl font-bold text-zinc-100 font-mono tracking-tight">{mainValue}</div>
        )}
        {subValue && <div className="text-xs text-zinc-400 font-mono">{subValue}</div>}
      </div>

      {/* FOOTER */}
      {(footerLeft || footerRight || actionButton) && (
        <div className="mt-3 pt-2.5 border-t border-zinc-800/80 text-[11px] font-mono text-zinc-500 flex items-center justify-between gap-2">
          <span className="truncate">{footerLeft}</span>
          {footerRight && <span>{footerRight}</span>}
          {actionButton}
        </div>
      )}
    </div>
  )
}
