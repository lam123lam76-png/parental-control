// manager-web/src/components/ui/StatusDot.jsx
'use client';
import React from 'react';
import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils';

// ============ Variants cho dot ============
const dotVariants = cva('relative flex h-2 w-2', {
  variants: {
    status: {
      ready: 'bg-green-500',
      online: 'bg-green-500',
      paused: 'bg-emerald-500',
      warning: 'bg-emerald-500',
      limited: 'bg-emerald-500',
      offline: 'bg-emerald-500',
      blocked: 'bg-emerald-500',
      forbidden: 'bg-emerald-500',
      danger: 'bg-rose-500',
    },
  },
  defaultVariants: {
    status: 'ready',
  },
});

const pingVariants = cva('absolute inline-flex h-full w-full rounded-full opacity-75', {
  variants: {
    status: {
      ready: 'bg-green-500 animate-ping',
      online: 'bg-green-500 animate-ping',
      paused: 'bg-emerald-500 animate-ping',
      warning: 'bg-emerald-500 animate-ping',
      limited: 'bg-emerald-500 animate-ping',
      offline: 'hidden',
      blocked: 'hidden',
      forbidden: 'hidden',
      danger: 'hidden',
    },
  },
  defaultVariants: {
    status: 'ready',
  },
});

// ============ Map nhãn ============
const labelMap = {
  ready: 'Ready',
  online: 'Online',
  paused: 'Paused',
  warning: 'Warning',
  limited: 'Limited',
  offline: 'Offline',
  blocked: 'Blocked',
  forbidden: 'Forbidden',
  danger: 'Danger',
};

// ============ Component chính ============
export function StatusDot({
  status = 'ready',
  label,
  className = '',
}) {
  const displayLabel = label || labelMap[status] || 'Unknown';
  const isPingable = !['offline', 'blocked', 'forbidden', 'danger'].includes(status);

  return (
    <div className={cn('inline-flex items-center gap-1.5 font-mono text-xs', className)}>
      {/* Chấm tròn */}
      <span className={cn(dotVariants({ status }))}>
        {isPingable && (
          <span className={cn(pingVariants({ status }))}></span>
        )}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', dotVariants({ status }))}></span>
      </span>

      {/* Nhãn */}
      <span className={cn('font-mono text-xs font-medium', {
        'text-green-400': ['ready', 'online'].includes(status),
        'text-emerald-400': ['paused', 'warning', 'limited'].includes(status),
        'text-emerald-400': ['offline', 'blocked', 'forbidden'].includes(status),
        'text-rose-400': ['danger'].includes(status),
      })}>
        {displayLabel}
      </span>
    </div>
  );
}