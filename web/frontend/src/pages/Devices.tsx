import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Smartphone, Wifi, WifiOff, Plus, Trash2, Copy, CheckCheck } from 'lucide-react'
import { getDevices, deleteDevice, createToken, Device, TokenOut } from '../api'

export default function DevicesPage() {
  const qc = useQueryClient()
  const { data: devices = [], isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: getDevices,
    refetchInterval: 5000,
  })

  const [newName, setNewName] = useState('')
  const [createdToken, setCreatedToken] = useState<TokenOut | null>(null)
  const [copied, setCopied] = useState(false)
  const [showForm, setShowForm] = useState(false)

  const createMut = useMutation({
    mutationFn: (name: string) => createToken(name),
    onSuccess: (data) => {
      setCreatedToken(data)
      setNewName('')
      qc.invalidateQueries({ queryKey: ['devices'] })
    },
  })

  const deleteMut = useMutation({
    mutationFn: deleteDevice,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['devices'] }),
  })

  const handleCopy = () => {
    if (!createdToken) return
    navigator.clipboard.writeText(createdToken.token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Devices</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage devices connected via Portal app
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setCreatedToken(null) }}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm transition-colors"
        >
          <Plus size={15} /> Add Device
        </button>
      </div>

      {/* Add device form */}
      {showForm && (
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-5 mb-6">
          <h2 className="font-semibold mb-3">Generate Device Token</h2>
          {!createdToken ? (
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Device name (e.g. Pixel 7)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && createMut.mutate(newName || 'My Device')}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500"
              />
              <button
                onClick={() => createMut.mutate(newName || 'My Device')}
                disabled={createMut.isPending}
                className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors"
              >
                {createMut.isPending ? 'Generating…' : 'Generate'}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="text-gray-400 hover:text-gray-200 px-3 py-2 text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div>
              <p className="text-sm text-gray-400 mb-2">
                Copy this token and paste it into Portal app → <strong>Custom Connection</strong>.
                Set the server URL to <code className="bg-gray-800 px-1 rounded text-blue-400">ws://your-server:8000/v1/providers/join</code>
              </p>
              <div className="flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2 font-mono text-xs break-all">
                <span className="flex-1 text-green-400">{createdToken.token}</span>
                <button onClick={handleCopy} className="flex-shrink-0 text-gray-400 hover:text-white">
                  {copied ? <CheckCheck size={15} className="text-green-400" /> : <Copy size={15} />}
                </button>
              </div>
              <button
                onClick={() => { setShowForm(false); setCreatedToken(null) }}
                className="mt-3 text-sm text-gray-400 hover:text-gray-200"
              >
                Done
              </button>
            </div>
          )}
        </div>
      )}

      {/* Device list */}
      {isLoading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : devices.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Smartphone size={40} className="mx-auto mb-3 opacity-30" />
          <p>No devices registered yet.</p>
          <p className="text-xs mt-1">Add a device to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((d: Device) => (
            <DeviceCard
              key={d.id}
              device={d}
              onDelete={() => deleteMut.mutate(d.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DeviceCard({ device, onDelete }: { device: Device; onDelete: () => void }) {
  const online = device.status === 'online'
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-4">
      <div className={`p-2 rounded-lg ${online ? 'bg-green-900/40' : 'bg-gray-800'}`}>
        <Smartphone size={20} className={online ? 'text-green-400' : 'text-gray-500'} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{device.name || device.id}</span>
          <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
            online ? 'bg-green-900/50 text-green-400' : 'bg-gray-800 text-gray-500'
          }`}>
            {online ? <Wifi size={10} /> : <WifiOff size={10} />}
            {online ? 'Online' : 'Offline'}
          </span>
        </div>
        <div className="text-xs text-gray-500 mt-0.5">
          {device.model && <span className="mr-3">{device.model}</span>}
          {device.serial && <span className="mr-3">Serial: {device.serial}</span>}
          {device.last_seen && (
            <span>Last seen: {new Date(device.last_seen).toLocaleString()}</span>
          )}
        </div>
      </div>
      <button
        onClick={onDelete}
        className="text-gray-600 hover:text-red-400 transition-colors p-1"
        title="Remove device"
      >
        <Trash2 size={16} />
      </button>
    </div>
  )
}
