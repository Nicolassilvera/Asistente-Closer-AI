// ui/src/pages/Seguimientos.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Calendar, Phone, MessageCircle, Check } from 'lucide-react'
import { getFollowups, updateStatus, updateLead } from '../api'
import StatusBadge from '../components/StatusBadge'
import LeadDetail from './LeadDetail'

const PRIORIDAD_COLORS = {
  alta:  'text-red-400 bg-red-400/10 border-red-400/30',
  media: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
  baja:  'text-gray-400 bg-gray-400/10 border-gray-400/30',
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
    onSuccess:  () => {
      qc.invalidateQueries({ queryKey: ['followups'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    }
  })

  const clearFollowup = useMutation({
    mutationFn: (id) => updateLead(id, { followup_date: '' }),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['followups'] })
  })

  if (selectedId) {
    return <LeadDetail leadId={selectedId} onBack={() => setSelectedId(null)} />
  }

  // Separar vencidos de hoy y próximos
  const today    = new Date().toISOString().slice(0, 10)
  const vencidos = followups.filter(l => l.followup_date < today)
  const hoy      = followups.filter(l => l.followup_date === today)
  const proximos = followups.filter(l => l.followup_date > today)

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-jarvis-text flex items-center gap-2">
          <Bell size={20} className="text-amber-400" />
          Seguimientos
        </h1>
        <p className="text-jarvis-muted text-sm mt-0.5">
          {followups.length} pendientes
          {vencidos.length > 0 && (
            <span className="ml-2 text-red-400 font-medium">
              · {vencidos.length} vencidos
            </span>
          )}
        </p>
      </div>

      {isLoading && (
        <p className="text-jarvis-muted text-sm">Cargando...</p>
      )}

      {!isLoading && followups.length === 0 && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-8 text-center">
          <Bell size={32} className="text-jarvis-muted mx-auto mb-3" />
          <p className="text-jarvis-muted">Sin seguimientos pendientes.</p>
          <p className="text-xs text-jarvis-muted mt-1">
            Asigná una fecha de seguimiento a tus leads desde el panel de detalle.
          </p>
        </div>
      )}

      {/* Vencidos */}
      {vencidos.length > 0 && (
        <Section
          title="Vencidos"
          color="text-red-400"
          leads={vencidos}
          onSelect={setSelectedId}
          onStatus={statusMutation}
          onClear={clearFollowup}
          today={today}
        />
      )}

      {/* Hoy */}
      {hoy.length > 0 && (
        <Section
          title="Hoy"
          color="text-amber-400"
          leads={hoy}
          onSelect={setSelectedId}
          onStatus={statusMutation}
          onClear={clearFollowup}
          today={today}
        />
      )}

      {/* Próximos */}
      {proximos.length > 0 && (
        <Section
          title="Próximos"
          color="text-jarvis-muted"
          leads={proximos}
          onSelect={setSelectedId}
          onStatus={statusMutation}
          onClear={clearFollowup}
          today={today}
        />
      )}
    </div>
  )
}

function Section({ title, color, leads, onSelect, onStatus, onClear, today }) {
  return (
    <div className="space-y-2">
      <h2 className={`text-sm font-medium ${color} flex items-center gap-2`}>
        <Calendar size={14} />
        {title} ({leads.length})
      </h2>

      <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden">
        {leads.map((lead, i) => (
          <div key={lead.id}
            className={`flex items-center gap-4 px-4 py-3 hover:bg-jarvis-surface/50
                        transition-colors cursor-pointer
                        ${i < leads.length - 1 ? 'border-b border-jarvis-border' : ''}`}
            onClick={() => onSelect(lead.id)}>

            {/* Fecha */}
            <div className="flex-shrink-0 text-center w-14">
              <div className={`text-xs font-bold ${
                lead.followup_date < today ? 'text-red-400' :
                lead.followup_date === today ? 'text-amber-400' : 'text-jarvis-muted'
              }`}>
                {lead.followup_date?.slice(5)}
              </div>
              <div className="text-[10px] text-jarvis-muted">
                {lead.followup_date?.slice(0, 4)}
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-jarvis-text truncate">
                  {lead.company_name}
                </span>
                {lead.priority && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border
                    ${PRIORIDAD_COLORS[lead.priority]}`}>
                    {lead.priority}
                  </span>
                )}
              </div>
              <div className="text-xs text-jarvis-muted truncate mt-0.5">
                {[lead.contact_name, lead.city, lead.category]
                  .filter(Boolean).join(' · ')}
              </div>
              {lead.notes && (
                <div className="text-xs text-jarvis-muted/70 truncate mt-0.5 italic">
                  {lead.notes.slice(0, 80)}
                </div>
              )}
            </div>

            {/* Estado */}
            <div className="flex-shrink-0">
              <StatusBadge status={lead.lead_status} />
            </div>

            {/* Acciones rápidas */}
            <div className="flex items-center gap-1 flex-shrink-0"
              onClick={e => e.stopPropagation()}>

              {lead.whatsapp && (
                <a href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                  target="_blank" rel="noreferrer"
                  className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                             hover:text-green-400 transition-colors">
                  <MessageCircle size={14} />
                </a>
              )}
              {lead.phone && (
                <a href={`tel:${lead.phone}`}
                  className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                             hover:text-teal-400 transition-colors">
                  <Phone size={14} />
                </a>
              )}

              {/* Marcar contactado */}
              <button
                onClick={() => onStatus.mutate({ id: lead.id, status: 'contactado' })}
                title="Marcar como contactado"
                className="p-1.5 rounded-lg hover:bg-green-400/10 text-jarvis-muted
                           hover:text-green-400 transition-colors">
                <Check size={14} />
              </button>

              {/* Limpiar fecha */}
              <button
                onClick={() => onClear.mutate(lead.id)}
                title="Quitar seguimiento"
                className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                           hover:text-red-400 transition-colors text-xs font-medium">
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}