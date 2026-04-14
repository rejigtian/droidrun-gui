import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTaskLogs } from '../api'

interface Props {
  taskId: string
  live: boolean
}

export default function TaskLogStream({ taskId, live }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const [done, setDone] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // For completed tasks, load stored logs
  const { data: storedLogs } = useQuery({
    queryKey: ['taskLogs', taskId],
    queryFn: () => getTaskLogs(taskId),
    enabled: !live,
  })

  useEffect(() => {
    if (!live) return

    const es = new EventSource(`/api/tasks/${taskId}/stream`)

    es.onmessage = (e) => {
      const msg = e.data as string
      if (msg === '[DONE]') {
        setDone(true)
        es.close()
        return
      }
      setLines((prev) => [...prev, msg])
    }

    es.onerror = () => {
      es.close()
      setDone(true)
    }

    return () => es.close()
  }, [taskId, live])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines, storedLogs])

  const displayLines = live
    ? lines
    : (storedLogs?.map((l) => l.message) ?? [])

  return (
    <div className="h-80 overflow-y-auto p-4 font-mono text-xs leading-5">
      {displayLines.length === 0 && !done ? (
        <span className="text-gray-600">Waiting for logs…</span>
      ) : (
        displayLines.map((line, i) => (
          <div key={i} className="text-gray-300 whitespace-pre-wrap">
            {line}
          </div>
        ))
      )}
      {done && <div className="text-gray-600 mt-2">─── finished ───</div>}
      <div ref={bottomRef} />
    </div>
  )
}
