// ui/src/pages/Dashboard.jsx
import { useQuery } from '@tanstack/react-query'
import { Users, Flame, Bell, TrendingUp } from 'lucide-react'
import { getStats, getFollowups, getHotLeads } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

const STATUS_COLORS = {
  nuevo:        'bg-purple-500',
  analizado:    'bg-violet-500',
  contactado:   'bg-yellow-500',
  respondio:    'bg-teal-500',
  interesado:   'bg-green-500',
  caliente:     'bg-orange-500',
  negociacion:  'bg-pink-500',
  cerrado:      'bg-emerald-500',
  descartado:   'bg-gray-500',
}

const STATUS_HEX = {
  nuevo:        '#7c6ff7',
  analizado:    '#8b5cf6',
  contactado:   '#eab308',
  respondio:    '#14b8a6',
  interesado:   '#22c55e',
  caliente:     '#f97316',
  negociacion:  '#ec4899',
  cerrado:      '#10b981',
  descartado:   '#6b7280',
}

function BarChart({ data }) {
  if (!data.length) return (
    <p className="text-jarvis-muted text-sm">Sin datos todavía.</p>
  )
  const max = Math.max(...data.map(d => d.count), 1)

  return (
    <div className="space-y-2">
      {data.map(({ status, count }) => (
        <div key={status} className="flex items-center gap-3">
          <span className="text-xs text-jarvis-muted w-24 text-right truncate">
            {status}
          </span>
          <div className="flex-1 bg-jarvis-surface rounded-full h-5 overflow-hidden">
            <div
              className="h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
              style={{
                width: `${(count / max) * 100}%`,
                backgroundColor: STATUS_HEX[status] ?? '#7c6ff7',
                minWidth: count > 0 ? '2rem' : '0'
              }}>
              <span className="text-xs text-white font-medium">{count}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function DonutChart({ data }) {
  if (!data.length) return (
    <p className="text-jarvis-muted text-sm">Sin datos todavía.</p>
  )

  const total = data.reduce((s, d) => s + d.count, 0)
  let cumulative = 0
  const size   = 160
  const radius = 60
  const cx     = size / 2
  const cy     = size / 2

  const slices = data.map(d => {
    const pct   = d.count / total
    const start = cumulative
    cumulative += pct
    return { ...d, pct, start }
  })

  function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  function arcPath(cx, cy, r, startPct, endPct) {
    const start    = polarToCartesian(cx, cy, r, startPct * 360)
    const end      = polarToCartesian(cx, cy, r, endPct * 360)
    const largeArc = endPct - startPct > 0.5 ? 1 : 0
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`
  }

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} className="flex-shrink-0">
        {slices.map((s, i) => (
          <path
            key={i}
            d={arcPath(cx, cy, radius, s.start, s.start + s.pct)}
            fill="none"
            stroke={STATUS_HEX[s.status] ?? '#7c6ff7'}
            strokeWidth={22}
            strokeLinecap="butt"
          />
        ))}
        <text x={cx} y={cy - 6} textAnchor="middle"
          fill="#e2e0f0" fontSize={22} fontWeight="bold">
          {total}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle"
          fill="#8884a8" fontSize={10}>
          leads
        </text>
      </svg>

      <div className="flex flex-col gap-1.5 flex-1 min-w-0">
        {slices.filter(s => s.count > 0).map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: STATUS_HEX[s.status] ?? '#7c6ff7' }} />
            <span className="text-jarvis-muted truncate">{s.status}</span>
            <span className="text-jarvis-text font-medium ml-auto">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: stats }     = useQuery({
    queryKey: ['stats'],     queryFn: getStats,     refetchInterval: 10000
  })
  const { data: hot }       = useQuery({
    queryKey: ['hot'],       queryFn: getHotLeads,  refetchInterval: 10000
  })
  const { data: followups } = useQuery({
    queryKey: ['followups'], queryFn: getFollowups, refetchInterval: 10000
  })

  const barData = stats?.by_status
    ? Object.entries(stats.by_status)
        .map(([status, count]) => ({ status, count }))
        .sort((a, b) => b.count - a.count)
    : []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-jarvis-text">Dashboard</h1>
        <p className="text-jarvis-muted text-sm">Resumen operativo en tiempo real</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total leads"
          value={stats?.total}       icon={Users}       color="purple" />
        <StatCard label="Leads calientes"
          value={stats?.hot}         icon={Flame}       color="coral"  />
        <StatCard label="Seguimientos hoy"
          value={stats?.followups}   icon={Bell}        color="amber"  />
        <StatCard label="En negociación"
          value={stats?.by_status?.negociacion ?? 0}
          icon={TrendingUp}                             color="teal"   />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-4">
            Leads por estado
          </h2>
          <BarChart data={barData} />
        </div>

        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-4">
            Distribución
          </h2>
          <DonutChart data={barData} />
        </div>
      </div>

      {/* Calientes + Seguimientos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
            <Flame size={16} className="text-orange-400" /> Leads calientes
          </h2>
          <div className="space-y-2">
            {!hot?.length && (
              <p className="text-jarvis-muted text-sm">Sin leads calientes por ahora.</p>
            )}
            {hot?.map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between p-3 rounded-lg
                           bg-jarvis-surface hover:bg-jarvis-border/30 transition-colors">
                <div>
                  <div className="text-sm font-medium text-jarvis-text">
                    {lead.company_name}
                  </div>
                  <div className="text-xs text-jarvis-muted">
                    {lead.city} · {lead.category}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-400 font-medium">
                    ★ {lead.lead_score}
                  </span>
                  <StatusBadge status={lead.lead_status} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
            <Bell size={16} className="text-amber-400" /> Seguimientos pendientes
          </h2>
          <div className="space-y-2">
            {!followups?.length && (
              <p className="text-jarvis-muted text-sm">Sin seguimientos pendientes.</p>
            )}
            {followups?.map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between p-3 rounded-lg
                           bg-jarvis-surface hover:bg-jarvis-border/30 transition-colors">
                <div>
                  <div className="text-sm font-medium text-jarvis-text">
                    {lead.company_name}
                  </div>
                  <div className="text-xs text-jarvis-muted">{lead.followup_date}</div>
                </div>
                <StatusBadge status={lead.lead_status} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}