// ui/src/pages/LeadDetail.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Phone, MessageCircle, Star, Calendar, Clock } from 'lucide-react'
import { getLead, getEvents, getConversations, updateStatus, prospectLead, sendWhatsAppViaJarvis } from '../api'
import StatusBadge from '../components/StatusBadge'

const ESTADOS = [
  'nuevo','analizado','contactado','respondio',
  'interesado','caliente','negociacion','cerrado','descartado'
]

const EVENT_ICONS = {
  'lead_creado':      '🟢',
  'lead_detectado':   '🔍',
  'estado_cambiado':  '🔄',
  'lead_actualizado': '✏️',
  'mensaje_enviado':  '📤',
  'lead_respondió':   '📩',
}

export default function LeadDetail({ leadId, onBack }) {
  const qc = useQueryClient()

  const [draftMsg,   setDraftMsg]   = useState('')
  const [showDraft,  setShowDraft]  = useState(false)
  const [drafting,   setDrafting]   = useState(false)
  const [sending,    setSending]    = useState(false)
  const [sentOk,     setSentOk]     = useState(false)

  const handleProspect = async () => {
    setDrafting(true)
    try {
      const data = await prospectLead(leadId)
      setDraftMsg(data.message)
      setShowDraft(true)
    } catch (e) {
      console.error(e)
    }
    setDrafting(false)
  }

  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead', leadId],
    queryFn:  () => getLead(leadId),
  })

  const { data: events = [] } = useQuery({
    queryKey: ['events', leadId],
    queryFn:  () => getEvents(leadId),
    refetchInterval: 10000,
  })

  const { data: conversations = [] } = useQuery({
    queryKey: ['conversations', leadId],
    queryFn:  () => getConversations(leadId),
    refetchInterval: 10000,
  })

  const statusMutation = useMutation({
    mutationFn: ({ status }) => updateStatus(leadId, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    }
  })

  if (isLoading) return (
    <div className="p-6 text-jarvis-muted">Cargando...</div>
  )
  if (!lead) return (
    <div className="p-6 text-jarvis-muted">Lead no encontrado.</div>
  )

  return (
    <div className="p-6 space-y-6">

      {/* Header */}
      <div className="flex items-start gap-4">
        <button onClick={onBack}
          className="p-2 rounded-lg hover:bg-jarvis-card text-jarvis-muted
                     hover:text-jarvis-text transition-colors mt-0.5">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-semibold text-jarvis-text">
              {lead.company_name}
            </h1>
            <StatusBadge status={lead.lead_status} />
            <span className="text-amber-400 font-medium text-sm">
              ★ {lead.lead_score ?? 0}
            </span>
          </div>
          {lead.contact_name && (
            <p className="text-jarvis-muted text-sm mt-0.5">{lead.contact_name}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Columna izquierda — datos */}
        <div className="space-y-4">

          {/* Info */}
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4 space-y-3">
            <h2 className="text-sm font-medium text-jarvis-text">Información</h2>

            <InfoRow label="Rubro"    value={lead.category} />
            <InfoRow label="Ciudad"   value={lead.city} />
            <InfoRow label="Provincia" value={lead.province} />
            <InfoRow label="Fuente"   value={lead.source} />
            <InfoRow label="Prioridad" value={lead.priority} />

            {lead.followup_date && (
              <div className="flex items-center gap-2 text-amber-400 text-sm">
                <Calendar size={14} />
                <span>Seguimiento: {lead.followup_date}</span>
              </div>
            )}
          </div>

          {/* Contacto */}
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4 space-y-3">
            <h2 className="text-sm font-medium text-jarvis-text">Contacto</h2>

            {lead.phone && (
              <a href={`tel:${lead.phone}`}
                className="flex items-center gap-2 text-sm text-jarvis-muted
                           hover:text-teal-400 transition-colors">
                <Phone size={14} />
                {lead.phone}
              </a>
            )}
            {lead.whatsapp && (
              <a href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                target="_blank" rel="noreferrer"
                className="flex items-center gap-2 text-sm text-jarvis-muted
                           hover:text-green-400 transition-colors">
                <MessageCircle size={14} />
                {lead.whatsapp}
              </a>
            )}
            {lead.email && (
              <a href={`mailto:${lead.email}`}
                className="flex items-center gap-2 text-sm text-jarvis-muted
                           hover:text-blue-400 transition-colors">
                <span className="text-xs">✉</span>
                {lead.email}
              </a>
            )}
            {lead.instagram && (
              <a href={`https://instagram.com/${lead.instagram.replace('@','')}`}
                target="_blank" rel="noreferrer"
                className="flex items-center gap-2 text-sm text-jarvis-muted
                           hover:text-pink-400 transition-colors">
                <span className="text-xs">📷</span>
                {lead.instagram}
              </a>
            )}
            {lead.website && (
              <a href={lead.website} target="_blank" rel="noreferrer"
                className="flex items-center gap-2 text-sm text-jarvis-muted
                           hover:text-jarvis-purple transition-colors truncate">
                <span className="text-xs">🌐</span>
                {lead.website}
              </a>
            )}
          </div>

          {/* Cambiar estado */}
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
            <h2 className="text-sm font-medium text-jarvis-text mb-3">Estado</h2>
            <div className="flex flex-wrap gap-2">
              {ESTADOS.map(s => (
                <button key={s}
                  onClick={() => statusMutation.mutate({ status: s })}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors
                    ${lead.lead_status === s
                      ? 'bg-jarvis-purple/30 border-jarvis-purple text-jarvis-purple'
                      : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-purple/50'
                    }`}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Notas */}
          {lead.notes && (
            <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
              <h2 className="text-sm font-medium text-jarvis-text mb-2">Notas</h2>
              <p className="text-sm text-jarvis-muted whitespace-pre-wrap leading-relaxed">
                {lead.notes}
              </p>
            </div>
          )}

          {/* Prospección */}
          <button onClick={handleProspect} disabled={drafting}
            className="w-full px-4 py-2.5 bg-jarvis-purple/20 hover:bg-jarvis-purple/30
                       border border-jarvis-purple/40 rounded-xl text-sm text-jarvis-purple
                       font-medium transition-colors disabled:opacity-50">
            {drafting ? 'Generando...' : '✉ Generar mensaje de prospección'}
          </button>
        </div>

        {/* Columna derecha — historial */}
        <div className="lg:col-span-2 space-y-4">

          {/* Conversaciones */}
          {conversations.length > 0 && (
            <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
              <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
                <MessageCircle size={15} className="text-green-400" />
                Conversaciones ({conversations.length})
              </h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {conversations.map(conv => (
                  <div key={conv.id}
                    className={`flex gap-3 ${conv.sender === 'yo' || conv.sender === 'jarvis'
                      ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div className={`text-xs px-3 py-2 rounded-xl max-w-xs
                      ${conv.sender === 'yo' || conv.sender === 'jarvis'
                        ? 'bg-jarvis-purple/20 text-jarvis-text'
                        : 'bg-jarvis-surface text-jarvis-muted'
                      }`}>
                      <p>{conv.message}</p>
                      <p className="text-jarvis-muted mt-1 text-[10px]">
                        {conv.platform} · {conv.created_at?.slice(0,16)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Historial de eventos */}
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
            <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
              <Clock size={15} className="text-jarvis-muted" />
              Historial ({events.length})
            </h2>

            {events.length === 0 ? (
              <p className="text-jarvis-muted text-sm">Sin eventos registrados.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {events.map(ev => (
                  <div key={ev.id}
                    className="flex gap-3 p-2.5 rounded-lg hover:bg-jarvis-surface
                               transition-colors">
                    <span className="text-base flex-shrink-0 mt-0.5">
                      {EVENT_ICONS[ev.event_type] ?? '📌'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-jarvis-text leading-snug">
                        {ev.event_description || ev.event_type}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-jarvis-muted">
                          {ev.created_at?.slice(0,16)}
                        </span>
                        <span className="text-xs text-jarvis-muted">·</span>
                        <span className="text-xs text-jarvis-muted">{ev.created_by}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Toast confirmación envío */}
      {sentOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/20 border border-green-500/40
                        rounded-xl px-5 py-3 text-green-400 text-sm font-medium shadow-lg"
          onClick={() => setSentOk(false)}>
          Jarvis está enviando el mensaje por WhatsApp
        </div>
      )}

      {/* Modal borrador de prospección */}
      {showDraft && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl
                          w-full max-w-lg p-5 space-y-4">
            <h3 className="font-medium text-jarvis-text">Mensaje generado por Jarvis</h3>
            <textarea
              value={draftMsg}
              onChange={e => setDraftMsg(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                         rounded-lg text-sm text-jarvis-text focus:outline-none
                         focus:border-jarvis-purple resize-none"
            />
            <div className="flex gap-3">
              <button onClick={() => setShowDraft(false)}
                className="flex-1 px-4 py-2 border border-jarvis-border rounded-lg
                           text-sm text-jarvis-muted hover:bg-jarvis-surface transition-colors">
                Cerrar
              </button>
              <button onClick={() => { navigator.clipboard.writeText(draftMsg); setShowDraft(false) }}
                className="flex-1 px-4 py-2 bg-jarvis-teal/20 border border-jarvis-teal/40
                           rounded-lg text-sm text-teal-400 font-medium transition-colors">
                Copiar
              </button>
              <button
                onClick={async () => {
                  // Priorizar número de WhatsApp del lead (permite envío sin contacto guardado)
                  const contact = lead.whatsapp || lead.contact_name || lead.company_name
                  setSending(true)
                  try {
                    await sendWhatsAppViaJarvis(contact, draftMsg, leadId)
                    setSentOk(true)
                    setShowDraft(false)
                  } catch (e) {
                    console.error(e)
                  }
                  setSending(false)
                }}
                disabled={sending}
                className="flex-1 px-4 py-2 bg-green-500/20 border border-green-500/40
                           rounded-lg text-sm text-green-400 font-medium transition-colors
                           disabled:opacity-50">
                {sending ? 'Enviando...' : '🤖 Enviar con Jarvis'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-jarvis-muted">{label}</span>
      <span className="text-jarvis-text font-medium">{value}</span>
    </div>
  )
}
