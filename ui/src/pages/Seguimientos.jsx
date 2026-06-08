// ui/src/pages/Seguimientos.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Calendar, Phone, MessageCircle, Check, X } from 'lucide-react'
import { getFollowups, updateStatus, updateLead } from '../api'
import StatusBadge from '../components/StatusBadge'
import LeadDetail from './LeadDetail'

const PRIORITY_STYLE = {
  alta:  'text-red-400 bg-red-400/10 border-red-400/30',
  media: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
  baja:  'text-slate-400 bg-slate-400/10 border-slate-400/30',
}

export default function Seguimientos() {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState(null)

  const { data: followups = [], isLoading } = useQuery({
    queryKey: ['followups'],
    queryFn:  getFollowups,
    refetchInterval: 30000,
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['followups'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const clearFollowup = useMutation({
    mutationFn: (id) => updateLead(id, { followup_date: '' }),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['followups'] }),
  })

  if (selectedId) {
    return <LeadDetail leadId={selectedId} onBack={() => setSelectedId(null)} />
  }

  const today    = new Date().toISOString().slice(0, 10)
  const vencidos = followups.filter(l => l.followup_date < today)
  const hoy      = followups.filter(l => l.followup_date === today)
  const proximos = followups.filter(l => l.followup_date > today)

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-jarvis-text flex items-center gap-2">
            Seguimientos
          </h1>
          <p className="text-jarvis-muted text-sm mt-0.5">
            {followups.length} pendientes
            {vencidos.length > 0 && (
              <span className="ml-2 text-red-400 font-semibold">· {vencidos.length} vencidos</span>
            )}
          </p>
        </div>
        {followups.length > 0 && (
          <div className="flex items-center gap-3 text-xs">
            {vencidos.length > 0 && (
              <span className="px-3 py-1.5 rounded-full bg-red-400/10 border border-red-400/25 text-red-400 font-medium">
                {vencidos.length} vencidos
              </span>
            )}
            {hoy.length > 0 && (
              <span className="px-3 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/25 text-amber-400 font-medium">
                {hoy.length} hoy
              </span>
            )}
          </div>
        )}
      </div>

      {isLoading && <p className="text-jarvis-muted text-sm">Cargando...</p>}

      {!isLoading && followups.length === 0 && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-10 text-center">
          <div className="w-12 h-12 rounded-full bg-jarvis-surface flex items-center justify-center mx-auto mb-4">
            <Bell size={22} className="text-jarvis-muted" />
          </div>
          <p className="text-jarvis-text font-medium">Sin seguimientos pendientes</p>
          <p className="text-xs text-jarvis-muted mt-1">
            Asigná una fecha de seguimiento a tus leads desde su panel de detalle.
          </p>
        </div>
      )}

      {vencidos.length > 0 && (
        <Group title="Vencidos" titleColor="text-red-400"
          leads={vencidos} today={today}
          onSelect={setSelectedId} onStatus={statusMutation} onClear={clearFollowup} />
      )}

      {hoy.length > 0 && (
        <Group title="Para hoy" titleColor="text-amber-400"
          leads={hoy} today={today}
          onSelect={setSelectedId} onStatus={statusMutation} onClear={clearFollowup} />
      )}

      {proximos.length > 0 && (
        <Group title="Próximos" titleColor="text-jarvis-muted"
          leads={proximos} today={today}
          onSelect={setSelectedId} onStatus={statusMutation} onClear={clearFollowup} />
      )}
    </div>
  )
}

function Group({ title, titleColor, leads, today, onSelect, onStatus, onClear }) {
  return (
    <div className="space-y-2">
      <h2 className={`text-sm font-semibold ${titleColor} flex items-center gap-1.5`}>
        <Calendar size={13} /> {title}
        <span className="text-jarvis-muted font-normal ml-0.5">({leads.length})</span>
      </h2>

      <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden divide-y divide-jarvis-border/50">
        {leads.map(lead => {
          const isOverdue = lead.followup_date < today
          const isToday   = lead.followup_date === today
          return (
            <div key={lead.id}
              className="flex items-center gap-4 px-4 py-3.5 hover:bg-jarvis-surface/50
                         transition-colors cursor-pointer"
              onClick={() => onSelect(lead.id)}>

              {/* Fecha */}
              <div className="w-12 text-center flex-shrink-0">
                <div className={`text-sm font-bold leading-none
                  ${isOverdue ? 'text-red-400' : isToday ? 'text-amber-400' : 'text-jarvis-muted'}`}>
                  {lead.followup_date?.slice(8)}
                </div>
                <div className="text-[10px] text-jarvis-muted mt-0.5 uppercase">
                  {new Date(lead.followup_date + 'T12:00:00').toLocaleString('es-AR', { month: 'short' })}
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-jarvis-text truncate">
                    {lead.company_name}
                  </span>
                  {lead.priority && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-medium
                      ${PRIORITY_STYLE[lead.priority] ?? PRIORITY_STYLE.media}`}>
                      {lead.priority}
                    </span>
                  )}
                </div>
                <div className="text-xs text-jarvis-muted truncate mt-0.5">
                  {[lead.contact_name, lead.city, lead.category].filter(Boolean).join(' · ')}
                </div>
              </div>

              {/* Estado */}
              <div className="flex-shrink-0">
                <StatusBadge status={lead.lead_status} />
              </div>

              {/* Acciones */}
              <div className="flex items-center gap-0.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
                {lead.whatsapp && (
                  <a href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                    target="_blank" rel="noreferrer"
                    className="p-1.5 rounded-lg hover:bg-green-400/10 text-jarvis-muted hover:text-green-400 transition-colors">
                    <MessageCircle size={13} />
                  </a>
                )}
                {lead.phone && (
                  <a href={`tel:${lead.phone}`}
                    className="p-1.5 rounded-lg hover:bg-teal-400/10 text-jarvis-muted hover:text-teal-400 transition-colors">
                    <Phone size={13} />
                  </a>
                )}
                <button
                  onClick={() => onStatus.mutate({ id: lead.id, status: 'contactado' })}
                  title="Marcar contactado"
                  className="p-1.5 rounded-lg hover:bg-green-400/10 text-jarvis-muted hover:text-green-400 transition-colors">
                  <Check size={13} />
                </button>
                <button
                  onClick={() => onClear.mutate(lead.id)}
                  title="Quitar seguimiento"
                  className="p-1.5 rounded-lg hover:bg-red-400/10 text-jarvis-muted hover:text-red-400 transition-colors">
                  <X size={13} />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
