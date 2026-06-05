// ui/src/pages/Dashboard.jsx
import { useQuery } from '@tanstack/react-query'
import { Users, Flame, Bell, TrendingUp } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { getStats, getFollowups, getHotLeads } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

// Colores por estado
const STATUS_COLORS = {
  nuevo:               '#7c6ff7',
  analizado:           '#a855f7',
  contactado:          '#eab308',
  respondio:           '#14b8a6',
  interesado:          '#22c55e',
  caliente:            '#f97316',
  negociacion:         '#ec4899',
  cerrado:             '#10b981',
  descartado:          '#6b7280',
  'seguimiento pendiente': '#f59e0b',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-lg px-3 py-2 text-xs">
      <p className="text-jarvis-muted mb-1">{label}</p>
      <p className="text-jarvis-text font-medium">{payload[0].value} leads</p>
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

  // Datos para gráfico de barras — leads por estado
  const barData = stats?.by_status
    ? Object.entries(stats.by_status).map(([status, count]) => ({
        status,
        count,
        fill: STATUS_COLORS[status] ?? '#8884d8'
      }))
    : []

  // Datos para gráfico de torta — distribución
  const pieData = barData.filter(d => d.count > 0)

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-jarvis-text">Dashboard</h1>
        <p className="text-jarvis-muted text-sm">Resumen operativo en tiempo real</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total leads"
          value={stats?.total}
          icon={Users}
          color="purple" />
        <StatCard label="Leads calientes"
          value={stats?.hot}
          icon={Flame}
          color="coral" />
        <StatCard label="Seguimientos hoy"
          value={stats?.followups}
          icon={Bell}
          color="amber" />
        <StatCard label="En negociación"
          value={stats?.by_status?.negociacion ?? 0}
          icon={TrendingUp}
          color="teal" />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Barras — leads por estado */}
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-4">
            Leads por estado
          </h2>
          {barData.length === 0 ? (
            <p className="text-jarvis-muted text-sm">Sin datos todavía.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="status"
                  tick={{ fill: '#8884a8', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#8884a8', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#2e2e40' }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Torta — distribución */}
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-4">
            Distribución
          </h2>
          {pieData.length === 0 ? (
            <p className="text-jarvis-muted text-sm">Sin datos todavía.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [value, name]}
                  contentStyle={{
                    backgroundColor: '#22222f',
                    border: '1px solid #2e2e40',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => (
                    <span style={{ color: '#8884a8', fontSize: 11 }}>{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Leads calientes + Seguimientos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Calientes */}
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

        {/* Seguimientos */}
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
