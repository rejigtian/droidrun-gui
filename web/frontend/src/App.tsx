import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { Smartphone, ListChecks, PlusCircle, Settings } from 'lucide-react'
import DevicesPage from './pages/Devices'
import TasksPage from './pages/Tasks'
import NewTaskPage from './pages/NewTask'
import SettingsPage from './pages/Settings'

const navItems = [
  { to: '/devices', label: 'Devices', icon: Smartphone },
  { to: '/tasks', label: 'History', icon: ListChecks },
  { to: '/new', label: 'New Task', icon: PlusCircle },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <nav className="w-52 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-5 py-5">
          <span className="text-lg font-bold tracking-tight">
            🤖 DroidRun
          </span>
          <span className="ml-2 text-xs text-gray-500">WebGUI</span>
        </div>
        <ul className="flex-1 space-y-1 px-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="px-5 py-4 text-xs text-gray-600">
          Self-hosted droidrun
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/devices" replace />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/tasks/:id" element={<TasksPage />} />
          <Route path="/new" element={<NewTaskPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
