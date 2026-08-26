'use client';
import React from 'react'
import { Clock, CheckCircle2, Circle, Trash2 } from 'lucide-react'
import { Button } from '../ui/Button'

export function ScheduleTable({
  tasks = [],
  completedTasksMap = {},
  onToggleComplete,
  onDeleteTask
}) {
  const safeTasks = Array.isArray(tasks) ? tasks : []

  if (safeTasks.length === 0) {
    return (
      <div className="p-8 text-center text-xs font-mono text-zinc-500 bg-zinc-900/30 border border-zinc-900 rounded-xl">
        Chưa có lịch trình hay công việc nào.
      </div>
    )
  }

  return (
    <div className="hidden lg:block border border-zinc-800 rounded-xl overflow-hidden bg-black/40">
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="border-b border-zinc-800 text-zinc-500 font-mono text-[11px] uppercase tracking-wider bg-zinc-900/50">
            <th className="py-2.5 px-4 font-medium w-10">#</th>
            <th className="py-2.5 px-4 font-medium w-44">Buổi / Khung giờ</th>
            <th className="py-2.5 px-4 font-medium">Nội dung công việc</th>
            <th className="py-2.5 px-4 font-medium w-32">Mức ưu tiên</th>
            <th className="py-2.5 px-4 font-medium w-24 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/60">
          {(safeTasks ?? []).map((task, idx) => {
            if (!task) return null
            const taskId = task?.id ?? `task_${idx}`
            const isCompleted = !!(completedTasksMap && completedTasksMap[taskId])
            const taskTitle = task?.title ?? task?.content ?? 'Công việc'
            const taskTime = task?.sessionTime ?? task?.time ?? 'Cả ngày'
            const taskPriority = task?.priorityLabel ?? (task?.isDaily ? 'Hằng ngày' : 'Bình thường')

            return (
              <tr key={taskId} className="hover:bg-zinc-900/60 transition-colors">
                <td className="py-2.5 px-4">
                  <button
                    onClick={() => onToggleComplete && onToggleComplete(taskId)}
                    className="text-zinc-500 hover:text-zinc-200 transition"
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 stroke-[1.5]" />
                    ) : (
                      <Circle className="w-4 h-4 stroke-[1.5]" />
                    )}
                  </button>
                </td>
                <td className="py-2.5 px-4 font-mono text-zinc-300">
                  <span className="inline-flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-zinc-500 stroke-[1.5]" />
                    {taskTime}
                  </span>
                </td>
                <td className={`py-2.5 px-4 text-zinc-100 ${isCompleted ? 'line-through text-zinc-500' : ''}`}>
                  {taskTitle}
                </td>
                <td className="py-2.5 px-4">
                  <span className="rounded-full px-2.5 py-0.5 text-[11px] font-mono font-medium border border-white/10 bg-white/5 text-zinc-300">
                    {taskPriority}
                  </span>
                </td>
                <td className="py-2.5 px-4 text-right">
                  {onDeleteTask && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => onDeleteTask(taskId)}
                      title="Xóa công việc"
                    >
                      <Trash2 className="w-3.5 h-3.5 stroke-[1.5]" />
                    </Button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
