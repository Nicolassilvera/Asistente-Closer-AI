// ui/src/App.jsx
import { useState } from 'react'
import { LayoutDashboard, Users, Bell, Settings, Zap } from 'lucide-react'
import { useWebSocket } from './hooks/useWebSocket'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Seguimientos from './pages/Seguimientos'


const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'leads',     label: 'Leads',     icon: Users },
  { id: 'followups', label: 'Seguimientos', icon: Bell },
  { id: 'settings',  label: 'Ajustes',   icon: Settings },
]

export default function App() {
  const [page, setPage] = useState('dashboard')
  useWebSocket()

  return (
    <div className="flex h-screen bg-jarvis-bg overflow-hidden">

      {/* Sidebar */}
      <aside className="w-56 bg-jarvis-surface border-r border-jarvis-border
                        flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-jarvis-border">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-jarvis-purple/20 flex items-center
                            justify-center">
              <Zap size={14} className="text-jarvis-purple" />
            </div>
            <span className="font-semibold text-jarvis-text">Jarvis</span>
            <span className="text-xs text-jarvis-muted ml-auto">v1.0</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg
                         text-sm transition-colors text-left
                         ${page === id
                           ? 'bg-jarvis-purple/20 text-jarvis-purple font-medium'
                           : 'text-jarvis-muted hover:bg-jarvis-card hover:text-jarvis-text'
                         }`}>
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>

        {/* Status */}
        <div className="px-4 py-3 border-t border-jarvis-border">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
            <span className="text-xs text-jarvis-muted">Sistema activo</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {page === 'dashboard' && <Dashboard />}
        {page === 'leads'     && <Leads />}
        {page === 'followups' && <Seguimientos />}
        {page === 'settings'  && (
          <div className="p-6 text-jarvis-muted">Ajustes — próximamente</div>
        )}
      </main>
    </div>
  )
}
