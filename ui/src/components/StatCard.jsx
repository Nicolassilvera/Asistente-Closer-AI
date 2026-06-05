// ui/src/components/StatCard.jsx
export default function StatCard({ label, value, icon: Icon, color = 'purple' }) {
  const colors = {
    purple: 'text-purple-400 bg-purple-500/10',
    teal:   'text-teal-400 bg-teal-500/10',
    amber:  'text-amber-400 bg-amber-500/10',
    coral:  'text-red-400 bg-red-500/10',
  }
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-4 flex items-center gap-4">
      <div className={`p-2 rounded-lg ${colors[color]}`}>
        <Icon size={20} className={colors[color].split(' ')[0]} />
      </div>
      <div>
        <div className="text-2xl font-semibold text-jarvis-text">{value ?? '—'}</div>
        <div className="text-xs text-jarvis-muted">{label}</div>
      </div>
    </div>
  )
}