'use client';
import React from 'react'
import { Clock, CheckCircle2, Circle, Trash2 } from 'lucide-react'
import { StatusBadge } from '../ui/StatusBadge'
import { Button } from '../ui/Button'

export function ScheduleCardList({
  tasks = [],
  completedTasksMap = {},
  onToggleComplete,
  onDeleteTask
}) {
  const safeTasks = Array.isArray(tasks) ? tasks : []

  if (safeTasks.length === 0) {
    return (
      <div className="lg:hidden p-4 text-center text-xs font-mono text-zinc-500 bg-zinc-900/30 border border-zinc-800 rounded-xl">
        Chưa có lịch trình hay công việc nào.
      </div>
    )
  }

  return (
    <div className="lg:hidden flex flex-col gap-2.5">
      {(safeTasks ?? []).map((task, idx) => {
        if (!task) return null
        const taskId = task?.id ?? `task_${idx}`
        const isCompleted = !!(completedTasksMap && completedTasksMap[taskId])
        const taskTitle = task?.title ?? task?.content ?? 'Công việc'
        const taskTime = task?.sessionTime ?? task?.time ?? 'Cả ngày'
        const taskPriority = task?.priorityLabel ?? (task?.isDaily ? 'Hằng ngày' : 'Bình thường')

        return (
          <div
            key={taskId}
            className="p-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-2.5"
          >
            {/* DÒNG 1: STATUS BADGE + KHUNG GIỜ */}
            <div className="flex items-center justify-between text-xs">
              <StatusBadge
                status={isCompleted ? 'ready' : 'warning'}
                label={isCompleted ? 'Hoàn thành' : 'Đang chờ'}
              />
              <span className="inline-flex items-center gap-1 font-mono text-[11px] text-zinc-400">
                <Clock className="w-3 h-3 text-zinc-500 stroke-[1.5]" />
                {taskTime}
              </span>
            </div>

            {/* DÒNG 2: NỘI DUNG CÔNG VIỆC TỰ DO XUỐNG DÒNG */}
            <div
              onClick={() => onToggleComplete && onToggleComplete(taskId)}
              className={`flex items-start gap-2 cursor-pointer ${isCompleted ? 'line-through text-zinc-500' : 'text-zinc-100'}`}
            >
              <span className="mt-0.5 shrink-0 text-zinc-400">
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 stroke-[1.5]" />
                ) : (
                  <Circle className="w-4 h-4 stroke-[1.5]" />
                )}
              </span>
              <p className="text-xs leading-relaxed font-sans break-words font-medium">
                {taskTitle}
              </p>
            </div>

            {/* DÒNG 3: PRIORITY BADGE + ACTIONS */}
            <div className="flex items-center justify-between pt-2 border-t border-zinc-800/60">
              <span className="rounded-full px-2.5 py-0.5 text-[10px] font-mono font-medium border border-white/10 bg-white/5 text-zinc-300">
                {taskPriority}
              </span>
              
              {onDeleteTask && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => onDeleteTask(taskId)}
                  title="Xóa công việc"
                >
                  <Trash2 className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>Xóa</span>
                </Button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
