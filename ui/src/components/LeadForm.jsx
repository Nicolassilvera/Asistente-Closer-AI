// ui/src/components/LeadForm.jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { createLead } from '../api'

const ESTADOS = [
  'nuevo', 'analizado', 'contactado', 'respondio',
  'interesado', 'caliente', 'negociacion', 'cerrado', 'descartado'
]

const PRIORIDADES = ['alta', 'media', 'baja']

export default function LeadForm({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    company_name: '', contact_name: '', category: '',
    city: '', province: '', phone: '', whatsapp: '',
    email: '', instagram: '', website: '',
    source: 'manual', notes: '',
    lead_status: 'nuevo', priority: 'media',
    lead_score: 0, followup_date: '',
  })
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createLead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
      onClose()
    },
    onError: (e) => setError(e.message || 'Error al crear lead')
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = () => {
    if (!form.company_name.trim()) {
      setError('El nombre de la empresa es obligatorio')
      return
    }
    setError('')
    mutation.mutate(form)
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-2xl
                      max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-jarvis-border">
          <h2 className="text-lg font-semibold text-jarvis-text">Nuevo lead</h2>
          <button onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                       hover:text-jarvis-text transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5">

          {/* Empresa */}
          <div>
            <p className="text-xs font-medium text-jarvis-muted uppercase tracking-wider mb-3">
              Empresa
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Input label="Nombre de la empresa *"
                  value={form.company_name}
                  onChange={v => set('company_name', v)} />
              </div>
              <Input label="Contacto"
                value={form.contact_name}
                onChange={v => set('contact_name', v)} />
              <Input label="Rubro / Categoría"
                value={form.category}
                onChange={v => set('category', v)} />
              <Input label="Ciudad"
                value={form.city}
                onChange={v => set('city', v)} />
              <Input label="Provincia"
                value={form.province}
                onChange={v => set('province', v)} />
            </div>
          </div>

          {/* Contacto */}
          <div>
            <p className="text-xs font-medium text-jarvis-muted uppercase tracking-wider mb-3">
              Contacto
            </p>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Teléfono"
                value={form.phone}
                onChange={v => set('phone', v)} />
              <Input label="WhatsApp"
                value={form.whatsapp}
                onChange={v => set('whatsapp', v)} />
              <Input label="Email"
                value={form.email}
                onChange={v => set('email', v)} />
              <Input label="Instagram"
                value={form.instagram}
                onChange={v => set('instagram', v)} />
              <div className="col-span-2">
                <Input label="Sitio web"
                  value={form.website}
                  onChange={v => set('website', v)} />
              </div>
            </div>
          </div>

          {/* Clasificación */}
          <div>
            <p className="text-xs font-medium text-jarvis-muted uppercase tracking-wider mb-3">
              Clasificación
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-jarvis-muted mb-1 block">Estado</label>
                <select value={form.lead_status}
                  onChange={e => set('lead_status', e.target.value)}
                  className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                             rounded-lg text-sm text-jarvis-text focus:outline-none
                             focus:border-jarvis-purple">
                  {ESTADOS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-jarvis-muted mb-1 block">Prioridad</label>
                <select value={form.priority}
                  onChange={e => set('priority', e.target.value)}
                  className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                             rounded-lg text-sm text-jarvis-text focus:outline-none
                             focus:border-jarvis-purple">
                  {PRIORIDADES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-jarvis-muted mb-1 block">Score (0-10)</label>
                <input type="number" min="0" max="10" step="0.5"
                  value={form.lead_score}
                  onChange={e => set('lead_score', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                             rounded-lg text-sm text-jarvis-text focus:outline-none
                             focus:border-jarvis-purple" />
              </div>
              <div>
                <label className="text-xs text-jarvis-muted mb-1 block">Fuente</label>
                <select value={form.source}
                  onChange={e => set('source', e.target.value)}
                  className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                             rounded-lg text-sm text-jarvis-text focus:outline-none
                             focus:border-jarvis-purple">
                  {['manual','google_maps','facebook','instagram','google_organic','referido'].map(
                    s => <option key={s} value={s}>{s}</option>
                  )}
                </select>
              </div>
              <div>
                <label className="text-xs text-jarvis-muted mb-1 block">Seguimiento</label>
                <input type="date"
                  value={form.followup_date}
                  onChange={e => set('followup_date', e.target.value)}
                  className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                             rounded-lg text-sm text-jarvis-text focus:outline-none
                             focus:border-jarvis-purple" />
              </div>
            </div>
          </div>

          {/* Notas */}
          <div>
            <label className="text-xs text-jarvis-muted mb-1 block">Notas</label>
            <textarea value={form.notes}
              onChange={e => set('notes', e.target.value)}
              rows={3}
              placeholder="Observaciones, contexto, señales comerciales..."
              className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                         rounded-lg text-sm text-jarvis-text placeholder-jarvis-muted
                         focus:outline-none focus:border-jarvis-purple resize-none" />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-400/10 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-jarvis-border">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 border border-jarvis-border rounded-lg
                       text-sm text-jarvis-muted hover:bg-jarvis-surface transition-colors">
            Cancelar
          </button>
          <button onClick={handleSubmit}
            disabled={mutation.isPending}
            className="flex-1 px-4 py-2 bg-jarvis-purple hover:bg-purple-500
                       rounded-lg text-sm font-medium text-white transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed">
            {mutation.isPending ? 'Guardando...' : 'Guardar lead'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Input({ label, value, onChange, type = 'text' }) {
  return (
    <div>
      <label className="text-xs text-jarvis-muted mb-1 block">{label}</label>
      <input type={type} value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-jarvis-surface border border-jarvis-border
                   rounded-lg text-sm text-jarvis-text placeholder-jarvis-muted
                   focus:outline-none focus:border-jarvis-purple" />
    </div>
  )
}
