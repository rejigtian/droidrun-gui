import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Play, Loader2 } from 'lucide-react'
import { getDevices, getSettings, createTask } from '../api'

const PROVIDERS = ['GoogleGenAI', 'OpenAI', 'Anthropic', 'DeepSeek', 'ZhipuAI', 'Ollama']

export default function NewTaskPage() {
  const navigate = useNavigate()
  const { data: devices = [] } = useQuery({ queryKey: ['devices'], queryFn: getDevices })
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  const onlineDevices = devices.filter((d) => d.status === 'online')

  const [goal, setGoal] = useState('')
  const [deviceId, setDeviceId] = useState('')
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [vision, setVision] = useState(false)
  const [reasoning, setReasoning] = useState(false)

  const effectiveProvider = provider || settings?.default_provider || 'GoogleGenAI'

  const createMut = useMutation({
    mutationFn: createTask,
    onSuccess: (task) => navigate(`/tasks/${task.id}`),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!goal.trim() || !deviceId) return
    createMut.mutate({
      goal: goal.trim(),
      device_id: deviceId,
      provider: provider || undefined,
      model: model || undefined,
      enable_vision: vision,
      enable_reasoning: reasoning,
    })
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-1">New Task</h1>
      <p className="text-sm text-gray-400 mb-6">
        Describe a task in plain language and let the AI agent execute it on your device.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Goal */}
        <Field label="Task Goal">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Open YouTube and search for 'droidrun demo'"
            rows={3}
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500 resize-none"
          />
        </Field>

        {/* Device */}
        <Field label="Target Device">
          {onlineDevices.length === 0 ? (
            <p className="text-sm text-red-400">
              No devices online. Connect a device first.
            </p>
          ) : (
            <select
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
            >
              <option value="">Select a device…</option>
              {onlineDevices.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.model || d.id})</option>
              ))}
            </select>
          )}
        </Field>

        {/* Provider + Model */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Provider">
            <select
              value={provider}
              onChange={(e) => { setProvider(e.target.value); setModel('') }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
            >
              <option value="">Default ({settings?.default_provider})</option>
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Model (optional)">
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={getDefaultModel(effectiveProvider, settings)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
            />
          </Field>
        </div>

        {/* Options */}
        <Field label="Options">
          <div className="flex gap-6">
            <Toggle label="Vision mode" checked={vision} onChange={setVision} />
            <Toggle label="Reasoning mode" checked={reasoning} onChange={setReasoning} />
          </div>
        </Field>

        <button
          type="submit"
          disabled={createMut.isPending || !goal.trim() || !deviceId}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          {createMut.isPending ? (
            <><Loader2 size={15} className="animate-spin" /> Starting…</>
          ) : (
            <><Play size={15} /> Run Task</>
          )}
        </button>

        {createMut.isError && (
          <p className="text-sm text-red-400">{String(createMut.error)}</p>
        )}
      </form>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function Toggle({ label, checked, onChange }: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div
        onClick={() => onChange(!checked)}
        className={`w-9 h-5 rounded-full transition-colors flex items-center ${
          checked ? 'bg-blue-600' : 'bg-gray-700'
        }`}
      >
        <div className={`w-4 h-4 bg-white rounded-full mx-0.5 transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`} />
      </div>
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  )
}

function getDefaultModel(provider: string, settings: any) {
  if (!settings) return ''
  const map: Record<string, string> = {
    GoogleGenAI: settings.gemini_model,
    OpenAI: settings.openai_model,
    Anthropic: settings.anthropic_model,
    DeepSeek: settings.deepseek_model,
    ZhipuAI: settings.zhipu_model,
    Ollama: settings.ollama_model,
  }
  return map[provider] || ''
}
