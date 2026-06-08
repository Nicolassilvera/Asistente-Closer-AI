// ui/src/pages/LeadFinder.jsx
import { useState, useEffect, useRef } from 'react'
import { SearchCheck, Plus, CheckCircle, XCircle, Loader2, RotateCcw } from 'lucide-react'
import { startLeadFind, getLeadFindStatus } from '../api'

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

const toggle = (list, setList, val) =>
  setList(prev => prev.includes(val) ? prev.filter(x => x !== val) : [...prev, val])

export default function LeadFinder() {
  const [selRubros,   setSelRubros]   = useState([])
  const [selZonas,    setSelZonas]    = useState([])
  const [maxResults,  setMaxResults]  = useState(10)
  const [customRubro, setCustomRubro] = useState('')
  const [customZona,  setCustomZona]  = useState('')
  const [jobId,       setJobId]       = useState(null)
  const [job,         setJob]         = useState(null)
  const [startError,  setStartError]  = useState('')
  const pollRef = useRef(null)

  const addCustom = (val, list, setList, setVal) => {
    const v = val.trim()
    if (v && !list.includes(v)) setList(prev => [...prev, v])
    setVal('')
  }

  const handleStart = async () => {
    setStartError('')
    if (!selRubros.length || !selZonas.length) {
      setStartError('Seleccioná al menos un rubro y una zona.')
      return
    }
    try {
      const data = await startLeadFind(selRubros, selZonas, maxResults)
      setJobId(data.id)
      setJob({ id: data.id, status: 'running', done: 0, total: data.total, found: 0, logs: [] })
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

  const combos    = selRubros.length * selZonas.length
  const isDone    = job?.status === 'done'

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

      {/* Config */}
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

      {/* Job activo o terminado */}
      {job && <JobView job={job} />}
    </div>
  )
}

function SelectorPanel({ title, subtitle, preset, selected, onToggle, customValue, onCustomChange, onCustomAdd, placeholder }) {
  const customs = selected.filter(v => !preset.includes(v))
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-jarvis-text">{title}</h2>
        <p className="text-xs text-jarvis-muted mt-0.5">{subtitle}</p>
      </div>

      {/* Custom chips arriba */}
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

      {/* Chips preset */}
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

      {/* Custom input */}
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
                     text-jarvis-muted hover:text-[#FF8C00] hover:border-[#FF8C00]/40
                     transition-colors">
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

function JobView({ job }) {
  const pct = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0
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
          <span className="text-xs text-jarvis-muted">
            {job.done} / {job.total} combinaciones
          </span>
        </div>

        {/* Barra */}
        <div className="w-full bg-jarvis-surface rounded-full h-2.5 overflow-hidden">
          <div
            className="h-2.5 rounded-full transition-all duration-700"
            style={{
              width: `${pct}%`,
              background: isDone
                ? '#10b981'
                : `linear-gradient(90deg, #FF8C00, #e07d00)`,
            }}
          />
        </div>

        {/* Resultado */}
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-heading font-bold text-green-400">{job.found}</div>
            <div className="text-xs text-jarvis-muted">leads encontrados</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-heading font-bold text-[#FF8C00]">{pct}%</div>
            <div className="text-xs text-jarvis-muted">completado</div>
          </div>
          {!isDone && (
            <span className="text-xs text-jarvis-muted animate-pulse ml-auto">procesando...</span>
          )}
        </div>
      </div>

      {/* Log */}
      {job.logs.length > 0 && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5">
          <h3 className="text-[11px] font-semibold text-jarvis-muted uppercase tracking-widest mb-3">
            Actividad
          </h3>
          <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
            {job.logs.map((log, i) => (
              <div key={i} className="flex items-center gap-2.5 text-xs py-1">
                {log.error
                  ? <XCircle size={13} className="text-red-400 flex-shrink-0" />
                  : <CheckCircle size={13} className="text-green-400 flex-shrink-0" />
                }
                <span className="flex-1 text-jarvis-muted">
                  <span className="text-jarvis-text font-medium">{log.cat}</span>
                  {' en '}
                  <span className="text-jarvis-text font-medium">{log.city}</span>
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
    </div>
  )
}
