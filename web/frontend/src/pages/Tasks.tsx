import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle, XCircle, Clock, Loader2, ChevronRight, ArrowLeft } from 'lucide-react'
import { getTasks, getTask, getTaskLogs, Task } from '../api'
import TaskLogStream from '../components/TaskLogStream'

const STATUS_ICON = {
  done: <CheckCircle size={15} className="text-green-400" />,
  error: <XCircle size={15} className="text-red-400" />,
  running: <Loader2 size={15} className="text-blue-400 animate-spin" />,
  pending: <Clock size={15} className="text-gray-400" />,
}

const STATUS_BADGE = {
  done: 'bg-green-900/40 text-green-400',
  error: 'bg-red-900/40 text-red-400',
  running: 'bg-blue-900/40 text-blue-400',
  pending: 'bg-gray-800 text-gray-400',
}

export default function TasksPage() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()

  if (id) return <TaskDetail id={id} onBack={() => navigate('/tasks')} />
  return <TaskList />
}

function TaskList() {
  const navigate = useNavigate()
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
    refetchInterval: 5000,
  })

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-2xl font-bold mb-1">Task History</h1>
      <p className="text-sm text-gray-400 mb-6">All previously run tasks</p>

      {isLoading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Clock size={40} className="mx-auto mb-3 opacity-30" />
          <p>No tasks yet.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.map((t: Task) => (
            <button
              key={t.id}
              onClick={() => navigate(`/tasks/${t.id}`)}
              className="w-full text-left bg-gray-900 hover:bg-gray-800 rounded-xl border border-gray-800 p-4 flex items-center gap-3 transition-colors"
            >
              <span className="flex-shrink-0">
                {STATUS_ICON[t.status as keyof typeof STATUS_ICON] ?? STATUS_ICON.pending}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">{t.goal}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t.provider}/{t.model} · {t.steps} steps ·{' '}
                  {new Date(t.created_at).toLocaleString()}
                </p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_BADGE[t.status as keyof typeof STATUS_BADGE] ?? STATUS_BADGE.pending}`}>
                {t.status}
              </span>
              <ChevronRight size={14} className="text-gray-600" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function TaskDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const { data: task } = useQuery({
    queryKey: ['task', id],
    queryFn: () => getTask(id),
    refetchInterval: (q) =>
      q.state.data?.status === 'running' || q.state.data?.status === 'pending'
        ? 2000
        : false,
  })

  const running = task?.status === 'running' || task?.status === 'pending'

  return (
    <div className="p-6 max-w-3xl">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 mb-5 transition-colors"
      >
        <ArrowLeft size={14} /> Back
      </button>

      {!task ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : (
        <>
          <div className="flex items-start gap-3 mb-4">
            <span className="mt-0.5">{STATUS_ICON[task.status as keyof typeof STATUS_ICON]}</span>
            <div>
              <h1 className="text-xl font-bold leading-snug">{task.goal}</h1>
              <p className="text-xs text-gray-500 mt-1">
                {task.provider}/{task.model} · {task.steps} steps ·{' '}
                {new Date(task.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {task.reason && (
            <div className={`rounded-lg p-3 mb-4 text-sm ${
              task.success ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'
            }`}>
              {task.reason}
            </div>
          )}

          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-gray-800 text-xs font-medium text-gray-400 uppercase tracking-wider">
              Logs
            </div>
            <TaskLogStream taskId={id} live={running} />
          </div>
        </>
      )}
    </div>
  )
}
