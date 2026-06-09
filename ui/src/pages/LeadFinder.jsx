// ui/src/pages/LeadFinder.jsx
import { useState, useEffect, useRef } from 'react'
import { SearchCheck, Plus, CheckCircle, XCircle, Loader2, RotateCcw,
         Globe, AtSign, Link2, WifiOff, Sparkles, ChevronDown, ChevronUp } from 'lucide-react'
import { startLeadFind, getLeadFindStatus, analyzeFinderLead } from '../api'

const RUBROS = [
  'frigoríficos', 'carnicerías mayoristas', 'acopios de granos',
  'molinos harineros', 'silos y cereales', 'logística y distribución',
  'empresas de transporte', 'depósitos y almacenes', 'galpones industriales',
  'supermercados', 'hipermercados', 'mayoristas', 'distribuidoras',
  'plantas industriales', 'fábricas', 'industrias alimenticias',
  'laboratorios', 'cooperativas agropecuarias', 'feedlots', 'tambos',
  'pesca y mariscos', 'minería', 'químicas', 'empresas agroindustriales',
]

const ZONAS = [
  'Buenos Aires', 'CABA', 'La Plata', 'Mar del Plata', 'Bahía Blanca',
  'Quilmes', 'Lanús', 'Lomas de Zamora', 'Tigre', 'Morón',
  'Córdoba', 'Río Cuarto', 'Villa María',
  'Rosario', 'Santa Fe', 'Rafaela',
  'Mendoza', 'San Rafael',
  'Tucumán', 'Salta', 'Jujuy',
  'San Juan', 'San Luis',
  'Neuquén', 'Bariloche', 'Cipolletti',
  'Resistencia', 'Corrientes', 'Posadas',
  'Paraná', 'Concordia',
]

const WEB_FILTERS = [
  { key: 'social', label: 'Solo redes', desc: 'Usan Instagram o Facebook como web — oportunidad de prospección con datos completos', color: 'purple' },
  { key: 'none',   label: 'Sin web',    desc: 'Sin presencia digital — podés ofrecer soluciones tecnológicas', color: 'amber' },
  { key: 'web',    label: 'Con web propia', desc: 'Ya tienen sitio web propio', color: 'teal' },
]

const toggle = (list, setList, val) =>
  setList(prev => prev.includes(val) ? prev.filter(x => x !== val) : [...prev, val])

