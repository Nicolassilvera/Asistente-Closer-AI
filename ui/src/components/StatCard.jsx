// ui/src/components/StatCard.jsx
const ACCENTS = {
  orange: { text: 'text-[#FF8C00]',  bg: 'bg-[#FF8C00]/10',  bar: 'bg-[#FF8C00]'  },
  teal:   { text: 'text-teal-400',   bg: 'bg-teal-400/10',   bar: 'bg-teal-400'   },
  amber:  { text: 'text-amber-400',  bg: 'bg-amber-400/10',  bar: 'bg-amber-400'  },
  red:    { text: 'text-red-400',    bg: 'bg-red-400/10',    bar: 'bg-red-400'    },
  purple: { text: 'text-[#FF8C00]',  bg: 'bg-[#FF8C00]/10',  bar: 'bg-[#FF8C00]'  },
  coral:  { text: 'text-red-400',    bg: 'bg-red-400/10',    bar: 'bg-red-400'    },
}

export default function StatCard({ label, value, icon: Icon, color = 'orange' }) {
  const a = ACCENTS[color] ?? ACCENTS.orange
  return (
    <div className={`relative bg-jarvis-card border border-jarvis-border rounded-xl p-5
                     overflow-hidden group hover:border-jarvis-border/80 transition-colors`}>
      <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${a.bar}`} />
      <div className="flex items-start justify-between">
        <div>
          <div className="text-3xl font-heading font-bold text-jarvis-text">
            {value ?? <span className="text-jarvis-muted">—</span>}
          </div>
          <div className="text-xs text-jarvis-muted mt-1 font-medium">{label}</div>
        </div>
        <div className={`p-2.5 rounded-xl ${a.bg} flex-shrink-0`}>
          <Icon size={18} className={a.text} />
        </div>
      </div>
    </div>
  )
}
