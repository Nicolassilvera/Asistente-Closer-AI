// ui/src/pages/LeadDetail.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Phone, MessageCircle, Calendar, Clock,
  Pencil, Trash2, X, Globe, Mail, AtSign,
} from 'lucide-react'
import {
  getLead, getEvents, getConversations,
  updateStatus, updateLead, deleteLead,
  prospectLead, sendWhatsAppViaJarvis,
} from '../api'
import StatusBadge, { STATUS_CONFIG } from '../components/StatusBadge'

const ESTADOS = [
  'nuevo','analizado','contactado','respondio',
  'interesado','caliente','negociacion','cerrado','descartado',
]

const EVENT_ICONS = {
  lead_creado:      '🟢',
  lead_detectado:   '🔍',
  estado_cambiado:  '🔄',
  lead_actualizado: '✏️',
  mensaje_enviado:  '📤',
  'lead_respondió': '📩',
}

export default function LeadDetail({ leadId, onBack }) {
  const qc = useQueryClient()

  const [tab,        setTab]        = useState('info')
  const [draftMsg,   setDraftMsg]   = useState('')
  const [showDraft,  setShowDraft]  = useState(false)
  const [drafting,   setDrafting]   = useState(false)
  const [sending,    setSending]    = useState(false)
  const [sentOk,     setSentOk]     = useState(false)
  const [showEdit,   setShowEdit]   = useState(false)
  const [editForm,   setEditForm]   = useState(null)
  const [editSaving, setEditSaving] = useState(false)
  const [confirmDel, setConfirmDel] = useState(false)
  const [deleting,   setDeleting]   = useState(false)

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
    },
  })

  const editMutation = useMutation({
    mutationFn: (data) => updateLead(leadId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      setShowEdit(false)
      setEditSaving(false)
    },
    onError: () => setEditSaving(false),
  })

  const handleDelete = async () => {
    setDeleting(true)
    try { await deleteLead(leadId); onBack() }
    catch (e) { console.error(e); setDeleting(false); setConfirmDel(false) }
  }

  const handleProspect = async () => {
    setDrafting(true)
    try { const d = await prospectLead(leadId); setDraftMsg(d.message); setShowDraft(true) }
    catch (e) { console.error(e) }
    setDrafting(false)
  }

  if (isLoading) return <div className="p-6 text-jarvis-muted text-sm">Cargando...</div>
  if (!lead)    return <div className="p-6 text-jarvis-muted text-sm">Lead no encontrado.</div>

  const TABS = [
    { id: 'info',     label: 'Info' },
    { id: 'estado',   label: 'Estado' },
    { id: 'convs',    label: `Mensajes ${conversations.length ? `(${conversations.length})` : ''}` },
    { id: 'historial',label: `Historial ${events.length ? `(${events.length})` : ''}` },
  ]

  return (
    <div className="p-6 space-y-5 max-w-5xl">

      {/* Encabezado */}
      <div className="flex items-start gap-3">
        <button onClick={onBack}
          className="p-2 rounded-lg hover:bg-jarvis-card text-jarvis-muted hover:text-jarvis-text
                     transition-colors mt-0.5 flex-shrink-0">
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="font-heading font-bold text-xl text-jarvis-text truncate">
              {lead.company_name}
            </h1>
            <StatusBadge status={lead.lead_status} />
            <span className="text-amber-400 font-bold text-sm">★ {lead.lead_score ?? 0}</span>
          </div>
          {lead.contact_name && (
            <p className="text-jarvis-muted text-sm mt-0.5">{lead.contact_name}</p>
          )}
          {lead.city && (
            <p className="text-jarvis-muted text-xs mt-0.5">{[lead.city, lead.province].filter(Boolean).join(', ')}</p>
          )}
        </div>

        {/* Acciones */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => { setEditForm({ ...lead }); setShowEdit(true) }}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                       bg-jarvis-card border border-jarvis-border text-jarvis-muted
                       hover:text-jarvis-text hover:border-[#FF8C00]/40 transition-colors">
            <Pencil size={12} /> Editar
          </button>
          <button
            onClick={() => setConfirmDel(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                       bg-jarvis-card border border-red-500/25 text-red-400/60
                       hover:text-red-400 hover:border-red-500/50 transition-colors">
            <Trash2 size={12} /> Eliminar
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 border-b border-jarvis-border">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px
              ${tab === t.id
                ? 'text-[#FF8C00] border-[#FF8C00]'
                : 'text-jarvis-muted border-transparent hover:text-jarvis-text'
              }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Info */}
      {tab === 'info' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Información general">
            <InfoRow label="Rubro"     value={lead.category} />
            <InfoRow label="Ciudad"    value={lead.city} />
            <InfoRow label="Provincia" value={lead.province} />
            <InfoRow label="Fuente"    value={lead.source} />
            <InfoRow label="Prioridad" value={lead.priority} />
            {lead.followup_date && (
              <div className="flex items-center gap-2 text-amber-400 text-sm pt-1">
                <Calendar size={13} />
                <span>Seguimiento: {lead.followup_date}</span>
              </div>
            )}
          </Panel>

          <Panel title="Datos de contacto">
            {lead.phone && (
              <ContactRow icon={<Phone size={13} />} href={`tel:${lead.phone}`} hoverColor="hover:text-teal-400">
                {lead.phone}
              </ContactRow>
            )}
            {lead.whatsapp && (
              <ContactRow icon={<MessageCircle size={13} />}
                href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                hoverColor="hover:text-green-400" external>
                {lead.whatsapp}
              </ContactRow>
            )}
            {lead.email && (
              <ContactRow icon={<Mail size={13} />} href={`mailto:${lead.email}`} hoverColor="hover:text-blue-400">
                {lead.email}
              </ContactRow>
            )}
            {lead.instagram && (
              <ContactRow icon={<AtSign size={13} />}
                href={`https://instagram.com/${lead.instagram.replace('@','')}`}
                hoverColor="hover:text-pink-400" external>
                {lead.instagram}
              </ContactRow>
            )}
            {lead.website && (
              <ContactRow icon={<Globe size={13} />} href={lead.website}
                hoverColor="hover:text-[#FF8C00]" external>
                <span className="truncate">{lead.website}</span>
              </ContactRow>
            )}
            {!lead.phone && !lead.whatsapp && !lead.email && !lead.instagram && !lead.website && (
              <p className="text-jarvis-muted text-sm">Sin datos de contacto.</p>
            )}
          </Panel>

          {lead.notes && (
            <div className="lg:col-span-2">
              <Panel title="Notas">
                <p className="text-sm text-jarvis-muted whitespace-pre-wrap leading-relaxed">{lead.notes}</p>
              </Panel>
            </div>
          )}

          {/* Botón prospección */}
          <div className="lg:col-span-2">
            <button onClick={handleProspect} disabled={drafting}
              className="w-full px-4 py-3 bg-[#FF8C00]/10 hover:bg-[#FF8C00]/20 border
                         border-[#FF8C00]/30 rounded-xl text-sm text-[#FF8C00] font-semibold
                         transition-colors disabled:opacity-50">
              {drafting ? 'Generando mensaje...' : '✉ Generar mensaje de prospección'}
            </button>
          </div>
        </div>
      )}

      {/* Tab: Estado */}
      {tab === 'estado' && (
        <div className="max-w-lg space-y-4">
          <Panel title="Cambiar estado del lead">
            <div className="flex flex-wrap gap-2">
              {ESTADOS.map(s => {
                const cfg = STATUS_CONFIG[s] ?? STATUS_CONFIG.descartado
                const isActive = lead.lead_status === s
                return (
                  <button key={s}
                    onClick={() => statusMutation.mutate({ status: s })}
                    className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full
                                border transition-colors font-medium
                                ${isActive ? cfg.cls : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${isActive ? cfg.dot : 'bg-jarvis-muted/30'}`} />
                    {s}
                  </button>
                )
              })}
            </div>
          </Panel>
        </div>
      )}

      {/* Tab: Mensajes */}
      {tab === 'convs' && (
        <Panel title="Conversaciones">
          {conversations.length === 0
            ? <p className="text-jarvis-muted text-sm">Sin conversaciones registradas.</p>
            : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {conversations.map(conv => {
                  const isMe = conv.sender === 'yo' || conv.sender === 'jarvis'
                  return (
                    <div key={conv.id} className={`flex gap-3 ${isMe ? 'flex-row-reverse' : ''}`}>
                      <div className={`text-xs px-3.5 py-2.5 rounded-2xl max-w-sm
                        ${isMe
                          ? 'bg-[#FF8C00]/15 text-jarvis-text rounded-tr-sm'
                          : 'bg-jarvis-surface text-jarvis-muted rounded-tl-sm'
                        }`}>
                        <p className="leading-relaxed">{conv.message}</p>
                        <p className={`text-[10px] mt-1 ${isMe ? 'text-[#FF8C00]/60 text-right' : 'text-jarvis-muted/60'}`}>
                          {conv.platform} · {conv.created_at?.slice(0,16)}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          }
        </Panel>
      )}

      {/* Tab: Historial */}
      {tab === 'historial' && (
        <Panel title="Historial de actividad">
          {events.length === 0
            ? <p className="text-jarvis-muted text-sm">Sin eventos registrados.</p>
            : (
              <div className="space-y-1 max-h-[32rem] overflow-y-auto pr-1">
                {events.map(ev => (
                  <div key={ev.id}
                    className="flex gap-3 p-3 rounded-xl hover:bg-jarvis-surface/60 transition-colors">
                    <span className="text-base flex-shrink-0 mt-0.5">
                      {EVENT_ICONS[ev.event_type] ?? '📌'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-jarvis-text leading-snug">
                        {ev.event_description || ev.event_type}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-jarvis-muted">{ev.created_at?.slice(0,16)}</span>
                        <span className="text-jarvis-border">·</span>
                        <span className="text-xs text-jarvis-muted">{ev.created_by}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )
          }
        </Panel>
      )}

      {/* Toast */}
      {sentOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/15 border border-green-500/30
                        rounded-xl px-5 py-3 text-green-400 text-sm font-medium shadow-xl"
          onClick={() => setSentOk(false)}>
          Jarvis está enviando el mensaje por WhatsApp
        </div>
      )}

      {/* Modal: Editar */}
      {showEdit && editForm && (
        <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-2xl my-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-jarvis-border">
              <h3 className="font-heading font-bold text-base text-jarvis-text">Editar lead</h3>
              <button onClick={() => setShowEdit(false)} className="text-jarvis-muted hover:text-jarvis-text">
                <X size={16} />
              </button>
            </div>
            <div className="px-6 py-5 space-y-4 max-h-[65vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-3">
                <EF label="Empresa" required span2>
                  <input value={editForm.company_name ?? ''} onChange={e => setEditForm(f => ({...f, company_name: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Contacto">
                  <input value={editForm.contact_name ?? ''} onChange={e => setEditForm(f => ({...f, contact_name: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Rubro">
                  <input value={editForm.category ?? ''} onChange={e => setEditForm(f => ({...f, category: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Ciudad">
                  <input value={editForm.city ?? ''} onChange={e => setEditForm(f => ({...f, city: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Provincia">
                  <input value={editForm.province ?? ''} onChange={e => setEditForm(f => ({...f, province: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Teléfono">
                  <input value={editForm.phone ?? ''} onChange={e => setEditForm(f => ({...f, phone: e.target.value}))} className="field-input" />
                </EF>
                <EF label="WhatsApp">
                  <input value={editForm.whatsapp ?? ''} onChange={e => setEditForm(f => ({...f, whatsapp: e.target.value}))} className="field-input" placeholder="+5491100000000" />
                </EF>
                <EF label="Email">
                  <input value={editForm.email ?? ''} type="email" onChange={e => setEditForm(f => ({...f, email: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Instagram">
                  <input value={editForm.instagram ?? ''} onChange={e => setEditForm(f => ({...f, instagram: e.target.value}))} className="field-input" placeholder="@usuario" />
                </EF>
                <EF label="Sitio web" span2>
                  <input value={editForm.website ?? ''} onChange={e => setEditForm(f => ({...f, website: e.target.value}))} className="field-input" placeholder="https://..." />
                </EF>
                <EF label="Prioridad">
                  <select value={editForm.priority ?? 'media'} onChange={e => setEditForm(f => ({...f, priority: e.target.value}))} className="field-input">
                    <option value="alta">Alta</option>
                    <option value="media">Media</option>
                    <option value="baja">Baja</option>
                  </select>
                </EF>
                <EF label="Estado">
                  <select value={editForm.lead_status ?? 'nuevo'} onChange={e => setEditForm(f => ({...f, lead_status: e.target.value}))} className="field-input">
                    {ESTADOS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </EF>
                <EF label="Score (0-10)">
                  <input type="number" min={0} max={10} step={0.1} value={editForm.lead_score ?? 0}
                    onChange={e => setEditForm(f => ({...f, lead_score: Number(e.target.value)}))} className="field-input" />
                </EF>
                <EF label="Fecha seguimiento">
                  <input type="date" value={editForm.followup_date ?? ''} onChange={e => setEditForm(f => ({...f, followup_date: e.target.value}))} className="field-input" />
                </EF>
                <EF label="Notas" span2>
                  <textarea value={editForm.notes ?? ''} onChange={e => setEditForm(f => ({...f, notes: e.target.value}))} rows={3} className="field-input resize-none" />
                </EF>
              </div>
            </div>
            <div className="flex gap-3 px-6 py-4 border-t border-jarvis-border">
              <button onClick={() => setShowEdit(false)}
                className="flex-1 px-4 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cancelar
              </button>
              <button
                onClick={() => { setEditSaving(true); editMutation.mutate(editForm) }}
                disabled={editSaving}
                className="flex-1 px-4 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00] rounded-xl text-sm
                           font-semibold text-white transition-colors disabled:opacity-50">
                {editSaving ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Confirmar eliminar */}
      {confirmDel && (
        <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-red-500/25 rounded-xl w-full max-w-sm p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-red-400/10 flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-red-400" />
              </div>
              <div>
                <p className="text-jarvis-text font-semibold">Eliminar lead</p>
                <p className="text-jarvis-muted text-sm mt-1">
                  ¿Eliminar <span className="text-jarvis-text font-medium">{lead.company_name}</span>?
                  Esta acción no se puede deshacer.
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setConfirmDel(false)}
                className="flex-1 px-4 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cancelar
              </button>
              <button onClick={handleDelete} disabled={deleting}
                className="flex-1 px-4 py-2.5 bg-red-500/15 hover:bg-red-500/25 border border-red-500/30
                           rounded-xl text-sm text-red-400 font-semibold transition-colors disabled:opacity-50">
                {deleting ? 'Eliminando...' : 'Sí, eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Borrador de mensaje */}
      {showDraft && (
        <div className="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-base text-jarvis-text">Mensaje generado</h3>
              <button onClick={() => setShowDraft(false)} className="text-jarvis-muted hover:text-jarvis-text">
                <X size={16} />
              </button>
            </div>
            <textarea
              value={draftMsg}
              onChange={e => setDraftMsg(e.target.value)}
              rows={7}
              className="field-input resize-none"
            />
            <div className="flex gap-2">
              <button onClick={() => { navigator.clipboard.writeText(draftMsg); setShowDraft(false) }}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Copiar
              </button>
              <button
                onClick={async () => {
                  const contact = lead.whatsapp || lead.contact_name || lead.company_name
                  setSending(true)
                  try {
                    await sendWhatsAppViaJarvis(contact, draftMsg, leadId)
                    setSentOk(true)
                    setShowDraft(false)
                  } catch (e) { console.error(e) }
                  setSending(false)
                }}
                disabled={sending}
                className="flex-1 px-3 py-2.5 bg-green-500/15 hover:bg-green-500/25 border
                           border-green-500/30 rounded-xl text-sm text-green-400 font-semibold
                           transition-colors disabled:opacity-50">
                {sending ? 'Enviando...' : '🤖 Enviar con Jarvis'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Panel({ title, children }) {
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5 space-y-3">
      <h2 className="text-xs font-semibold text-jarvis-muted uppercase tracking-widest">{title}</h2>
      {children}
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

function ContactRow({ icon, href, hoverColor, external, children }) {
  return (
    <a href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined}
      className={`flex items-center gap-2.5 text-sm text-jarvis-muted ${hoverColor} transition-colors`}>
      <span className="flex-shrink-0 opacity-60">{icon}</span>
      {children}
    </a>
  )
}

function EF({ label, children, span2 = false }) {
  return (
    <div className={`flex flex-col gap-1 ${span2 ? 'col-span-2' : ''}`}>
      <label className="text-xs text-jarvis-muted">{label}</label>
      {children}
    </div>
  )
}
