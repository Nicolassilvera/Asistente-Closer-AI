// ui/src/pages/Leads.jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Plus, Phone, MessageCircle, ChevronRight, Sparkles, X, Calendar, Trash2, Download, Upload, Radio } from 'lucide-react'
import { getLeads, prospectLead, sendWhatsAppViaJarvis, updateLead, deleteLead, exportLeadsCsv, importLeadsCsv } from '../api'
import { useMutation, useQueryClient } from '@tanstack/react-query'
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
  const [prospLead,  setProspLead]  = useState(null)
  const [draft,      setDraft]      = useState('')
  const [drafting,   setDrafting]   = useState(false)
  const [sending,    setSending]    = useState(false)
  const [sentOk,     setSentOk]     = useState(false)

  // Seguimiento
  const tomorrow = () => new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  const [followLead, setFollowLead] = useState(null)
  const [followDate, setFollowDate] = useState(tomorrow())
  const [followOk,   setFollowOk]   = useState(false)

  // Eliminar
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting,     setDeleting]     = useState(false)

  // Importar CSV
  const [importing,   setImporting]   = useState(false)
  const [importResult,setImportResult]= useState(null)

  // Campaña masiva WA
  const [selected,       setSelected]       = useState(new Set())
  const [showCampaign,   setShowCampaign]   = useState(false)
  const [campaignMsg,    setCampaignMsg]    = useState('Hola {nombre}, te escribo de parte de Balanzas Caballito para consultarte si te interesaría conocer nuestros productos. Quedamos a disposición, saludos.')
  const [campaignProgress, setCampaignProgress] = useState(null)  // null | { sent, failed, total, done }

  const toggleSelect = (id, e) => {
    e.stopPropagation()
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }
  const toggleAll = () => {
    if (!leads?.length) return
    const allIds = leads.map(l => l.id)
    setSelected(prev => prev.size === allIds.length ? new Set() : new Set(allIds))
  }

  const sendCampaign = async () => {
    const targets = (leads ?? []).filter(l => selected.has(l.id))
    if (!targets.length) return
    setCampaignProgress({ sent: 0, failed: 0, total: targets.length, done: false })
    let sent = 0, failed = 0
    for (const lead of targets) {
      const contact = lead.whatsapp || lead.phone || lead.contact_name || lead.company_name
      const name    = lead.contact_name || lead.company_name || ''
      const msg     = campaignMsg.replace(/\{nombre\}/gi, name).replace(/\{empresa\}/gi, lead.company_name || '')
      try {
        await sendWhatsAppViaJarvis(contact, msg, lead.id)
        sent++
      } catch { failed++ }
      setCampaignProgress({ sent, failed, total: targets.length, done: false })
    }
    setCampaignProgress({ sent, failed, total: targets.length, done: true })
    setSelected(new Set())
    queryClient.invalidateQueries(['leads'])
  }

  const queryClient = useQueryClient()

  const followMutation = useMutation({
    mutationFn: ({ id, date }) => updateLead(id, { followup_date: date }),
    onSuccess: () => {
      queryClient.invalidateQueries(['leads'])
      setFollowLead(null)
      setFollowOk(true)
      setTimeout(() => setFollowOk(false), 3000)
    },
  })

  const handleDelete = async (lead, e) => {
    e.stopPropagation()
    setDeleteTarget(lead)
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteLead(deleteTarget.id)
      queryClient.invalidateQueries(['leads'])
      setDeleteTarget(null)
    } catch (err) { console.error(err) }
    setDeleting(false)
  }

  const handleImport = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    const reader = new FileReader()
    reader.onload = async (ev) => {
      setImporting(true)
      try {
        const text   = ev.target.result
        const lines  = text.split(/\r?\n/).filter(l => l.trim())
        if (lines.length < 2) return
        // Detectar separador: ; o ,
        const sep    = lines[0].includes(';') ? ';' : ','
        const headers = lines[0].split(sep).map(h => h.replace(/^"|"$/g, '').trim().toLowerCase())
        const rows   = lines.slice(1).map(line => {
          const vals = line.split(sep).map(v => v.replace(/^"|"$/g, '').trim())
          const obj  = {}
          headers.forEach((h, i) => { if (vals[i]) obj[h] = vals[i] })
          return obj
        }).filter(r => Object.keys(r).length > 0)

        const result = await importLeadsCsv(rows)
        setImportResult(result)
        queryClient.invalidateQueries(['leads'])
        setTimeout(() => setImportResult(null), 5000)
      } catch (err) {
        setImportResult({ error: 'Error al importar el archivo.' })
      }
      setImporting(false)
    }
    reader.readAsText(file, 'utf-8')
  }

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
        <div className="flex items-center gap-2">
          {selected.size > 0 && (
            <button
              onClick={() => setShowCampaign(true)}
              className="flex items-center gap-2 px-3 py-2.5 bg-purple-500/15 border border-purple-500/30
                         rounded-xl text-sm font-semibold text-purple-400 hover:bg-purple-500/25 transition-colors">
              <Radio size={14} /> Campaña ({selected.size})
            </button>
          )}
          <label
            title="Importar leads desde CSV"
            className={`flex items-center gap-2 px-3 py-2.5 border border-jarvis-border
                       rounded-xl text-sm font-medium cursor-pointer transition-colors
                       ${importing
                         ? 'text-[#FF8C00] border-[#FF8C00]/40 bg-[#FF8C00]/5'
                         : 'text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-card'}`}>
            <Upload size={15} />
            {importing ? 'Importando…' : 'Importar'}
            <input type="file" accept=".csv" className="hidden" onChange={handleImport} disabled={importing} />
          </label>
          <button
            onClick={() => exportLeadsCsv({ search: search || undefined, status: filter || undefined })}
            title="Exportar leads filtrados a CSV"
            className="flex items-center gap-2 px-3 py-2.5 border border-jarvis-border
                       rounded-xl text-sm font-medium text-jarvis-muted hover:text-jarvis-text
                       hover:bg-jarvis-card transition-colors">
            <Download size={15} /> CSV
          </button>
          <button onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00]
                       rounded-xl text-sm font-semibold text-white transition-colors shadow-lg
                       shadow-[#FF8C00]/20">
            <Plus size={16} /> Nuevo lead
          </button>
        </div>
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
              <th className="w-10 pl-4 py-3">
                <input type="checkbox"
                  className="rounded border-jarvis-border accent-[#FF8C00] cursor-pointer"
                  checked={leads?.length > 0 && selected.size === leads?.length}
                  onChange={toggleAll}
                />
              </th>
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
                            ${i < leads.length - 1 ? 'border-b border-jarvis-border/50' : ''}
                            ${selected.has(lead.id) ? 'bg-purple-500/5' : ''}`}>
                <td className="w-10 pl-4 py-3.5" onClick={e => e.stopPropagation()}>
                  <input type="checkbox"
                    className="rounded border-jarvis-border accent-[#FF8C00] cursor-pointer"
                    checked={selected.has(lead.id)}
                    onChange={e => toggleSelect(lead.id, e)}
                  />
                </td>
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
                    {/* Mensaje de prospección */}
                    <button
                      onClick={e => handleProspect(lead, e)}
                      title="Generar mensaje de prospección"
                      className="p-1.5 rounded-lg hover:bg-[#FF8C00]/10 text-jarvis-muted
                                 hover:text-[#FF8C00] transition-colors">
                      <Sparkles size={13} />
                    </button>
                    {/* Agregar seguimiento */}
                    <button
                      onClick={e => { e.stopPropagation(); setFollowLead(lead); setFollowDate(tomorrow()) }}
                      title="Agendar seguimiento"
                      className="p-1.5 rounded-lg hover:bg-blue-500/10 text-jarvis-muted
                                 hover:text-blue-400 transition-colors">
                      <Calendar size={13} />
                    </button>
                    {/* Eliminar */}
                    <button
                      onClick={e => handleDelete(lead, e)}
                      title="Eliminar lead"
                      className="p-1.5 rounded-lg hover:bg-red-500/10 text-jarvis-muted
                                 hover:text-red-400 transition-colors">
                      <Trash2 size={13} />
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

      {/* ── Modal campaña masiva WA ── */}
      {showCampaign && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-jarvis-text flex items-center gap-2">
                  <Radio size={15} className="text-purple-400" /> Campaña WA masiva
                </h3>
                <p className="text-xs text-jarvis-muted mt-0.5">
                  {selected.size} lead{selected.size !== 1 ? 's' : ''} seleccionados
                </p>
              </div>
              <button onClick={() => { setShowCampaign(false); setCampaignProgress(null) }}
                disabled={campaignProgress && !campaignProgress.done}
                className="text-jarvis-muted hover:text-jarvis-text disabled:opacity-40">
                <X size={16} />
              </button>
            </div>

            {/* Lista de destinatarios */}
            <div className="max-h-32 overflow-y-auto space-y-1 bg-jarvis-surface rounded-lg p-2.5">
              {(leads ?? []).filter(l => selected.has(l.id)).map(l => (
                <div key={l.id} className="flex items-center gap-2 text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0" />
                  <span className="text-jarvis-text font-medium">{l.company_name}</span>
                  <span className="text-jarvis-muted">
                    {l.whatsapp || l.phone || '(sin contacto)'}
                  </span>
                </div>
              ))}
            </div>

            {/* Mensaje */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-jarvis-muted">
                Mensaje — usá <code className="bg-jarvis-surface px-1 rounded">{'{nombre}'}</code> y{' '}
                <code className="bg-jarvis-surface px-1 rounded">{'{empresa}'}</code> como variables
              </label>
              <textarea
                value={campaignMsg}
                onChange={e => setCampaignMsg(e.target.value)}
                rows={4}
                disabled={campaignProgress && !campaignProgress.done}
                className="field-input resize-none text-sm disabled:opacity-50"
              />
            </div>

            {/* Progreso */}
            {campaignProgress && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-jarvis-muted">
                  <span>{campaignProgress.done ? 'Campaña finalizada' : 'Enviando…'}</span>
                  <span>{campaignProgress.sent + campaignProgress.failed} / {campaignProgress.total}</span>
                </div>
                <div className="w-full bg-jarvis-surface rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300
                               ${campaignProgress.done ? 'bg-teal-500' : 'bg-purple-500 animate-pulse'}`}
                    style={{ width: `${((campaignProgress.sent + campaignProgress.failed) / campaignProgress.total) * 100}%` }}
                  />
                </div>
                <div className="flex gap-3 text-xs">
                  <span className="text-teal-400">✓ {campaignProgress.sent} enviados</span>
                  {campaignProgress.failed > 0 && (
                    <span className="text-red-400">✗ {campaignProgress.failed} fallidos</span>
                  )}
                </div>
              </div>
            )}

            {/* Botones */}
            {(!campaignProgress || campaignProgress.done) && (
              <div className="flex gap-2 pt-1">
                <button onClick={() => { setShowCampaign(false); setCampaignProgress(null) }}
                  className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                             text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                  {campaignProgress?.done ? 'Cerrar' : 'Cancelar'}
                </button>
                {!campaignProgress?.done && (
                  <button onClick={sendCampaign} disabled={!campaignMsg.trim()}
                    className="flex-1 px-3 py-2.5 bg-purple-500/15 hover:bg-purple-500/25 border
                               border-purple-500/30 rounded-xl text-sm text-purple-400 font-semibold
                               transition-colors disabled:opacity-40">
                    🤖 Enviar campaña
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toast envío OK */}
      {sentOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/15 border border-green-500/30
                        rounded-xl px-5 py-3 text-green-400 text-sm font-medium shadow-xl
                        cursor-pointer"
          onClick={() => setSentOk(false)}>
          Jarvis está enviando el mensaje por WhatsApp
        </div>
      )}

      {/* Toast import */}
      {importResult && (
        <div className={`fixed bottom-6 right-6 z-50 rounded-xl px-5 py-3 text-sm font-medium shadow-xl cursor-pointer
                        ${importResult.error
                          ? 'bg-red-500/15 border border-red-500/30 text-red-400'
                          : 'bg-teal-500/15 border border-teal-500/30 text-teal-400'}`}
          onClick={() => setImportResult(null)}>
          {importResult.error
            ? importResult.error
            : `✓ ${importResult.created} lead${importResult.created !== 1 ? 's' : ''} importados${importResult.skipped ? ` · ${importResult.skipped} omitidos` : ''}`}
        </div>
      )}

      {/* Toast seguimiento OK */}
      {followOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-blue-500/15 border border-blue-500/30
                        rounded-xl px-5 py-3 text-blue-400 text-sm font-medium shadow-xl
                        cursor-pointer"
          onClick={() => setFollowOk(false)}>
          Seguimiento agendado correctamente
        </div>
      )}

      {/* Modal seguimiento */}
      {followLead && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-jarvis-text">Agendar seguimiento</h3>
                <p className="text-xs text-jarvis-muted mt-0.5">{followLead.company_name}</p>
              </div>
              <button onClick={() => setFollowLead(null)} className="text-jarvis-muted hover:text-jarvis-text">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-jarvis-muted font-medium">Fecha del seguimiento</label>
              <input
                type="date"
                value={followDate}
                min={new Date().toISOString().slice(0, 10)}
                onChange={e => setFollowDate(e.target.value)}
                className="field-input"
              />
            </div>

            <div className="flex gap-2">
              <button onClick={() => setFollowLead(null)}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cancelar
              </button>
              <button
                onClick={() => followMutation.mutate({ id: followLead.id, date: followDate })}
                disabled={!followDate || followMutation.isPending}
                className="flex-1 px-3 py-2.5 bg-blue-500/15 hover:bg-blue-500/25 border
                           border-blue-500/30 rounded-xl text-sm text-blue-400 font-semibold
                           transition-colors disabled:opacity-40">
                {followMutation.isPending ? 'Guardando...' : 'Agendar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmar eliminación */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-red-500/30 rounded-xl w-full max-w-sm p-6 space-y-4">
            <h3 className="font-heading font-bold text-base text-jarvis-text">Eliminar lead</h3>
            <p className="text-sm text-jarvis-muted">
              ¿Eliminás <span className="text-jarvis-text font-semibold">{deleteTarget.company_name}</span>?
              Esta acción no se puede deshacer.
            </p>
            <div className="flex gap-2">
              <button onClick={() => setDeleteTarget(null)}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="flex-1 px-3 py-2.5 bg-red-500/15 hover:bg-red-500/25 border
                           border-red-500/30 rounded-xl text-sm text-red-400 font-semibold
                           transition-colors disabled:opacity-40">
                {deleting ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
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
