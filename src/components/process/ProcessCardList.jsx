'use client';
import React from 'react'
import { Cpu, HardDrive, Terminal } from 'lucide-react'
import { StatusBadge } from '../ui/StatusBadge'

export function ProcessCardList({ processes = [] }) {
  const safeProcesses = Array.isArray(processes) ? processes : []

  if (safeProcesses.length === 0) {
    return (
      <div className="lg:hidden p-4 text-center text-xs font-mono text-zinc-500 bg-zinc-900/30 border border-zinc-800 rounded-xl">
        No active process logs recorded.
      </div>
    )
  }

  return (
    <div className="lg:hidden flex flex-col gap-2.5">
      {(safeProcesses ?? []).map((proc, idx) => {
        if (!proc) return null
        const pidVal = proc?.pid ?? 'N/A'
        const procName = proc?.process_name ?? 'Unknown'
        const cpuVal = proc?.cpu_percent ? `${proc.cpu_percent}%` : '0%'
        const memVal = proc?.memory_mb ? `${proc.memory_mb} MB` : '0 MB'
        return (
          <div
            key={`m_proc_${pidVal}_${idx}`}
            className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-2"
          >
            {/* DÒNG 1: STATUS BADGE + PID */}
            <div className="flex items-center justify-between text-xs">
              <StatusBadge status="ready" label="Running" />
              <span className="font-mono text-xs text-zinc-500">PID: {pidVal}</span>
            </div>

            {/* DÒNG 2: PROCESS NAME FULL TEXT */}
            <div className="flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-zinc-500 stroke-[1.5] shrink-0" />
              <span className="font-mono text-xs text-zinc-100 font-semibold break-all">
                {procName}
              </span>
            </div>

            {/* DÒNG 3: CPU & MEMORY BADGES */}
            <div className="flex items-center gap-3 pt-1 border-t border-zinc-800/60 text-[11px] font-mono text-zinc-400">
              <span className="inline-flex items-center gap-1">
                <Cpu className="w-3 h-3 text-zinc-500 stroke-[1.5]" />
                {cpuVal}
              </span>
              <span className="inline-flex items-center gap-1">
                <HardDrive className="w-3 h-3 text-zinc-500 stroke-[1.5]" />
                {memVal}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
