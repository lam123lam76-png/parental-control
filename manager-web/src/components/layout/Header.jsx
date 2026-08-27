'use client';
import React from 'react'
import { Search, Lock, PauseCircle, PlayCircle, RefreshCw, KeyRound } from 'lucide-react'
import { StatusBadge } from '../ui/StatusBadge'
import { Button } from '../ui/Button'

export function Header({
  device,
  isPaused,
  isAdmin,
  togglePauseLoading,
  updateSending,
  handleTogglePauseControl,
  triggerForceAgentUpdate,
  setIsAdmin,
  setShowLoginModal,
  searchQuery,
  setSearchQuery
}) {
  const getDeviceStatus = () => {
    if (isPaused) return 'paused'
    if (device?.is_online) return 'ready'
    return 'blocked'
  }

  // Origin / backend indicator: which server is serving this page (for monitoring)
  const host = typeof window !== 'undefined' ? window.location.hostname : '';
  const isLocal = ['localhost', '127.0.0.1', '::1'].includes(host);
  const sourceLabel = isLocal ? 'Local' : 'Cloud (Vercel)';

  return (
    <>
    <header className="bg-black/90 border-b border-zinc-800 px-5 py-3 sticky top-0 z-20 backdrop-blur-md flex items-center justify-between gap-4">
      {/* SEARCH INPUT (/ Find) */}
      <div className="relative flex-grow max-w-xs">
        <div className="absolute left-2.5 top-2 text-zinc-500 pointer-events-none">
          <Search className="w-3.5 h-3.5 stroke-[1.5]" />
        </div>
        <input
          type="text"
          value={searchQuery || ''}
          onChange={(e) => setSearchQuery && setSearchQuery(e.target.value)}
          placeholder="/ Find command or process..."
          className="w-full bg-zinc-900 border border-zinc-900 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 font-mono focus:outline-none focus:border-zinc-700 transition"
        />
      </div>

      {/* RIGHT CONTROLS & STATUS BADGE */}
      <div className="flex items-center gap-3">
        <StatusBadge
          status={getDeviceStatus()}
          label={isPaused ? 'Paused' : (device?.is_online ? 'Ready' : 'Offline')}
          className="hidden sm:inline-flex"
        />

        {isAdmin && (
          <>
            <Button
              variant={isPaused ? 'primary' : 'ghost'}
              size="sm"
              disabled={togglePauseLoading}
              onClick={handleTogglePauseControl}
            >
              {isPaused ? <PlayCircle className="w-3.5 h-3.5 stroke-[1.5]" /> : <PauseCircle className="w-3.5 h-3.5 stroke-[1.5]" />}
              <span>{isPaused ? 'Resume' : 'Pause'}</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              disabled={updateSending}
              onClick={triggerForceAgentUpdate}
            >
              <RefreshCw className={`w-3.5 h-3.5 stroke-[1.5] ${updateSending ? 'animate-spin' : ''}`} />
              <span className="hidden md:inline">Update Agent</span>
            </Button>
          </>
        )}

        {isAdmin ? (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setIsAdmin(false)}
            title="Đăng xuất Admin"
          >
            <Lock className="w-3.5 h-3.5 stroke-[1.5]" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLoginModal(true)}
          >
            <KeyRound className="w-3.5 h-3.5 stroke-[1.5]" />
            <span>Admin PIN</span>
          </Button>
        )}
      </div>
    </header>
    {/* Origin / backend indicator line */}
    <div className="bg-black/60 px-5 py-1 text-[10px] font-mono text-zinc-500 border-b border-zinc-800 flex items-center gap-2">
      <span className={isLocal ? "text-emerald-400" : (isVercel ? "text-sky-400" : "text-zinc-400")}>●</span>
      <span>Nguồn: <b className="text-zinc-300">{sourceLabel}</b></span>
      <span className="opacity-60">{host || 'localhost'}</span>
      <span className="opacity-40">·</span>
      <span>DB: <b className="text-zinc-300">Supabase</b></span>
      <span className="ml-auto opacity-60">{typeof window !== 'undefined' ? window.location.origin : ''}</span>
    </div>
    </>
  )
}
