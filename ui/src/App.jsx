// ui/src/App.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LayoutDashboard, Users, Bell, Settings as SettingsIcon, SearchCheck, Scale, Bot, Power,
         MessageSquareText, CalendarDays } from 'lucide-react'
import { useWebSocket } from './hooks/useWebSocket'
import { getMonitorStatus, toggleMonitor, getStats, getSettings } from './api'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Seguimientos from './pages/Seguimientos'
import LeadFinder from './pages/LeadFinder'
import Chat from './pages/Chat'
import Pizarron from './pages/Pizarron'
import Settings from './pages/Settings'

const NAV = [
  { id: 'dashboard', label: 'Dashboard',    icon: LayoutDashboard },
  { id: 'leads',     label: 'Leads',        icon: Users },
  { id: 'finder',    label: 'LeadFinder',   icon: SearchCheck },
  { id: 'followups', label: 'Seguimientos', icon: Bell },
  { id: 'chat',      label: 'Asistente IA', icon: MessageSquareText },
  { id: 'pizarron',  label: 'Pizarrón',     icon: CalendarDays },
]

export default function App() {
  const [page, setPage] = useState('dashboard')
  useWebSocket()

  const queryClient = useQueryClient()
  const { data: monitorData } = useQuery({
    queryKey: ['monitor-status'],
    queryFn: getMonitorStatus,
    refetchInterval: 15000,
  })
  const monitorOn    = monitorData?.enabled ?? true

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn:  getStats,
    refetchInterval: 30000,
  })
  const followupBadge = stats?.followups ?? 0

  const { data: appSettings } = useQuery({
    queryKey: ['settings'],
    queryFn:  getSettings,
    staleTime: 60000,
  })

  const toggleMutation = useMutation({
    mutationFn: toggleMonitor,
    onSuccess: (data) => {
      queryClient.setQueryData(['monitor-status'], data)
    },
  })

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
                {appSettings?.company_name ?? 'Jarvis CRM'}
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
              <span className="flex-1">{label}</span>
              {id === 'followups' && followupBadge > 0 && (
                <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500 text-white
                                 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                  {followupBadge > 99 ? '99+' : followupBadge}
                </span>
              )}
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
            <SettingsIcon size={16} className="flex-shrink-0" />
            Ajustes
          </button>
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-jarvis-border space-y-2.5">

          {/* Toggle monitor WhatsApp */}
          <button
            onClick={() => toggleMutation.mutate()}
            disabled={toggleMutation.isPending}
            title={monitorOn ? 'Pausar seguimiento en vivo' : 'Activar seguimiento en vivo'}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border transition-all
                        ${monitorOn
                          ? 'bg-teal-500/10 border-teal-500/25 text-teal-400 hover:bg-teal-500/20'
                          : 'bg-jarvis-surface border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80 hover:text-jarvis-text'
                        }`}>
            <Power size={13} className="flex-shrink-0" />
            <div className="flex-1 text-left min-w-0">
              <div className="text-[11px] font-semibold truncate">
                {monitorOn ? 'Seguimiento en vivo' : 'Seguimiento pausado'}
              </div>
              <div className="text-[9px] opacity-60 mt-0.5">
                {monitorOn ? 'WA monitoreado c/5 min' : 'Toca para reactivar'}
              </div>
            </div>
            {/* Pill on/off */}
            <div className={`w-7 h-3.5 rounded-full flex-shrink-0 transition-colors relative
                            ${monitorOn ? 'bg-teal-500' : 'bg-jarvis-border'}`}>
              <span className={`absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white shadow transition-all
                               ${monitorOn ? 'left-[14px]' : 'left-0.5'}`} />
            </div>
          </button>

          {/* Jarvis status */}
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
        {page === 'chat'      && <Chat />}
        {page === 'pizarron'  && <Pizarron />}
        {page === 'settings'  && <Settings />}
      </main>
    </div>
  )
}
