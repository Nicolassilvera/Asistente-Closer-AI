// ui/src/pages/Leads.jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Plus, Phone, MessageCircle, ChevronRight, Sparkles, X } from 'lucide-react'
import { getLeads, prospectLead, sendWhatsAppViaJarvis } from '../api'
import StatusBadge, { STATUS_CONFIG } from '../components/StatusBadge'
import LeadForm from '../components/LeadForm'
import LeadDetail from './LeadDetail'

const STATUSES = [
  'nuevo','analizado','contactado','respondio',
  'interesado','caliente','negociacion','cerrado','descartado',
]

export default function Leads() {
  const [search,     setSearch]     = useState('')
  const [filter,     setFilter]     = useState('')
  const [showForm,   setShowForm]   = useState(false)
  const [selectedId, setSelectedId] = useState(null)

  // Estado para el modal de prospección rápida
  const [prospLead,  setProspLead]  = useState(null)   // lead seleccionado para prospectar
  const [draft,      setDraft]      = useState('')
  const [drafting,   setDrafting]   = useState(false)
  const [sending,    setSending]    = useState(false)
  const [sentOk,     setSentOk]     = useState(false)

  const { data: leads, isLoading } = useQuery({
    queryKey: ['leads', search, filter],
    queryFn:  () => getLeads({ search: search || undefined, status: filter || undefined }),
    refetchInterval: 10000,
  })

  const handleProspect = async (lead, e) => {
    e.stopPropagation()
    setProspLead(lead)
    setDraft('')
    setDrafting(true)
    try {
      const data = await prospectLead(lead.id)
      setDraft(data.message)
    } catch (err) {
      console.error(err)
      setDraft('No se pudo generar el mensaje. Intentá de nuevo.')
    }
    setDrafting(false)
  }

  const handleSend = async () => {
    if (!prospLead) return
    const contact = prospLead.whatsapp || prospLead.contact_name || prospLead.company_name
    setSending(true)
    try {
      await sendWhatsAppViaJarvis(contact, draft, prospLead.id)
      setSentOk(true)
      setProspLead(null)
    } catch (e) { console.error(e) }
    setSending(false)
  }

  if (selectedId) {
    return <LeadDetail leadId={selectedId} onBack={() => setSelectedId(null)} />
  }

  return (
    <div className="p-6 space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading font-bold text-2xl text-jarvis-text">Leads</h1>
          <p className="text-jarvis-muted text-sm mt-0.5">{leads?.length ?? 0} prospectos registrados</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00]
                     rounded-xl text-sm font-semibold text-white transition-colors shadow-lg
                     shadow-[#FF8C00]/20">
          <Plus size={16} /> Nuevo lead
        </button>
      </div>

      {/* Barra de búsqueda */}
      <div className="relative">
        <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-jarvis-muted" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar por empresa, ciudad, rubro..."
          className="w-full pl-10 pr-4 py-2.5 bg-jarvis-card border border-jarvis-border rounded-xl
                     text-sm text-jarvis-text placeholder-jarvis-muted/60
                     focus:outline-none focus:border-[#FF8C00]/50 transition-colors"
        />
      </div>

      {/* Filtro por estado — chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setFilter('')}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors font-medium
            ${filter === ''
              ? 'bg-[#FF8C00]/15 border-[#FF8C00]/40 text-[#FF8C00]'
              : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80 hover:text-jarvis-text'
            }`}>
          Todos
        </button>
        {STATUSES.map(s => {
          const cfg = STATUS_CONFIG[s]
          const isActive = filter === s
          return (
            <button key={s}
              onClick={() => setFilter(s === filter ? '' : s)}
              className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border
                         transition-colors font-medium
                         ${isActive ? cfg.cls : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isActive ? cfg.dot : 'bg-jarvis-muted/30'}`} />
              {s}
              {leads?.filter(l => l.lead_status === s).length > 0 && (
                <span className={`${isActive ? 'opacity-70' : 'text-jarvis-muted/50'}`}>
                  {leads.filter(l => l.lead_status === s).length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Tabla */}
      <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-jarvis-border bg-jarvis-surface/50">
              {['Empresa','Ciudad','Rubro','Score','Estado','Acciones'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-[11px] font-semibold
                                       text-jarvis-muted uppercase tracking-wider">
                  {h}
                </th>
              ))}
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-jarvis-muted text-sm">
                Cargando...
              </td></tr>
            )}
            {!isLoading && !leads?.length && (
              <tr><td colSpan={7} className="px-4 py-10 text-center">
                <p className="text-jarvis-muted text-sm">No hay leads todavía.</p>
                <button onClick={() => setShowForm(true)}
                  className="mt-3 text-xs text-[#FF8C00] hover:underline">
                  Crear el primero
                </button>
              </td></tr>
            )}
            {leads?.map((lead, i) => (
              <tr key={lead.id}
                onClick={() => setSelectedId(lead.id)}
                className={`cursor-pointer hover:bg-jarvis-surface/60 transition-colors
                            ${i < leads.length - 1 ? 'border-b border-jarvis-border/50' : ''}`}>
                <td className="px-4 py-3.5">
                  <div className="font-semibold text-sm text-jarvis-text">{lead.company_name}</div>
                  {lead.contact_name && (
                    <div className="text-xs text-jarvis-muted mt-0.5">{lead.contact_name}</div>
                  )}
                </td>
                <td className="px-4 py-3.5 text-sm text-jarvis-muted">{lead.city ?? '—'}</td>
                <td className="px-4 py-3.5 text-sm text-jarvis-muted max-w-32">
                  <span className="truncate block">{lead.category ?? '—'}</span>
                </td>
                <td className="px-4 py-3.5">
                  <span className="text-amber-400 font-bold text-sm">★ {lead.lead_score ?? 0}</span>
                </td>
                <td className="px-4 py-3.5">
                  <StatusBadge status={lead.lead_status} />
                </td>
                <td className="px-4 py-3.5" onClick={e => e.stopPropagation()}>
                  <div className="flex items-center gap-1">
                    {/* Generar mensaje de prospección */}
                    <button
                      onClick={e => handleProspect(lead, e)}
                      title="Generar mensaje de prospección"
                      className="p-1.5 rounded-lg hover:bg-[#FF8C00]/10 text-jarvis-muted
                                 hover:text-[#FF8C00] transition-colors">
                      <Sparkles size={13} />
                    </button>
                    {lead.phone && (
                      <a href={`tel:${lead.phone}`}
                        className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                                   hover:text-teal-400 transition-colors">
                        <Phone size={13} />
                      </a>
                    )}
                    {lead.whatsapp && (
                      <a href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                        target="_blank" rel="noreferrer"
                        className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                                   hover:text-green-400 transition-colors">
                        <MessageCircle size={13} />
                      </a>
                    )}
                  </div>
                </td>
                <td className="pr-3">
                  <ChevronRight size={14} className="text-jarvis-muted/40" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && <LeadForm onClose={() => setShowForm(false)} />}

      {/* Toast envío OK */}
      {sentOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/15 border border-green-500/30
                        rounded-xl px-5 py-3 text-green-400 text-sm font-medium shadow-xl
                        cursor-pointer"
          onClick={() => setSentOk(false)}>
          Jarvis está enviando el mensaje por WhatsApp
        </div>
      )}

      {/* Modal de prospección rápida */}
      {prospLead && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-lg p-6 space-y-4">

            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-jarvis-text">
                  Mensaje de prospección
                </h3>
                <p className="text-xs text-jarvis-muted mt-0.5">{prospLead.company_name}</p>
              </div>
              <button onClick={() => setProspLead(null)}
                className="text-jarvis-muted hover:text-jarvis-text transition-colors">
                <X size={16} />
              </button>
            </div>

            {drafting ? (
              <div className="flex items-center gap-3 py-6 justify-center">
                <div className="w-4 h-4 border-2 border-[#FF8C00] border-t-transparent rounded-full animate-spin" />
                <span className="text-jarvis-muted text-sm">Jarvis está generando el mensaje...</span>
              </div>
            ) : (
              <textarea
                value={draft}
                onChange={e => setDraft(e.target.value)}
                rows={7}
                className="field-input resize-none"
                placeholder="El mensaje aparecerá aquí..."
              />
            )}

            <div className="flex gap-2">
              <button onClick={() => setProspLead(null)}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cerrar
              </button>
              <button
                onClick={() => { navigator.clipboard.writeText(draft) }}
                disabled={drafting || !draft}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium
                           disabled:opacity-40">
                Copiar
              </button>
              <button
                onClick={handleSend}
                disabled={drafting || !draft || sending}
                className="flex-1 px-3 py-2.5 bg-green-500/15 hover:bg-green-500/25 border
                           border-green-500/30 rounded-xl text-sm text-green-400 font-semibold
                           transition-colors disabled:opacity-40">
                {sending ? 'Enviando...' : '🤖 Enviar con Jarvis'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
