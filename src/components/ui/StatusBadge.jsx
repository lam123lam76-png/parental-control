'use client';
import React from 'react'

export function StatusBadge({ status = 'ready', label, className = '' }) {
  let dotColor = 'bg-emerald-500'
  let textColor = 'text-emerald-400'
  let badgeBg = 'bg-emerald-500/10'
  let borderStyle = 'border-emerald-500/20'
  let defaultLabel = 'Ready'
  let isPingable = true

  if (status === 'paused' || status === 'warning' || status === 'limited') {
    dotColor = 'bg-amber-500'
    textColor = 'text-amber-400'
    badgeBg = 'bg-amber-500/10'
    borderStyle = 'border-amber-500/20'
    defaultLabel = 'Paused'
  } else if (status === 'blocked' || status === 'danger' || status === 'offline' || status === 'forbidden') {
    dotColor = 'bg-rose-500'
    textColor = 'text-rose-400'
    badgeBg = 'bg-rose-500/10'
    borderStyle = 'border-rose-500/20'
    defaultLabel = 'Blocked'
    isPingable = false
  }

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border ${badgeBg} ${borderStyle} font-mono text-xs ${className}`}>
      <span className="relative flex h-2 w-2">
        {isPingable && (
          <span className={`status-ping absolute inline-flex h-full w-full rounded-full ${dotColor} opacity-75`}></span>
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor}`}></span>
      </span>
      <span className={`font-mono text-xs font-medium ${textColor}`}>
        {label || defaultLabel}
      </span>
    </div>
  )
}
