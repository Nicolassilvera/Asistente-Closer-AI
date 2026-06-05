// ui/src/pages/Leads.jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Phone, MessageCircle } from 'lucide-react'
import { getLeads, updateStatus } from '../api'
import StatusBadge from '../components/StatusBadge'
import LeadForm from '../components/LeadForm'
import LeadDetail from './LeadDetail'

const STATUSES = [
  'nuevo','analizado','contactado','respondio',
  'interesado','caliente','negociacion','cerrado','descartado'
]

export default function Leads() {
  const qc                      = useQueryClient()
  const [search, setSearch]     = useState('')
  const [filter, setFilter]     = useState('')
  const [showForm, setShowForm] = useState(false)
  const [selectedId, setSelectedId] = useState(null)

  const { data: leads, isLoading } = useQuery({
    queryKey: ['leads', search, filter],
    queryFn:  () => getLeads({ search: search || undefined, status: filter || undefined }),
    refetchInterval: 10000,
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => updateStatus(id, status),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['leads'] })
  })

  // Si hay un lead seleccionado, mostrar el detalle
  if (selectedId) {
    return <LeadDetail leadId={selectedId} onBack={() => setSelectedId(null)} />
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-jarvis-text">Leads</h1>
          <p className="text-jarvis-muted text-sm">{leads?.length ?? 0} prospectos</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-jarvis-purple
                     hover:bg-purple-500 rounded-lg text-sm font-medium
                     text-white transition-colors">
          <Plus size={16} /> Nuevo lead
        </button>
      </div>

      {/* Filtros */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-muted" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por nombre, ciudad, rubro..."
            className="w-full pl-9 pr-4 py-2 bg-jarvis-card border border-jarvis-border
                       rounded-lg text-sm text-jarvis-text placeholder-jarvis-muted
                       focus:outline-none focus:border-jarvis-purple"
          />
        </div>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="px-3 py-2 bg-jarvis-card border border-jarvis-border rounded-lg
                     text-sm text-jarvis-text focus:outline-none focus:border-jarvis-purple">
          <option value="">Todos los estados</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Tabla */}
      <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-jarvis-border">
              {['Empresa','Ciudad','Categoría','Score','Estado','Acciones'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-medium
                                       text-jarvis-muted uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-jarvis-border">
            {isLoading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-jarvis-muted">
                Cargando...
              </td></tr>
            )}
            {!isLoading && leads?.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-jarvis-muted">
                No hay leads todavía.
              </td></tr>
            )}
            {leads?.map(lead => (
              <tr key={lead.id}
                onClick={() => setSelectedId(lead.id)}
                className="hover:bg-jarvis-surface/50 transition-colors cursor-pointer">
                <td className="px-4 py-3">
                  <div className="font-medium text-jarvis-text">{lead.company_name}</div>
                  {lead.contact_name && (
                    <div className="text-xs text-jarvis-muted">{lead.contact_name}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-jarvis-muted">
                  {lead.city ?? '—'}
                </td>
                <td className="px-4 py-3 text-sm text-jarvis-muted">
                  {lead.category ?? '—'}
                </td>
                <td className="px-4 py-3">
                  <span className="text-amber-400 font-medium text-sm">
                    ★ {lead.lead_score ?? 0}
                  </span>
                </td>
                <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                  <select
                    value={lead.lead_status}
                    onChange={e => statusMutation.mutate({ id: lead.id, status: e.target.value })}
                    className="bg-transparent text-xs focus:outline-none cursor-pointer">
                    {STATUSES.map(s => (
                      <option key={s} value={s} className="bg-jarvis-card">{s}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    {lead.phone && (
                      <a href={`tel:${lead.phone}`}
                        className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                                   hover:text-teal-400 transition-colors">
                        <Phone size={14} />
                      </a>
                    )}
                    {lead.whatsapp && (
                      <a href={`https://wa.me/${lead.whatsapp.replace(/\D/g,'')}`}
                        target="_blank" rel="noreferrer"
                        className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                                   hover:text-green-400 transition-colors">
                        <MessageCircle size={14} />
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && <LeadForm onClose={() => setShowForm(false)} />}
    </div>
  )
}
