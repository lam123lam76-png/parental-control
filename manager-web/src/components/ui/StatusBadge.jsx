'use client';
import React from 'react';
import { cn } from '../../lib/utils';

const statusConfig = {
  online:   { dot: 'bg-green-500', ping: 'bg-green-500 animate-ping', text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', label: 'Online', pingable: true },
  ready:    { dot: 'bg-green-500', ping: 'bg-green-500 animate-ping', text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', label: 'Ready', pingable: true },
  paused:   { dot: 'bg-yellow-500', ping: 'bg-yellow-500 animate-ping', text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Paused', pingable: true },
  warning:  { dot: 'bg-yellow-500', ping: 'bg-yellow-500 animate-ping', text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Warning', pingable: true },
  limited:  { dot: 'bg-yellow-500', ping: 'bg-yellow-500 animate-ping', text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', label: 'Limited', pingable: true },
  offline:  { dot: 'bg-red-500', ping: 'hidden', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Offline', pingable: false },
  blocked:  { dot: 'bg-red-500', ping: 'hidden', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Blocked', pingable: false },
  forbidden:{ dot: 'bg-red-500', ping: 'hidden', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Forbidden', pingable: false },
  danger:   { dot: 'bg-red-500', ping: 'hidden', text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Danger', pingable: false },
};

export function StatusBadge({ status = 'ready', label, className = '' }) {
  const config = statusConfig[status] || statusConfig.ready;
  const displayLabel = label || config.label;

  return (
    <div className={cn('inline-flex items-center gap-2 px-2.5 py-1 rounded-full border font-mono text-xs', config.bg, config.border, className)}>
      <span className={cn('relative flex h-2 w-2', config.dot)}>
        {config.pingable && (
          <span className={cn('absolute inline-flex h-full w-full rounded-full opacity-75', config.ping)}></span>
        )}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', config.dot)}></span>
      </span>
      <span className={cn('font-mono text-xs font-medium', config.text)}>
        {displayLabel}
      </span>
    </div>
  );
}