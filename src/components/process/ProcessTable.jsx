'use client';
import React from 'react'
import { Cpu, HardDrive } from 'lucide-react'

export function ProcessTable({ processes = [] }) {
  const safeProcesses = Array.isArray(processes) ? processes : []

  if (safeProcesses.length === 0) {
    return (
      <div className="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-900/30 border border-zinc-800 rounded-xl">
        No active process logs recorded.
      </div>
    )
  }

  return (
    <div className="hidden lg:block border border-zinc-800 rounded-xl overflow-hidden bg-black/40">
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500 font-mono text-[11px] uppercase tracking-wider bg-zinc-900/50">
            <th className="py-2.5 px-4 font-medium">PID</th>
            <th className="py-2.5 px-4 font-medium">Process Name</th>
            <th className="py-2.5 px-4 font-medium">CPU %</th>
            <th className="py-2.5 px-4 font-medium">Memory (MB)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60">
          {(safeProcesses ?? []).map((proc, idx) => {
            if (!proc) return null
            const pidVal = proc?.pid ?? 'N/A'
            const procName = proc?.process_name ?? 'Unknown'
            const cpuVal = proc?.cpu_percent ? `${proc.cpu_percent}%` : '0%'
            const memVal = proc?.memory_mb ? `${proc.memory_mb} MB` : '0 MB'
            return (
              <tr key={`${pidVal}_${idx}`} className="hover:bg-zinc-900/60 transition-colors">
                <td className="py-2 px-4 font-mono text-zinc-400 text-xs">{pidVal}</td>
                <td className="py-2 px-4 font-mono text-zinc-100 text-xs font-medium">{procName}</td>
                <td className="py-2 px-4 text-zinc-400 font-mono">
                  <span className="inline-flex items-center gap-1">
                    <Cpu className="w-3 h-3 text-zinc-500 stroke-[1.5]" />
                    {cpuVal}
                  </span>
                </td>
                <td className="py-2 px-4 text-zinc-400 font-mono">
                  <span className="inline-flex items-center gap-1">
                    <HardDrive className="w-3 h-3 text-zinc-500 stroke-[1.5]" />
                    {memVal}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
