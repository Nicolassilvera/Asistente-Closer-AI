// ui/src/components/StatusBadge.jsx
const COLORS = {
  nuevo:               'bg-blue-500/20 text-blue-300 border-blue-500/30',
  analizado:           'bg-purple-500/20 text-purple-300 border-purple-500/30',
  contactado:          'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  respondio:           'bg-teal-500/20 text-teal-300 border-teal-500/30',
  interesado:          'bg-green-500/20 text-green-300 border-green-500/30',
  caliente:            'bg-orange-500/20 text-orange-300 border-orange-500/30',
  negociacion:         'bg-pink-500/20 text-pink-300 border-pink-500/30',
  cerrado:             'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  descartado:          'bg-gray-500/20 text-gray-400 border-gray-500/30',
  'seguimiento pendiente': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium
      ${COLORS[status] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30'}`}>
      {status}
    </span>
  )
}