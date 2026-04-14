import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, CheckCircle } from 'lucide-react'
import { getSettings, updateSettings, Settings } from '../api'

const PROVIDERS = ['GoogleGenAI', 'OpenAI', 'Anthropic', 'DeepSeek', 'ZhipuAI', 'Ollama']

export default function SettingsPage() {
  const qc = useQueryClient()
  const { data: remote } = useQuery({ queryKey: ['settings'], queryFn: getSettings })
  const [form, setForm] = useState<Partial<Settings>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (remote) setForm(remote)
  }, [remote])

  const mut = useMutation({
    mutationFn: updateSettings,
    onSuccess: (data) => {
      qc.setQueryData(['settings'], data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  const set = (key: keyof Settings, value: string | number) =>
    setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Exclude API key fields that are empty or still show a masked value (****) —
    // those should not overwrite the stored key.
    const API_KEY_FIELDS: (keyof Settings)[] = [
      'google_api_key', 'openai_api_key', 'anthropic_api_key',
      'deepseek_api_key', 'zhipu_api_key',
    ]
    const payload: Partial<Settings> = { ...form }
    for (const key of API_KEY_FIELDS) {
      const val = payload[key] as string | undefined
      if (!val || val.includes('****')) delete payload[key]
    }
    mut.mutate(payload)
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-1">Settings</h1>
      <p className="text-sm text-gray-400 mb-6">Configure LLM providers and defaults</p>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Default provider */}
        <Section title="Default Provider">
          <Field label="Provider">
            <select
              value={form.default_provider || ''}
              onChange={(e) => set('default_provider', e.target.value)}
              className={selectClass}
            >
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Max Steps">
            <input
              type="number"
              min={1}
              max={100}
              value={form.max_steps ?? 15}
              onChange={(e) => set('max_steps', Number(e.target.value))}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* Google / Gemini */}
        <Section title="Google Gemini">
          <Field label="API Key">
            <input
              type="password"
              placeholder={form.google_api_key || 'Enter API key…'}
              onChange={(e) => set('google_api_key', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.gemini_model || ''}
              onChange={(e) => set('gemini_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* OpenAI */}
        <Section title="OpenAI">
          <Field label="API Key">
            <input
              type="password"
              placeholder={form.openai_api_key || 'Enter API key…'}
              onChange={(e) => set('openai_api_key', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.openai_model || ''}
              onChange={(e) => set('openai_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* Anthropic */}
        <Section title="Anthropic">
          <Field label="API Key">
            <input
              type="password"
              placeholder={form.anthropic_api_key || 'Enter API key…'}
              onChange={(e) => set('anthropic_api_key', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.anthropic_model || ''}
              onChange={(e) => set('anthropic_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* DeepSeek */}
        <Section title="DeepSeek">
          <Field label="API Key">
            <input
              type="password"
              placeholder={form.deepseek_api_key || 'Enter API key…'}
              onChange={(e) => set('deepseek_api_key', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.deepseek_model || ''}
              onChange={(e) => set('deepseek_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* ZhipuAI */}
        <Section title="ZhipuAI">
          <Field label="API Key">
            <input
              type="password"
              placeholder={form.zhipu_api_key || 'Enter API key…'}
              onChange={(e) => set('zhipu_api_key', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.zhipu_model || ''}
              onChange={(e) => set('zhipu_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {/* Ollama */}
        <Section title="Ollama (local)">
          <Field label="Base URL">
            <input
              type="text"
              value={form.ollama_base_url || ''}
              onChange={(e) => set('ollama_base_url', e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Model">
            <input
              type="text"
              value={form.ollama_model || ''}
              onChange={(e) => set('ollama_model', e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={mut.isPending}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {saved ? (
              <><CheckCircle size={15} className="text-green-300" /> Saved</>
            ) : (
              <><Save size={15} /> Save Settings</>
            )}
          </button>
          {mut.isError && (
            <span className="text-sm text-red-400">{String(mut.error)}</span>
          )}
        </div>
      </form>
    </div>
  )
}

const inputClass =
  'w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500'
const selectClass =
  'w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-4">{children}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      {children}
    </div>
  )
}