export default function LeadFinder() {
  const [selRubros,    setSelRubros]    = useState([])
  const [selZonas,     setSelZonas]     = useState([])
  const [maxResults,   setMaxResults]   = useState(10)
  const [customRubro,  setCustomRubro]  = useState('')
  const [customZona,   setCustomZona]   = useState('')
  const [webFilters,   setWebFilters]   = useState([])   // [] = todos
  const [jobId,        setJobId]        = useState(null)
  const [job,          setJob]          = useState(null)
  const [startError,   setStartError]   = useState('')
  const pollRef = useRef(null)

  const addCustom = (val, list, setList, setVal) => {
    const v = val.trim()
    if (v && !list.includes(v)) setList(prev => [...prev, v])
    setVal('')
  }

  const toggleWebFilter = (key) => {
    setWebFilters(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  const handleStart = async () => {
    setStartError('')
    if (!selRubros.length || !selZonas.length) {
      setStartError('Seleccioná al menos un rubro y una zona.')
      return
    }
    try {
      const wt   = webFilters.length > 0 ? webFilters : null
      const data = await startLeadFind(selRubros, selZonas, maxResults, wt)
      setJobId(data.id)
      setJob({ id: data.id, status: 'running', done: 0, total: data.total, found: 0, logs: [], leads: [] })
    } catch {
      setStartError('No se pudo iniciar la búsqueda. ¿Está Jarvis corriendo?')
    }
  }

  const handleReset = () => {
    clearInterval(pollRef.current)
    setJob(null)
    setJobId(null)
  }

  useEffect(() => {
    if (!jobId) return
    pollRef.current = setInterval(async () => {
      try {
        const data = await getLeadFindStatus(jobId)
        setJob(data)
        if (data.status === 'done') clearInterval(pollRef.current)
      } catch {}
    }, 2000)
    return () => clearInterval(pollRef.current)
  }, [jobId])

  const combos = selRubros.length * selZonas.length
  const isDone = job?.status === 'done'

  return (
    <div className="p-6 space-y-5 max-w-5xl">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#FF8C00]/15 flex items-center justify-center">
            <SearchCheck size={18} className="text-[#FF8C00]" />
          </div>
          <div>
            <h1 className="font-heading font-bold text-2xl text-jarvis-text">LeadFinder</h1>
            <p className="text-jarvis-muted text-xs mt-0.5">Prospección automática en Google Maps</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {combos > 0 && !job && (
            <span className="text-xs text-jarvis-muted bg-jarvis-card border border-jarvis-border px-3 py-1.5 rounded-full">
              {combos} combos · ~{combos * maxResults} leads
            </span>
          )}
          {isDone && (
            <button onClick={handleReset}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-jarvis-border
                         rounded-lg text-jarvis-muted hover:bg-jarvis-card hover:text-jarvis-text transition-colors">
              <RotateCcw size={12} /> Nueva búsqueda
            </button>
          )}
        </div>
      </div>

      {/* Configuración pre-búsqueda */}
      {!job && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <SelectorPanel
              title="Rubros"
              subtitle="¿Qué tipo de empresas buscás?"
              preset={RUBROS}
              selected={selRubros}
              onToggle={v => toggle(selRubros, setSelRubros, v)}
              customValue={customRubro}
              onCustomChange={setCustomRubro}
              onCustomAdd={() => addCustom(customRubro, selRubros, setSelRubros, setCustomRubro)}
              placeholder="Otro rubro..."
            />
            <SelectorPanel
              title="Zonas"
              subtitle="¿En qué ciudades o provincias?"
              preset={ZONAS}
              selected={selZonas}
              onToggle={v => toggle(selZonas, setSelZonas, v)}
              customValue={customZona}
              onCustomChange={setCustomZona}
              onCustomAdd={() => addCustom(customZona, selZonas, setSelZonas, setCustomZona)}
              placeholder="Otra zona..."
            />
          </div>

          {/* Filtros de presencia web */}
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5 space-y-3">
            <div>
              <h2 className="text-sm font-semibold text-jarvis-text">Filtrar por presencia web</h2>
              <p className="text-xs text-jarvis-muted mt-0.5">
                Seleccioná qué tipo de leads querés traer. Sin selección trae todos.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {WEB_FILTERS.map(f => {
                const active = webFilters.includes(f.key)
                const colors = {
                  purple: active ? 'bg-purple-500/15 border-purple-500/40 text-purple-400' : 'border-jarvis-border text-jarvis-muted hover:border-purple-500/30 hover:text-purple-400',
                  amber:  active ? 'bg-amber-500/15 border-amber-500/40 text-amber-400'    : 'border-jarvis-border text-jarvis-muted hover:border-amber-500/30 hover:text-amber-400',
                  teal:   active ? 'bg-teal-500/15 border-teal-500/40 text-teal-400'       : 'border-jarvis-border text-jarvis-muted hover:border-teal-500/30 hover:text-teal-400',
                }
                return (
                  <button
                    key={f.key}
                    onClick={() => toggleWebFilter(f.key)}
                    title={f.desc}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-medium transition-all ${colors[f.color]}`}>
                    {f.key === 'social' && <AtSign size={12} />}
                    {f.key === 'none'   && <WifiOff size={12} />}
                    {f.key === 'web'    && <Globe size={12} />}
                    {f.label}
                    {active && <span className="text-[10px] opacity-70">✓</span>}
                  </button>
                )
              })}
            </div>
            {webFilters.length > 0 && (
              <p className="text-[11px] text-jarvis-muted">
                Solo se guardarán leads con:
                {' '}<span className="text-jarvis-text font-medium">
                  {webFilters.map(k => WEB_FILTERS.find(f => f.key === k)?.label).join(' + ')}
                </span>
              </p>
            )}
          </div>

          {/* Controles */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2.5">
              <label className="text-sm text-jarvis-muted whitespace-nowrap">Resultados por búsqueda:</label>
              <input
                type="number" min={3} max={30} value={maxResults}
                onChange={e => setMaxResults(Number(e.target.value))}
                className="w-16 px-2 py-1.5 bg-jarvis-surface border border-jarvis-border rounded-lg
                           text-sm text-jarvis-text text-center focus:outline-none
                           focus:border-[#FF8C00]/50 transition-colors"
              />
            </div>
            <button
              onClick={handleStart}
              disabled={!selRubros.length || !selZonas.length}
              className="flex items-center gap-2 px-6 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00]
                         rounded-xl text-white font-semibold text-sm transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#FF8C00]/20">
              <SearchCheck size={15} /> Buscar leads
            </button>
            {startError && <span className="text-xs text-red-400">{startError}</span>}
          </div>
        </>
      )}

      {job && <JobView job={job} />}
    </div>
  )
}

// ── Componentes auxiliares ────────────────────────────────────────────────────

function SelectorPanel({ title, subtitle, preset, selected, onToggle, customValue, onCustomChange, onCustomAdd, placeholder }) {
  const customs = selected.filter(v => !preset.includes(v))
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-jarvis-text">{title}</h2>
        <p className="text-xs text-jarvis-muted mt-0.5">{subtitle}</p>
      </div>
      {customs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {customs.map(opt => (
            <button key={opt} onClick={() => onToggle(opt)}
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border
                         bg-teal-500/10 border-teal-500/40 text-teal-400 hover:border-teal-400
                         transition-colors font-medium">
              {opt} <span className="opacity-60 text-[10px]">×</span>
            </button>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
        {preset.map(opt => {
          const active = selected.includes(opt)
          return (
            <button key={opt} onClick={() => onToggle(opt)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors font-medium
                ${active
                  ? 'bg-[#FF8C00]/15 border-[#FF8C00]/40 text-[#FF8C00]'
                  : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80 hover:text-jarvis-text'
                }`}>
              {opt}
            </button>
          )
        })}
      </div>
      <div className="flex gap-2">
        <input
          value={customValue}
          onChange={e => onCustomChange(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onCustomAdd()}
          placeholder={placeholder}
          className="flex-1 px-3 py-1.5 bg-jarvis-surface border border-jarvis-border rounded-lg
                     text-xs text-jarvis-text placeholder-jarvis-muted/50
                     focus:outline-none focus:border-[#FF8C00]/50 transition-colors"
        />
        <button onClick={onCustomAdd}
          className="px-3 py-1.5 bg-jarvis-surface border border-jarvis-border rounded-lg
                     text-jarvis-muted hover:text-[#FF8C00] hover:border-[#FF8C00]/40 transition-colors">
          <Plus size={13} />
        </button>
      </div>
      {selected.length > 0 && (
        <p className="text-xs text-[#FF8C00] font-medium">
          {selected.length} seleccionado{selected.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}

function WebBadge({ webType, instagram, facebook }) {
  if (webType === 'social') {
    if (instagram) return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                       bg-purple-500/10 border border-purple-500/25 text-purple-400 font-medium">
        <AtSign size={10} /> {instagram}
      </span>
    )
    if (facebook) return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                       bg-blue-500/10 border border-blue-500/25 text-blue-400 font-medium">
        <Link2 size={10} /> Facebook
      </span>
    )
  }
  if (webType === 'web') return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                     bg-teal-500/10 border border-teal-500/25 text-teal-400 font-medium">
      <Globe size={10} /> Web propia
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                     bg-jarvis-surface border border-jarvis-border text-jarvis-muted">
      <WifiOff size={10} /> Sin web
    </span>
  )
}

function LeadRow({ lead }) {
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis,  setAnalysis]  = useState(null)
  const [expanded,  setExpanded]  = useState(false)

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setExpanded(true)
    try {
      const res = await analyzeFinderLead(lead)
      setAnalysis(res.analysis)
    } catch {
      setAnalysis('No se pudo generar el análisis. Verificá la API key de Groq en Ajustes.')
    } finally {
      setAnalyzing(false)
    }
  }

  const contact = lead.whatsapp || lead.phone || '—'
  const priorityColor = { alta: 'text-red-400', media: 'text-amber-400', baja: 'text-jarvis-muted' }

  return (
    <>
      <tr className="border-b border-jarvis-border/50 hover:bg-jarvis-surface/40 transition-colors">
        <td className="py-2.5 px-3">
          <div className="font-medium text-sm text-jarvis-text truncate max-w-[180px]">{lead.company_name}</div>
          <div className="text-[10px] text-jarvis-muted mt-0.5">{lead.city} · {lead.category}</div>
        </td>
        <td className="py-2.5 px-3 text-xs text-jarvis-muted">{contact}</td>
        <td className="py-2.5 px-3">
          <WebBadge webType={lead.web_type} instagram={lead.instagram} facebook={lead.facebook} />
        </td>
        <td className="py-2.5 px-3 text-xs font-semibold text-[#FF8C00]">★ {lead.lead_score ?? '—'}</td>
        <td className="py-2.5 px-3">
          <span className={`text-xs font-medium ${priorityColor[lead.priority] ?? 'text-jarvis-muted'}`}>
            {lead.priority ?? '—'}
          </span>
        </td>
        <td className="py-2.5 px-3">
          <div className="flex items-center gap-1.5">
            <button onClick={handleAnalyze} disabled={analyzing}
              className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg border
                         border-[#FF8C00]/30 text-[#FF8C00] hover:bg-[#FF8C00]/10
                         transition-colors disabled:opacity-50 whitespace-nowrap">
              {analyzing ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
              Analizar
            </button>
            {analysis && (
              <button onClick={() => setExpanded(e => !e)}
                className="text-jarvis-muted hover:text-jarvis-text transition-colors">
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            )}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-jarvis-border/30">
          <td colSpan={6} className="px-3 pb-3 pt-1">
            <div className="bg-jarvis-surface/60 border border-[#FF8C00]/20 rounded-lg p-3">
              {analyzing
                ? <div className="flex items-center gap-2 text-xs text-jarvis-muted">
                    <Loader2 size={12} className="animate-spin text-[#FF8C00]" />
                    Generando análisis con IA...
                  </div>
                : <p className="text-xs text-jarvis-text leading-relaxed">{analysis}</p>
              }
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

const RESULT_FILTERS = [
  { key: 'all',    label: 'Todos' },
  { key: 'social', label: 'Solo redes ★' },
  { key: 'none',   label: 'Sin web' },
  { key: 'web',    label: 'Con web' },
]

function LeadsTable({ leads }) {
  const [filter, setFilter] = useState('all')

  const counts = {
    all:    leads.length,
    social: leads.filter(l => l.web_type === 'social').length,
    none:   leads.filter(l => l.web_type === 'none').length,
    web:    leads.filter(l => l.web_type === 'web').length,
  }

  const filtered = filter === 'all' ? leads : leads.filter(l => l.web_type === filter)

  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden">
      <div className="flex items-center gap-1 p-3 border-b border-jarvis-border overflow-x-auto">
        {RESULT_FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg whitespace-nowrap
                        transition-colors font-medium border
                        ${filter === f.key
                          ? 'bg-[#FF8C00]/15 border-[#FF8C00]/30 text-[#FF8C00]'
                          : 'border-transparent text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-surface'
                        }`}>
            {f.label}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full
                              ${filter === f.key ? 'bg-[#FF8C00]/20 text-[#FF8C00]' : 'bg-jarvis-surface text-jarvis-muted'}`}>
              {counts[f.key]}
            </span>
          </button>
        ))}
      </div>

      {filtered.length === 0
        ? <div className="p-8 text-center text-jarvis-muted text-sm">Sin leads en este filtro.</div>
        : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-jarvis-border/50">
                  {['Empresa', 'Contacto', 'Web', 'Score', 'Prioridad', ''].map(h => (
                    <th key={h} className="text-left text-[10px] font-semibold text-jarvis-muted
                                          uppercase tracking-wider px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((lead, i) => <LeadRow key={i} lead={lead} />)}
              </tbody>
            </table>
          </div>
        )
      }
    </div>
  )
}

function JobView({ job }) {
  const pct    = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0
  const isDone = job.status === 'done'

  return (
    <div className="space-y-4">

      {/* Progreso */}
      <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            {isDone
              ? <CheckCircle size={18} className="text-green-400" />
              : <Loader2 size={18} className="text-[#FF8C00] animate-spin" />
            }
            <span className="font-semibold text-jarvis-text text-sm">
              {isDone ? 'Búsqueda completada' : 'Buscando leads...'}
            </span>
          </div>
          <span className="text-xs text-jarvis-muted">{job.done} / {job.total} combinaciones</span>
        </div>

        <div className="w-full bg-jarvis-surface rounded-full h-2.5 overflow-hidden">
          <div className="h-2.5 rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: isDone ? '#10b981' : 'linear-gradient(90deg, #FF8C00, #e07d00)' }} />
        </div>

        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-heading font-bold text-green-400">{job.found}</div>
            <div className="text-xs text-jarvis-muted">leads guardados</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-heading font-bold text-[#FF8C00]">{pct}%</div>
            <div className="text-xs text-jarvis-muted">completado</div>
          </div>
          {!isDone && <span className="text-xs text-jarvis-muted animate-pulse ml-auto">procesando...</span>}
        </div>
      </div>

      {/* Log (solo mientras corre) */}
      {job.logs.length > 0 && !isDone && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5">
          <h3 className="text-[11px] font-semibold text-jarvis-muted uppercase tracking-widest mb-3">Actividad</h3>
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {job.logs.map((log, i) => (
              <div key={i} className="flex items-center gap-2.5 text-xs py-1">
                {log.error
                  ? <XCircle size={13} className="text-red-400 flex-shrink-0" />
                  : <CheckCircle size={13} className="text-green-400 flex-shrink-0" />
                }
                <span className="flex-1 text-jarvis-muted">
                  <span className="text-jarvis-text font-medium">{log.cat}</span> en <span className="text-jarvis-text font-medium">{log.city}</span>
                </span>
                {log.error
                  ? <span className="text-red-400 truncate max-w-[140px]">{log.error}</span>
                  : <span className={`font-semibold ${log.found > 0 ? 'text-[#FF8C00]' : 'text-jarvis-muted'}`}>
                      {log.found} lead{log.found !== 1 ? 's' : ''}
                    </span>
                }
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabla de resultados */}
      {isDone && job.leads?.length > 0 && <LeadsTable leads={job.leads} />}

      {isDone && (!job.leads || job.leads.length === 0) && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-8 text-center">
          <p className="text-jarvis-muted text-sm">No se encontraron leads en esta búsqueda.</p>
        </div>
      )}
    </div>
  )
}
