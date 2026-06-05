// ui/src/pages/Dashboard.jsx
import { useQuery } from '@tanstack/react-query'
import { Users, Flame, Bell, TrendingUp } from 'lucide-react'
import { getStats, getFollowups, getHotLeads } from '../api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
const { data: stats }     = useQuery({ queryKey: ['stats'],     queryFn: getStats,     refetchInterval: 10000 })
const { data: hot }       = useQuery({ queryKey: ['hot'],       queryFn: getHotLeads,  refetchInterval: 10000 })
const { data: followups } = useQuery({ queryKey: ['followups'], queryFn: getFollowups, refetchInterval: 10000 })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-jarvis-text">Dashboard</h1>
        <p className="text-jarvis-muted text-sm">Resumen operativo en tiempo real</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total leads"      value={stats?.total}     icon={Users}      color="purple" />
        <StatCard label="Leads calientes"  value={stats?.hot}       icon={Flame}      color="coral"  />
        <StatCard label="Seguimientos hoy" value={stats?.followups} icon={Bell}       color="amber"  />
        <StatCard label="En negociación"   value={stats?.by_status?.negociacion ?? 0} icon={TrendingUp} color="teal" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leads calientes */}
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
            <Flame size={16} className="text-orange-400" /> Leads calientes
          </h2>
          <div className="space-y-2">
            {hot?.length === 0 && (
              <p className="text-jarvis-muted text-sm">Sin leads calientes por ahora.</p>
            )}
            {hot?.map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between p-3 rounded-lg
                           bg-jarvis-surface hover:bg-jarvis-border/30 transition-colors">
                <div>
                  <div className="text-sm font-medium text-jarvis-text">{lead.company_name}</div>
                  <div className="text-xs text-jarvis-muted">{lead.city} · {lead.category}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-400 font-medium">★ {lead.lead_score}</span>
                  <StatusBadge status={lead.lead_status} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Seguimientos pendientes */}
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-3 flex items-center gap-2">
            <Bell size={16} className="text-amber-400" /> Seguimientos pendientes
          </h2>
          <div className="space-y-2">
            {followups?.length === 0 && (
              <p className="text-jarvis-muted text-sm">Sin seguimientos pendientes.</p>
            )}
            {followups?.map(lead => (
              <div key={lead.id}
                className="flex items-center justify-between p-3 rounded-lg
                           bg-jarvis-surface hover:bg-jarvis-border/30 transition-colors">
                <div>
                  <div className="text-sm font-medium text-jarvis-text">{lead.company_name}</div>
                  <div className="text-xs text-jarvis-muted">{lead.followup_date}</div>
                </div>
                <StatusBadge status={lead.lead_status} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Estados */}
      {stats?.by_status && (
        <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4">
          <h2 className="text-sm font-medium text-jarvis-text mb-3">Leads por estado</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.by_status).map(([status, count]) => (
              <div key={status}
                className="flex items-center gap-2 px-3 py-1.5 bg-jarvis-surface rounded-lg">
                <StatusBadge status={status} />
                <span className="text-sm font-medium text-jarvis-text">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}