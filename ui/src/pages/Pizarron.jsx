import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Plus, X, Trash2, MessageCircle, Package, Check, CircleDashed } from 'lucide-react'
import { getCalendarEvents, createCalendarEvent, updateCalendarEvent, deleteCalendarEvent,
         getPostits, createPostit, updatePostit, deletePostit,
         sendWhatsAppAndWait } from '../api'

// ── Productos predefinidos ────────────────────────────────────────────────────
const PRODUCTS = [
  'Balanza 40', 'Balanza 150', 'Balanza 300', 'Balanza 500',
  'Roku', 'R36s', 'J36 Ultra', 'Buds 3 Pro',
]

// ── Tipos de eventos ──────────────────────────────────────────────────────────
const EVENT_TYPES = {
  envio:        { label: 'Envío',        color: '#FF8C00', cls: 'bg-[#FF8C00]/15 text-[#FF8C00] border-[#FF8C00]/30',    sale: true  },
  retiro:       { label: 'Retiro',       color: '#14b8a6', cls: 'bg-teal-500/15 text-teal-400 border-teal-500/30',        sale: true  },
  recordatorio: { label: 'Recordatorio', color: '#3b82f6', cls: 'bg-blue-500/15 text-blue-400 border-blue-500/30',        sale: false },
  campaña:      { label: 'Campaña',      color: '#a855f7', cls: 'bg-purple-500/15 text-purple-400 border-purple-500/30',  sale: false },
  tarea:        { label: 'Tarea',        color: '#eab308', cls: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',  sale: false },
  venta:        { label: 'Venta',        color: '#22c55e', cls: 'bg-green-500/15 text-green-400 border-green-500/30',     sale: false },
}

// ── Post-it colors ────────────────────────────────────────────────────────────
const POSTIT_COLORS = {
  orange: 'bg-orange-500/20 border-orange-500/40 text-orange-100',
  blue:   'bg-blue-500/20   border-blue-500/40   text-blue-100',
  green:  'bg-green-500/20  border-green-500/40  text-green-100',
  yellow: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-100',
  pink:   'bg-pink-500/20   border-pink-500/40   text-pink-100',
}
const POSTIT_DOT_CLS = {
  orange: 'bg-orange-400', blue: 'bg-blue-400', green: 'bg-green-400',
  yellow: 'bg-yellow-400', pink: 'bg-pink-400',
}

// ── WhatsApp templates ────────────────────────────────────────────────────────
const buildWaMsg = (evt) => {
  if (evt.delivery_type === 'envio') {
    return `Hola buenas, te escribia para confirmar el ENVIO de hoy para ${evt.detail || '[dirección]'}, mas que nada así me voy organizando con el stock, muchas gracias.`
  }
  const prod = evt.product ? `${evt.product}${evt.quantity > 1 ? ` x${evt.quantity}` : ''}` : '[producto]'
  return `Hola buenas, te escribia para confirmar si hoy pasabas a retirar ${prod}, mas que nada para organizarme con el stock, muchas gracias.`
}

// ── Calendar helpers ──────────────────────────────────────────────────────────
const MONTHS = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const DAYS   = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']

function calGrid(year, month) {
  const first = new Date(year, month, 1).getDay()
  const total = new Date(year, month + 1, 0).getDate()
  const cells = []
  for (let i = 0; i < first; i++) cells.push(null)
  for (let d = 1; d <= total; d++) cells.push(d)
  return cells
}

function isoDate(year, month, day) {
  return `${year}-${String(month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`
}

const todayIso = () => new Date().toISOString().slice(0, 10)

// ── Input numérico inline ─────────────────────────────────────────────────────
function InlineNum({ value, onCommit }) {
  const [v, setV] = useState(String(value ?? ''))
  useEffect(() => { setV(String(value ?? '')) }, [value])
  return (
    <input
      type="number"
      value={v}
      placeholder="0"
      onChange={e => setV(e.target.value)}
      onBlur={() => {
        const n = parseFloat(v) || 0
        if (n !== (parseFloat(value) || 0)) onCommit(n)
      }}
      className="w-16 bg-transparent border-b border-jarvis-border/60 text-xs text-center
                 focus:outline-none focus:border-[#FF8C00] text-jarvis-text"
    />
  )
}

// ── Componente ────────────────────────────────────────────────────────────────
export default function Pizarron() {
  const qc    = useQueryClient()
  const today = new Date()

  const [year,  setYear]  = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selDay, setSelDay] = useState(todayIso())

  // Modal de evento
  const [showEvtModal, setShowEvtModal] = useState(false)
  const [evtType,      setEvtType]      = useState('retiro')
  const [evtProduct,   setEvtProduct]   = useState('')
  const [customProd,   setCustomProd]   = useState('')
  const [evtQty,       setEvtQty]       = useState(1)
  const [evtDetail,    setEvtDetail]    = useState('')
  const [evtContact,   setEvtContact]   = useState('')
  const [evtNotes,     setEvtNotes]     = useState('')
  const [evtDate,      setEvtDate]      = useState(todayIso())

  // Modal WA
  const [waEvt,    setWaEvt]    = useState(null)
  const [waMsg,    setWaMsg]    = useState('')
  // Tab del panel de día
  const [dayTab, setDayTab] = useState('eventos')  // 'eventos' | 'ventas'

  const [waSendingId, setWaSendingId] = useState(null)
  const [waOk,        setWaOk]        = useState(false)
  const [waError,     setWaError]     = useState(null)

  // Post-its
  const [postitInput, setPostitInput] = useState('')
  const [postitColor, setPostitColor] = useState('orange')
  const [editingId,   setEditingId]   = useState(null)
  const [editText,    setEditText]    = useState('')

  const monthStr = `${year}-${String(month + 1).padStart(2,'0')}`

  // Queries
  const { data: monthEvents = [] } = useQuery({
    queryKey: ['calendar', monthStr],
    queryFn: () => getCalendarEvents({ month: monthStr }),
  })
  const { data: dayEvents = [] } = useQuery({
    queryKey: ['calendar-day', selDay],
    queryFn: () => getCalendarEvents({ date: selDay }),
    enabled: !!selDay,
  })
  // Eventos completados del mes — fuente de Ventas
  const { data: completedEvents = [] } = useQuery({
    queryKey: ['calendar-completed', monthStr],
    queryFn: () => getCalendarEvents({ month: monthStr, completed: 1 }),
  })
  const { data: postits = [] } = useQuery({
    queryKey: ['postits'],
    queryFn: getPostits,
  })

  // Mutations — eventos
  const addEvent = useMutation({
    mutationFn: (data) => createCalendarEvent(data),
    onSuccess: () => {
      qc.invalidateQueries(['calendar'])
      qc.invalidateQueries(['calendar-day'])
      setShowEvtModal(false)
      resetEventForm()
    },
  })
  const patchEvent = useMutation({
    mutationFn: ({ id, ...data }) => updateCalendarEvent(id, data),
    onSuccess: () => {
      qc.invalidateQueries(['calendar'])
      qc.invalidateQueries(['calendar-day'])
      qc.invalidateQueries(['calendar-completed'])
    },
  })
  const delEvent = useMutation({
    mutationFn: (id) => deleteCalendarEvent(id),
    onSuccess: () => {
      qc.invalidateQueries(['calendar'])
      qc.invalidateQueries(['calendar-day'])
      qc.invalidateQueries(['calendar-completed'])
    },
  })

  // ── Ventas: retiros/envíos concretados agrupados por semana ───────────────
  const saleEvents = completedEvents.filter(e => EVENT_TYPES[e.type]?.sale)

  const getWeekRange = (iso) => {
    const d   = new Date(iso + 'T12:00')
    const day = d.getDay()
    const mon = new Date(d); mon.setDate(d.getDate() + (day === 0 ? -6 : 1 - day))
    const sun = new Date(mon); sun.setDate(mon.getDate() + 6)
    const fmt = (dt) => dt.toLocaleDateString('es-AR', { day:'2-digit', month:'2-digit' })
    return {
      start: mon.toISOString().slice(0, 10),
      end:   sun.toISOString().slice(0, 10),
      label: `${fmt(mon)} — ${fmt(sun)}`,
    }
  }
  const fmtPeso = (n) => n.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })

  const sortedSales = [...saleEvents].sort((a, b) => a.date.localeCompare(b.date))
  const weekGroupMap = {}
  sortedSales.forEach(evt => {
    const wr = getWeekRange(evt.date)
    if (!weekGroupMap[wr.start]) weekGroupMap[wr.start] = { ...wr, events: [] }
    weekGroupMap[wr.start].events.push(evt)
  })
  const weekGroups  = Object.values(weekGroupMap)
  const monthTotal  = saleEvents.reduce((a, e) => a + (e.price  || 0), 0)
  const monthProfit = saleEvents.reduce((a, e) => a + (e.profit || 0), 0)

  const resetEventForm = () => {
    setEvtType('retiro'); setEvtProduct(''); setCustomProd('')
    setEvtQty(1); setEvtDetail(''); setEvtContact(''); setEvtNotes('')
    setEvtDate(todayIso())
  }

  const openEvtModal = (date) => {
    setEvtDate(date || todayIso())
    setShowEvtModal(true)
  }

  const submitEvent = () => {
    const isSale = EVENT_TYPES[evtType]?.sale
    const product = evtProduct === '__custom__' ? customProd : evtProduct
    const title = isSale
      ? `${product || evtType}${evtQty > 1 ? ` x${evtQty}` : ''}`
      : (evtNotes || evtType)
    addEvent.mutate({
      title,
      date:          evtDate,
      type:          evtType,
      notes:         evtNotes || null,
      product:       isSale ? product : null,
      quantity:      isSale ? evtQty : 1,
      delivery_type: isSale ? evtType : null,
      detail:        evtDetail || null,
      contact:       evtContact || null,
    })
  }

  // WhatsApp
  const openWa = (evt) => {
    setWaEvt(evt)
    setWaMsg(buildWaMsg(evt))
  }
  const sendWa = async () => {
    if (!waEvt) return
    const contact   = waEvt._contact || waEvt.contact || ''
    const evtId     = waEvt.id
    const msgToSend = waMsg

    setWaEvt(null)
    setWaSendingId(evtId)
    setWaError(null)

    try {
      const result = await sendWhatsAppAndWait(contact, msgToSend, null)
      if (result?.success) {
        patchEvent.mutate({ id: evtId, wa_sent: true })
        setWaOk(true)
        setTimeout(() => setWaOk(false), 4000)
      } else {
        setWaError(result?.error || 'Jarvis no pudo enviar el mensaje por WhatsApp.')
      }
    } catch (e) {
      if (e.message === 'timeout') {
        setWaError('Sin respuesta de Jarvis en 90 segundos. Verificá que esté activo y que WhatsApp esté abierto.')
      } else {
        setWaError('Error de conexión con Jarvis. Intentá de nuevo.')
      }
    }
    setWaSendingId(null)
  }

  // Post-its mutations
  const addPostit = useMutation({
    mutationFn: () => createPostit({ content: postitInput, color: postitColor }),
    onSuccess: () => { qc.invalidateQueries(['postits']); setPostitInput('') },
  })
  const updPostit = useMutation({
    mutationFn: ({ id, content }) => updatePostit(id, { content }),
    onSuccess: () => { qc.invalidateQueries(['postits']); setEditingId(null) },
  })
  const delPostit = useMutation({
    mutationFn: (id) => deletePostit(id),
    onSuccess: () => qc.invalidateQueries(['postits']),
  })

  // Dots para la grilla
  const dotsByDay = {}
  monthEvents.forEach(e => {
    if (!dotsByDay[e.date]) dotsByDay[e.date] = []
    dotsByDay[e.date].push({ color: EVENT_TYPES[e.type]?.color ?? '#888', done: e.completed })
  })

  const cells = calGrid(year, month)

  const prevMonth = () => {
    if (month === 0) { setYear(y => y-1); setMonth(11) } else setMonth(m => m-1)
  }
  const nextMonth = () => {
    if (month === 11) { setYear(y => y+1); setMonth(0) } else setMonth(m => m+1)
  }

  const isSaleType = EVENT_TYPES[evtType]?.sale

  return (
    <div className="p-6 flex gap-5 h-full overflow-hidden">

      {/* ── Columna izquierda: Calendario ── */}
      <div className="flex-1 flex flex-col gap-4 overflow-y-auto">

        {/* Header */}
        <div className="flex items-center justify-between flex-shrink-0">
          <h1 className="font-heading font-bold text-2xl text-jarvis-text">Pizarrón</h1>
          <div className="flex items-center gap-3">
            <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-jarvis-card text-jarvis-muted hover:text-jarvis-text transition-colors">
              <ChevronLeft size={16} />
            </button>
            <span className="font-heading font-bold text-jarvis-text text-sm w-40 text-center">
              {MONTHS[month]} {year}
            </span>
            <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-jarvis-card text-jarvis-muted hover:text-jarvis-text transition-colors">
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Grilla del mes */}
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden flex-shrink-0">
          <div className="grid grid-cols-7 border-b border-jarvis-border">
            {DAYS.map(d => (
              <div key={d} className="py-2 text-center text-[10px] font-semibold text-jarvis-muted uppercase tracking-wide">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((day, i) => {
              if (!day) return <div key={`e${i}`} className="h-14 border-b border-r border-jarvis-border/30" />
              const iso     = isoDate(year, month, day)
              const dots    = dotsByDay[iso] || []
              const isToday = iso === todayIso()
              const isSel   = iso === selDay
              return (
                <div key={iso}
                  onClick={() => setSelDay(isSel ? null : iso)}
                  className={`h-14 border-b border-r border-jarvis-border/30 p-1.5 cursor-pointer
                              transition-colors hover:bg-jarvis-surface/70
                              ${isSel ? 'bg-[#FF8C00]/10 border-[#FF8C00]/20' : ''}`}>
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold mb-1
                                  ${isToday ? 'bg-[#FF8C00] text-white' : isSel ? 'text-[#FF8C00]' : 'text-jarvis-muted'}`}>
                    {day}
                  </div>
                  <div className="flex flex-wrap gap-0.5">
                    {dots.slice(0, 5).map((d, di) => (
                      <span key={di}
                        style={{ background: d.color, opacity: d.done ? 0.35 : 1 }}
                        className="w-1.5 h-1.5 rounded-full"
                        title={d.done ? 'Concretado' : undefined}
                      />
                    ))}
                    {dots.length > 5 && <span className="text-[9px] text-jarvis-muted">+{dots.length-5}</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Panel día seleccionado */}
        {selDay && (
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl overflow-hidden flex-shrink-0">

            {/* Header con fecha y tabs */}
            <div className="px-4 pt-3 pb-0 border-b border-jarvis-border">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-heading font-semibold text-sm text-jarvis-text">
                  {new Date(selDay + 'T12:00').toLocaleDateString('es-AR', {
                    weekday:'long', day:'numeric', month:'long'
                  })}
                </h3>
                {dayTab === 'eventos' && (
                  <button
                    onClick={() => openEvtModal(selDay)}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold
                               bg-[#FF8C00]/15 border border-[#FF8C00]/30 text-[#FF8C00]
                               rounded-lg hover:bg-[#FF8C00]/25 transition-colors">
                    <Plus size={11} /> Evento
                  </button>
                )}
              </div>
              {/* Tabs */}
              <div className="flex gap-1">
                {['eventos','ventas'].map(t => (
                  <button key={t} onClick={() => setDayTab(t)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-colors
                               ${dayTab === t
                                 ? 'bg-jarvis-bg text-jarvis-text border-t border-x border-jarvis-border -mb-px'
                                 : 'text-jarvis-muted hover:text-jarvis-text'
                               }`}>
                    {t === 'eventos'
                      ? `Eventos${dayEvents.length ? ` (${dayEvents.length})` : ''}`
                      : `Ventas${saleEvents.length ? ` (${saleEvents.length})` : ''}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab: Eventos */}
            {dayTab === 'eventos' && (
              dayEvents.length === 0
                ? <p className="text-xs text-jarvis-muted px-4 py-4">Sin eventos. Agregá uno.</p>
                : <div className="divide-y divide-jarvis-border/50">
                    {dayEvents.map(evt => {
                      const cfg    = EVENT_TYPES[evt.type] ?? EVENT_TYPES.tarea
                      const isSale = cfg.sale
                      return (
                        <div key={evt.id} className="px-4 py-3 flex items-start gap-3">
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border flex-shrink-0 mt-0.5 ${cfg.cls}`}>
                            {cfg.label}
                          </span>
                          <div className="flex-1 min-w-0">
                            {isSale ? (
                              <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                  <Package size={11} className="text-jarvis-muted flex-shrink-0" />
                                  <span className="text-sm font-semibold text-jarvis-text">
                                    {evt.product || evt.title}
                                    {evt.quantity > 1 && <span className="text-jarvis-muted font-normal ml-1">x{evt.quantity}</span>}
                                  </span>
                                </div>
                                {evt.detail  && <p className="text-xs text-jarvis-muted pl-4">{evt.delivery_type === 'envio' ? '📍' : '🕐'} {evt.detail}</p>}
                                {evt.contact && <p className="text-xs text-jarvis-muted pl-4">👤 {evt.contact}</p>}
                              </div>
                            ) : (
                              <p className="text-sm text-jarvis-text">{evt.title}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            {isSale && (
                              <button onClick={() => waSendingId !== evt.id && openWa(evt)}
                                disabled={waSendingId === evt.id}
                                title={waSendingId === evt.id ? 'Enviando...' : evt.wa_sent ? 'Enviado — reenviar' : 'Confirmar por WA'}
                                className={`relative p-1.5 rounded-lg transition-colors
                                           ${waSendingId === evt.id ? 'cursor-default text-amber-400'
                                             : evt.wa_sent ? 'text-green-400 hover:bg-green-500/10'
                                             : 'text-jarvis-muted hover:bg-green-500/10 hover:text-green-400'}`}>
                                {waSendingId === evt.id ? (
                                  <span className="flex gap-0.5 items-end h-[13px]">
                                    <span className="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style={{animationDelay:'0ms'}} />
                                    <span className="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style={{animationDelay:'160ms'}} />
                                    <span className="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style={{animationDelay:'320ms'}} />
                                  </span>
                                ) : (
                                  <>
                                    <MessageCircle size={13} />
                                    {evt.wa_sent && <span className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-green-400 border border-jarvis-card" />}
                                  </>
                                )}
                              </button>
                            )}
                            <button onClick={() => patchEvent.mutate({ id: evt.id, completed: !evt.completed })}
                              title={evt.completed ? 'Pendiente' : 'Concretado'}
                              className={`p-1.5 rounded-lg transition-colors ${evt.completed ? 'bg-green-500/15 text-green-400 hover:bg-green-500/25' : 'text-jarvis-muted hover:bg-jarvis-surface'}`}>
                              {evt.completed ? <Check size={13} /> : <CircleDashed size={13} />}
                            </button>
                            <button onClick={() => delEvent.mutate(evt.id)}
                              className="p-1.5 rounded-lg hover:bg-red-500/10 text-jarvis-muted hover:text-red-400 transition-colors">
                              <X size={12} />
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
            )}

            {/* Tab: Ventas — retiros/envíos concretados del mes, agrupados por semana */}
            {dayTab === 'ventas' && (
              saleEvents.length === 0
                ? <p className="text-xs text-jarvis-muted px-4 py-6 text-center">
                    Sin ventas concretadas este mes.<br/>
                    <span className="opacity-60">Marcá un retiro o envío como concretado para que aparezca aquí.</span>
                  </p>
                : (
                  <div className="divide-y divide-jarvis-border/30">
                    {weekGroups.map(wg => {
                      const wTotal  = wg.events.reduce((a, e) => a + (e.price  || 0), 0)
                      const wProfit = wg.events.reduce((a, e) => a + (e.profit || 0), 0)
                      return (
                        <div key={wg.start}>
                          {/* Cabecera de semana */}
                          <div className="px-4 py-2 bg-jarvis-surface/50 flex items-center justify-between">
                            <span className="text-[10px] font-semibold text-jarvis-muted uppercase tracking-wide">
                              Semana {wg.label}
                            </span>
                            <div className="flex gap-3 text-[10px]">
                              <span className="text-jarvis-muted">
                                ${fmtPeso(wTotal)}
                              </span>
                              <span className="text-green-400/80">
                                Gan ${fmtPeso(wProfit)}
                              </span>
                            </div>
                          </div>

                          {/* Filas de eventos */}
                          {wg.events.map(evt => {
                            const cfg = EVENT_TYPES[evt.type] ?? EVENT_TYPES.retiro
                            return (
                              <div key={evt.id}
                                className="px-4 py-2.5 flex items-center gap-2 hover:bg-jarvis-surface/30 transition-colors">
                                {/* Badge tipo */}
                                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full border flex-shrink-0 ${cfg.cls}`}>
                                  {cfg.label}
                                </span>
                                {/* Producto + contacto */}
                                <div className="flex-1 min-w-0">
                                  <span className="text-xs font-medium text-jarvis-text truncate block">
                                    {evt.product || evt.title}
                                    {evt.quantity > 1 && <span className="text-jarvis-muted font-normal ml-1">x{evt.quantity}</span>}
                                  </span>
                                  {evt.contact && (
                                    <span className="text-[10px] text-jarvis-muted">{evt.contact}</span>
                                  )}
                                </div>
                                {/* Fecha */}
                                <span className="text-[10px] text-jarvis-muted flex-shrink-0 w-11 text-center">
                                  {new Date(evt.date + 'T12:00').toLocaleDateString('es-AR', { day:'2-digit', month:'2-digit' })}
                                </span>
                                {/* Precio */}
                                <div className="flex flex-col items-center flex-shrink-0">
                                  <span className="text-[9px] text-jarvis-muted mb-0.5">$</span>
                                  <InlineNum
                                    value={evt.price}
                                    onCommit={v => patchEvent.mutate({ id: evt.id, price: v })}
                                  />
                                </div>
                                {/* Ganancia */}
                                <div className="flex flex-col items-center flex-shrink-0">
                                  <span className="text-[9px] text-green-400/70 mb-0.5">Gan</span>
                                  <InlineNum
                                    value={evt.profit}
                                    onCommit={v => patchEvent.mutate({ id: evt.id, profit: v })}
                                  />
                                </div>
                                {/* Toggle pago */}
                                <button
                                  onClick={() => patchEvent.mutate({
                                    id: evt.id,
                                    payment_method: evt.payment_method === 'efectivo' ? 'transferencia' : 'efectivo'
                                  })}
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border transition-colors flex-shrink-0
                                             ${evt.payment_method === 'efectivo'
                                               ? 'bg-green-500/15 border-green-500/30 text-green-400'
                                               : 'bg-blue-500/15 border-blue-500/30 text-blue-400'
                                             }`}>
                                  {evt.payment_method === 'efectivo' ? 'Ef' : 'Tr'}
                                </button>
                              </div>
                            )
                          })}
                        </div>
                      )
                    })}

                    {/* Total mensual */}
                    <div className="px-4 py-3 bg-[#FF8C00]/5 border-t border-[#FF8C00]/15 flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#FF8C00]/80">{MONTHS[month]} {year} — Total</span>
                      <div className="flex gap-5">
                        <div className="text-right">
                          <div className="text-[9px] text-jarvis-muted">Vendido</div>
                          <div className="text-sm font-bold text-jarvis-text">${fmtPeso(monthTotal)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[9px] text-jarvis-muted">Ganancia</div>
                          <div className="text-sm font-bold text-green-400">${fmtPeso(monthProfit)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[9px] text-jarvis-muted">Operaciones</div>
                          <div className="text-sm font-bold text-jarvis-muted">{saleEvents.length}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
            )}
          </div>
        )}

        {/* Leyenda */}
        <div className="flex flex-wrap gap-3 flex-shrink-0 pb-2">
          {Object.entries(EVENT_TYPES).map(([k, v]) => (
            <span key={k} className="flex items-center gap-1.5 text-[10px] text-jarvis-muted">
              <span style={{ background: v.color }} className="w-2 h-2 rounded-full" />
              {v.label}
            </span>
          ))}
        </div>
      </div>

      {/* ── Columna derecha: Post-its ── */}
      <div className="w-72 flex flex-col gap-4 overflow-hidden">

        <div className="flex items-center justify-between flex-shrink-0">
          <h2 className="font-heading font-bold text-base text-jarvis-text">Notas</h2>
        </div>

        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-3 space-y-2.5 flex-shrink-0">
          <textarea
            value={postitInput}
            onChange={e => setPostitInput(e.target.value)}
            placeholder="Nota rápida..."
            rows={2}
            className="field-input resize-none text-xs"
          />
          <div className="flex items-center justify-between">
            <div className="flex gap-1.5">
              {Object.entries(POSTIT_DOT_CLS).map(([color, cls]) => (
                <button key={color} onClick={() => setPostitColor(color)}
                  className={`w-4 h-4 rounded-full ${cls} transition-transform
                             ${postitColor === color ? 'scale-125 ring-2 ring-white/30' : 'hover:scale-110'}`} />
              ))}
            </div>
            <button onClick={() => addPostit.mutate()} disabled={!postitInput.trim()}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold
                         bg-[#FF8C00] hover:bg-[#e07d00] text-white rounded-lg
                         transition-colors disabled:opacity-40">
              <Plus size={11} /> Agregar
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
          {postits.length === 0 && (
            <p className="text-xs text-jarvis-muted text-center py-3">Sin notas.</p>
          )}
          {postits.map(p => (
            <div key={p.id} className={`border rounded-xl p-3 ${POSTIT_COLORS[p.color] ?? POSTIT_COLORS.orange}`}>
              {editingId === p.id ? (
                <div className="space-y-2">
                  <textarea autoFocus value={editText} onChange={e => setEditText(e.target.value)}
                    rows={3} className="w-full bg-black/20 border border-white/20 rounded-lg px-2 py-1.5
                                       text-xs resize-none focus:outline-none text-inherit" />
                  <div className="flex gap-1.5">
                    <button onClick={() => updPostit.mutate({ id: p.id, content: editText })}
                      className="flex-1 text-[10px] py-1 bg-white/15 hover:bg-white/25 rounded-md font-semibold transition-colors">
                      Guardar
                    </button>
                    <button onClick={() => setEditingId(null)}
                      className="flex-1 text-[10px] py-1 hover:bg-black/20 rounded-md transition-colors">
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <p className="flex-1 text-xs leading-relaxed whitespace-pre-wrap cursor-pointer"
                    onClick={() => { setEditingId(p.id); setEditText(p.content) }}>
                    {p.content}
                  </p>
                  <button onClick={() => delPostit.mutate(p.id)} className="opacity-40 hover:opacity-80 flex-shrink-0 mt-0.5">
                    <Trash2 size={11} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Modal: Crear evento ── */}
      {showEvtModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-md p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-base text-jarvis-text">Nuevo evento</h3>
              <button onClick={() => { setShowEvtModal(false); resetEventForm() }} className="text-jarvis-muted hover:text-jarvis-text">
                <X size={15} />
              </button>
            </div>

            {/* Tipo */}
            <div className="space-y-1">
              <label className="text-xs text-jarvis-muted font-medium">Tipo</label>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(EVENT_TYPES).map(([k, v]) => (
                  <button key={k} onClick={() => setEvtType(k)}
                    className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors
                               ${evtType === k ? v.cls : 'border-jarvis-border text-jarvis-muted hover:border-jarvis-border/80'}`}>
                    {v.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Campos para retiro/envío */}
            {isSaleType ? (
              <>
                <div className="space-y-1">
                  <label className="text-xs text-jarvis-muted font-medium">Producto</label>
                  <select value={evtProduct} onChange={e => setEvtProduct(e.target.value)} className="field-input">
                    <option value="">— Seleccionar —</option>
                    {PRODUCTS.map(p => <option key={p} value={p}>{p}</option>)}
                    <option value="__custom__">Otro (especificar)...</option>
                  </select>
                  {evtProduct === '__custom__' && (
                    <input value={customProd} onChange={e => setCustomProd(e.target.value)}
                      placeholder="Nombre del producto" className="field-input mt-1.5" />
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs text-jarvis-muted font-medium">Cantidad</label>
                    <input type="number" min={1} value={evtQty}
                      onChange={e => setEvtQty(parseInt(e.target.value) || 1)}
                      className="field-input" />
                  </div>
                  <div className="col-span-2 space-y-1">
                    <label className="text-xs text-jarvis-muted font-medium">
                      {evtType === 'envio' ? 'Dirección' : 'Horario'}
                    </label>
                    <input value={evtDetail} onChange={e => setEvtDetail(e.target.value)}
                      placeholder={evtType === 'envio' ? 'Av. Corrientes 1234' : '15:30 hs'}
                      className="field-input" />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs text-jarvis-muted font-medium">Contacto WhatsApp (opcional)</label>
                  <input value={evtContact} onChange={e => setEvtContact(e.target.value)}
                    placeholder="Nombre o número para confirmar" className="field-input" />
                </div>
              </>
            ) : (
              <div className="space-y-1">
                <label className="text-xs text-jarvis-muted font-medium">Descripción</label>
                <input autoFocus value={evtNotes} onChange={e => setEvtNotes(e.target.value)}
                  placeholder="¿Qué hay que hacer?" className="field-input"
                  onKeyDown={e => e.key === 'Enter' && submitEvent()} />
              </div>
            )}

            {/* Fecha */}
            <div className="space-y-1">
              <label className="text-xs text-jarvis-muted font-medium">Fecha</label>
              <input type="date" value={evtDate} onChange={e => setEvtDate(e.target.value)} className="field-input" />
            </div>

            <div className="flex gap-2 pt-1">
              <button onClick={() => { setShowEvtModal(false); resetEventForm() }}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cancelar
              </button>
              <button onClick={submitEvent} disabled={addEvent.isPending}
                className="flex-1 px-3 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00] rounded-xl text-sm
                           text-white font-semibold transition-colors disabled:opacity-40">
                {addEvent.isPending ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal WA confirmación ── */}
      {waEvt && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-jarvis-text">Confirmar por WhatsApp</h3>
                <p className="text-xs text-jarvis-muted mt-0.5">
                  {waEvt.product || waEvt.title} · {EVENT_TYPES[waEvt.delivery_type]?.label ?? waEvt.type}
                  {waEvt.detail && ` · ${waEvt.detail}`}
                </p>
              </div>
              <button onClick={() => setWaEvt(null)} className="text-jarvis-muted hover:text-jarvis-text">
                <X size={16} />
              </button>
            </div>

            <textarea value={waMsg} onChange={e => setWaMsg(e.target.value)}
              rows={5} className="field-input resize-none" />

            {!waEvt.contact && (
              <div className="space-y-1">
                <label className="text-xs text-jarvis-muted font-medium">Contacto WhatsApp</label>
                <input
                  value={waEvt._contact ?? ''}
                  onChange={e => setWaEvt(prev => ({ ...prev, _contact: e.target.value }))}
                  placeholder="Nombre o número"
                  className="field-input"
                />
              </div>
            )}

            <div className="flex gap-2">
              <button onClick={() => setWaEvt(null)}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Cerrar
              </button>
              <button onClick={() => { navigator.clipboard.writeText(waMsg) }}
                className="flex-1 px-3 py-2.5 border border-jarvis-border rounded-xl text-sm
                           text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
                Copiar
              </button>
              <button onClick={sendWa}
                className="flex-1 px-3 py-2.5 bg-green-500/15 hover:bg-green-500/25 border
                           border-green-500/30 rounded-xl text-sm text-green-400 font-semibold
                           transition-colors">
                🤖 Jarvis WA
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Popup error WA */}
      {waError && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60] p-4">
          <div className="bg-jarvis-card border border-red-500/40 rounded-xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                <X size={16} className="text-red-400" />
              </div>
              <div>
                <h3 className="font-heading font-bold text-base text-jarvis-text">Mensaje no enviado</h3>
                <p className="text-sm text-jarvis-muted mt-1 leading-relaxed">{waError}</p>
              </div>
            </div>
            <button
              onClick={() => setWaError(null)}
              className="w-full px-3 py-2.5 bg-red-500/15 hover:bg-red-500/25 border border-red-500/30
                         rounded-xl text-sm text-red-400 font-semibold transition-colors">
              Entendido
            </button>
          </div>
        </div>
      )}

      {/* Toast WA OK */}
      {waOk && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/15 border border-green-500/30
                        rounded-xl px-5 py-3 text-green-400 text-sm font-medium shadow-xl cursor-pointer"
          onClick={() => setWaOk(false)}>
          Jarvis está enviando la confirmación por WhatsApp
        </div>
      )}
    </div>
  )
}
