'use client';
import React from 'react'

export function Button({
  variant = 'ghost', // 'primary' | 'ghost' | 'destructive'
  size = 'md',       // 'sm' | 'md' | 'lg'
  children,
  className = '',
  disabled = false,
  ...props
}) {
  let baseStyle = 'inline-flex items-center justify-center font-sans font-medium transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed'
  
  let variantStyle = 'bg-transparent text-zinc-300 hover:bg-zinc-900 hover:text-white border border-zinc-800 rounded-md'
  if (variant === 'primary') {
    variantStyle = 'bg-white text-black hover:bg-zinc-200 border border-white rounded-md shadow-sm'
  } else if (variant === 'destructive') {
    variantStyle = 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:border-rose-900/50 hover:bg-rose-950/30 hover:text-rose-400 rounded-md'
  }

  let sizeStyle = 'px-3 py-1.5 text-xs gap-1.5'
  if (size === 'sm') sizeStyle = 'px-2 py-1 text-[11px] gap-1'
  if (size === 'lg') sizeStyle = 'px-4 py-2 text-sm gap-2'

  return (
    <button
      disabled={disabled}
      className={`${baseStyle} ${variantStyle} ${sizeStyle} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
