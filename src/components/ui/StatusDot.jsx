'use client';
import React from 'react'

export function StatusDot({ status = 'ready', label, className = '' }) {
  let dotColor = 'bg-emerald-500'
  let textColor = 'text-emerald-400'
  let pingColor = 'bg-emerald-400'
  let defaultLabel = 'Ready'

  if (status === 'paused' || status === 'warning' || status === 'limited') {
    dotColor = 'bg-amber-500'
    textColor = 'text-amber-400'
    pingColor = 'bg-amber-400'
    defaultLabel = 'Paused'
  } else if (status === 'blocked' || status === 'danger' || status === 'offline' || status === 'forbidden') {
    dotColor = 'bg-rose-500'
    textColor = 'text-rose-400'
    pingColor = 'bg-rose-400'
    defaultLabel = 'Blocked'
  }

  const isPingable = status === 'ready' || status === 'online' || status === 'paused' || status === 'warning'

  return (
    <div className={`inline-flex items-center gap-1.5 font-mono text-xs ${className}`}>
      <span className="relative flex h-2 w-2">
        {isPingable && (
          <span className={`status-ping absolute inline-flex h-full w-full rounded-full ${pingColor} opacity-75`}></span>
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor}`}></span>
      </span>
      <span className={`font-mono text-xs font-medium ${textColor}`}>
        {label || defaultLabel}
      </span>
    </div>
  )
}
