// ui/src/App.jsx
import { useState } from 'react'
import { LayoutDashboard, Users, Bell, Settings, SearchCheck, Scale, Bot } from 'lucide-react'
import { useWebSocket } from './hooks/useWebSocket'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Seguimientos from './pages/Seguimientos'
import LeadFinder from './pages/LeadFinder'

const NAV = [
  { id: 'dashboard', label: 'Dashboard',    icon: LayoutDashboard },
  { id: 'leads',     label: 'Leads',        icon: Users },
  { id: 'finder',    label: 'LeadFinder',   icon: SearchCheck },
  { id: 'followups', label: 'Seguimientos', icon: Bell },
]

export default function App() {
  const [page, setPage] = useState('dashboard')
  useWebSocket()

  return (
    <div className="flex h-screen bg-jarvis-bg overflow-hidden">

      {/* Sidebar */}
      <aside className="w-60 bg-jarvis-surface border-r border-jarvis-border flex flex-col flex-shrink-0">

        {/* Logo / Branding */}
        <div className="px-4 py-5 border-b border-jarvis-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#FF8C00] flex items-center justify-center flex-shrink-0 shadow-lg shadow-[#FF8C00]/20">
              <Scale size={20} className="text-white" />
            </div>
            <div className="min-w-0">
              <div className="font-heading font-bold text-sm text-jarvis-text leading-tight truncate">
                Balanzas Caballito
              </div>
              <div className="text-[10px] text-[#FF8C00] uppercase tracking-widest font-medium mt-0.5">
                CRM
              </div>
            </div>
          </div>
        </div>

        {/* Navegación */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                         transition-all duration-150 text-left
                         ${page === id
                           ? 'bg-[#FF8C00]/15 text-[#FF8C00] font-semibold border border-[#FF8C00]/25'
                           : 'text-jarvis-muted hover:bg-jarvis-card hover:text-jarvis-text border border-transparent font-medium'
                         }`}>
              <Icon size={16} className="flex-shrink-0" />
              {label}
            </button>
          ))}

          <div className="pt-3 pb-1">
            <div className="border-t border-jarvis-border" />
          </div>

          <button
            onClick={() => setPage('settings')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                       transition-all duration-150 text-left
                       ${page === 'settings'
                         ? 'bg-[#FF8C00]/15 text-[#FF8C00] font-semibold border border-[#FF8C00]/25'
                         : 'text-jarvis-muted hover:bg-jarvis-card hover:text-jarvis-text border border-transparent font-medium'
                       }`}>
            <Settings size={16} className="flex-shrink-0" />
            Ajustes
          </button>
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-jarvis-border">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <Bot size={16} className="text-jarvis-muted" />
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-teal-400 border border-jarvis-surface" />
            </div>
            <span className="text-xs text-jarvis-muted">Jarvis operativo</span>
          </div>
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="flex-1 overflow-y-auto">
        {page === 'dashboard' && <Dashboard onNavigate={setPage} />}
        {page === 'leads'     && <Leads />}
        {page === 'finder'    && <LeadFinder />}
        {page === 'followups' && <Seguimientos />}
        {page === 'settings'  && (
          <div className="p-8 text-jarvis-muted">
            <p className="font-heading font-bold text-jarvis-text text-lg">Ajustes</p>
            <p className="text-sm mt-1">Próximamente</p>
          </div>
        )}
      </main>
    </div>
  )
}
