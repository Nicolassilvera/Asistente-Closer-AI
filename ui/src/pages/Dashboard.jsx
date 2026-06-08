// ui/src/pages/Dashboard.jsx
import { useQuery } from '@tanstack/react-query'
import { Users, Flame, Bell, TrendingUp, ArrowRight } from 'lucide-react'
import { getStats, getFollowups, getHotLeads } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

const STATUS_HEX = {
  nuevo:        '#6b7ff7',
  analizado:    '#8b8cf6',
  contactado:   '#eab308',
  respondio:    '#14b8a6',
  interesado:   '#22c55e',
  caliente:     '#FF8C00',
  negociacion:  '#ec4899',
  cerrado:      '#10b981',
  descartado:   '#4b5563',
}

function BarChart({ data }) {
  if (!data.length) return <p className="text-jarvis-muted text-sm">Sin datos.</p>
  const max = Math.max(...data.map(d => d.count), 1)
  return (
    <div className="space-y-2.5">
      {data.map(({ status, count }) => (
        <div key={status} className="flex items-center gap-3">
          <span className="text-xs text-jarvis-muted w-24 text-right truncate">{status}</span>
          <div className="flex-1 bg-jarvis-surface rounded-full h-5 overflow-hidden">
            <div
              className="h-full rounded-full flex items-center justify-end pr-2.5 transition-all duration-700"
              style={{
                width: `${(count / max) * 100}%`,
                backgroundColor: STATUS_HEX[status] ?? '#FF8C00',
                minWidth: count > 0 ? '2.5rem' : '0',
              }}>
              <span className="text-xs text-white font-semibold">{count}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function DonutChart({ data }) {
  if (!data.length) return <p className="text-jarvis-muted text-sm">Sin datos.</p>
  const total = data.reduce((s, d) => s + d.count, 0)
  let cumulative = 0
  const size = 160, radius = 58, cx = 80, cy = 80

  function polarXY(r, pct) {
    const rad = ((pct * 360 - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }
  function arc(startPct, endPct) {
    const s = polarXY(radius, startPct), e = polarXY(radius, endPct)
    const large = endPct - startPct > 0.5 ? 1 : 0
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`
  }

  const slices = data.map(d => {
    const pct = d.count / total, start = cumulative
    cumulative += pct
    return { ...d, pct, start }
  })

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} className="flex-shrink-0">
        {slices.map((s, i) => (
          <path key={i}
            d={arc(s.start, s.start + s.pct)}
            fill="none"
            stroke={STATUS_HEX[s.status] ?? '#FF8C00'}
            strokeWidth={20}
            strokeLinecap="butt"
          />
        ))}
        <text x={cx} y={cy - 7} textAnchor="middle" fill="#F0F0F0" fontSize={24} fontWeight="bold">
          {total}
        </text>
        <text x={cx} y={cy + 13} textAnchor="middle" fill="#9a9a9a" fontSize={10} fontFamily="Roboto">
          leads
        </text>
      </svg>
      <div className="flex flex-col gap-1.5 flex-1 min-w-0">
        {slices.filter(s => s.count > 0).map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: STATUS_HEX[s.status] ?? '#FF8C00' }} />
            <span className="text-jarvis-muted truncate">{s.status}</span>
            <span className="text-jarvis-text font-semibold ml-auto">{s.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard({ onNavigate }) {
  const { data: stats }     = useQuery({ queryKey: ['stats'],     queryFn: getStats,     refetchInterval: 10000 })
  const { data: hot }       = useQuery({ queryKey: ['hot'],       queryFn: getHotLeads,  refetchInterval: 10000 })
  const { data: followups } = useQuery({ queryKey: ['followups'], queryFn: getFollowups, refetchInterval: 10000 })

  const barData = stats?.by_status
    ? Object.entries(stats.by_status).map(([status, count]) => ({ status, count })).sort((a, b) => b.count - a.count)
    : []

  return (
    <div className="p-6 space-y-6">

      {/* Page header */}
      <div>
        <h1 className="font-heading font-bold text-2xl text-jarvis-text">Dashboard</h1>
        <p className="text-jarvis-muted text-sm mt-0.5">Resumen operativo en tiempo real</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total leads"      value={stats?.total}                           icon={Users}       color="orange" />
        <StatCard label="Leads calientes"  value={stats?.hot}                             icon={Flame}       color="red"    />
        <StatCard label="Seguimientos hoy" value={stats?.followups}                       icon={Bell}        color="amber"  />
        <StatCard label="En negociación"   value={stats?.by_status?.negociacion ?? 0}     icon={TrendingUp}  color="teal"   />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Leads por estado">
          <BarChart data={barData} />
        </Card>
        <Card title="Distribución">
          <DonutChart data={barData} />
        </Card>
      </div>

      {/* Listas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        <Card
          title="Leads calientes"
          icon={<Flame size={15} className="text-[#FF8C00]" />}
          action={onNavigate && (
            <button onClick={() => onNavigate('leads')}
              className="flex items-center gap-1 text-xs text-jarvis-muted hover:text-[#FF8C00] transition-colors">
              Ver todos <ArrowRight size={12} />
            </button>
          )}>
          {!hot?.length
            ? <p className="text-jarvis-muted text-sm">Sin leads calientes.</p>
            : hot.map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between py-2.5 border-b border-jarvis-border/50 last:border-0">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-jarvis-text truncate">{lead.company_name}</div>
                  <div className="text-xs text-jarvis-muted truncate">{[lead.city, lead.category].filter(Boolean).join(' · ')}</div>
                </div>
                <div className="flex items-center gap-2.5 ml-3 flex-shrink-0">
                  <span className="text-amber-400 font-bold text-xs">★ {lead.lead_score}</span>
                  <StatusBadge status={lead.lead_status} />
                </div>
              </div>
            ))
          }
        </Card>

        <Card
          title="Seguimientos pendientes"
          icon={<Bell size={15} className="text-amber-400" />}
          action={onNavigate && (
            <button onClick={() => onNavigate('followups')}
              className="flex items-center gap-1 text-xs text-jarvis-muted hover:text-amber-400 transition-colors">
              Ver todos <ArrowRight size={12} />
            </button>
          )}>
          {!followups?.length
            ? <p className="text-jarvis-muted text-sm">Sin seguimientos pendientes.</p>
            : followups.slice(0, 6).map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between py-2.5 border-b border-jarvis-border/50 last:border-0">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-jarvis-text truncate">{lead.company_name}</div>
                  <div className="text-xs text-amber-400/80">{lead.followup_date}</div>
                </div>
                <StatusBadge status={lead.lead_status} />
              </div>
            ))
          }
        </Card>
      </div>
    </div>
  )
}

function Card({ title, icon, action, children }) {
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-jarvis-text flex items-center gap-2">
          {icon}{title}
        </h2>
        {action}
      </div>
      <div className="space-y-0">{children}</div>
    </div>
  )
}
