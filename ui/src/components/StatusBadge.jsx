// ui/src/components/StatusBadge.jsx
const STATUS = {
  nuevo:       { dot: 'bg-blue-400',    cls: 'bg-blue-500/15 text-blue-300 border-blue-500/30' },
  analizado:   { dot: 'bg-slate-400',   cls: 'bg-slate-500/15 text-slate-300 border-slate-500/30' },
  contactado:  { dot: 'bg-yellow-400',  cls: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30' },
  respondio:   { dot: 'bg-teal-400',    cls: 'bg-teal-500/15 text-teal-300 border-teal-500/30' },
  interesado:  { dot: 'bg-green-400',   cls: 'bg-green-500/15 text-green-300 border-green-500/30' },
  caliente:    { dot: 'bg-[#FF8C00]',   cls: 'bg-[#FF8C00]/15 text-[#FF8C00] border-[#FF8C00]/40' },
  negociacion: { dot: 'bg-fuchsia-400', cls: 'bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30' },
  cerrado:     { dot: 'bg-emerald-400', cls: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  descartado:  { dot: 'bg-gray-600',    cls: 'bg-gray-500/10 text-gray-500 border-gray-500/20' },
}

export const STATUS_CONFIG = STATUS

export default function StatusBadge({ status }) {
  const cfg = STATUS[status] ?? STATUS.descartado
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      {status}
    </span>
  )
}