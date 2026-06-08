// ui/src/components/LeadForm.jsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { createLead } from '../api'

const ESTADOS     = ['nuevo','analizado','contactado','respondio','interesado','caliente','negociacion','cerrado','descartado']
const PRIORIDADES = ['alta','media','baja']
const FUENTES     = ['manual','google_maps','facebook','instagram','google_organic','referido']

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
    onError: (e) => setError(e.message || 'Error al crear lead'),
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const handleSubmit = () => {
    if (!form.company_name.trim()) { setError('El nombre de la empresa es obligatorio'); return }
    setError('')
    mutation.mutate(form)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-jarvis-card border border-jarvis-border rounded-xl w-full max-w-2xl my-4">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-jarvis-border">
          <h2 className="font-heading font-bold text-base text-jarvis-text">Nuevo lead</h2>
          <button onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-jarvis-border text-jarvis-muted
                       hover:text-jarvis-text transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">

          <Section label="Empresa">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <Field label="Nombre de la empresa *">
                  <input value={form.company_name} onChange={e => set('company_name', e.target.value)}
                    className="field-input" placeholder="Ej: Frigorífico Santa Rosa" />
                </Field>
              </div>
              <Field label="Persona de contacto">
                <input value={form.contact_name} onChange={e => set('contact_name', e.target.value)} className="field-input" />
              </Field>
              <Field label="Rubro">
                <input value={form.category} onChange={e => set('category', e.target.value)} className="field-input" />
              </Field>
              <Field label="Ciudad">
                <input value={form.city} onChange={e => set('city', e.target.value)} className="field-input" />
              </Field>
              <Field label="Provincia">
                <input value={form.province} onChange={e => set('province', e.target.value)} className="field-input" />
              </Field>
            </div>
          </Section>

          <Section label="Contacto">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Teléfono">
                <input value={form.phone} onChange={e => set('phone', e.target.value)} className="field-input" />
              </Field>
              <Field label="WhatsApp">
                <input value={form.whatsapp} onChange={e => set('whatsapp', e.target.value)}
                  className="field-input" placeholder="+5491100000000" />
              </Field>
              <Field label="Email">
                <input value={form.email} onChange={e => set('email', e.target.value)}
                  className="field-input" type="email" />
              </Field>
              <Field label="Instagram">
                <input value={form.instagram} onChange={e => set('instagram', e.target.value)}
                  className="field-input" placeholder="@usuario" />
              </Field>
              <div className="col-span-2">
                <Field label="Sitio web">
                  <input value={form.website} onChange={e => set('website', e.target.value)}
                    className="field-input" placeholder="https://..." />
                </Field>
              </div>
            </div>
          </Section>

          <Section label="Clasificación">
            <div className="grid grid-cols-3 gap-3">
              <Field label="Estado">
                <select value={form.lead_status} onChange={e => set('lead_status', e.target.value)} className="field-input">
                  {ESTADOS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Prioridad">
                <select value={form.priority} onChange={e => set('priority', e.target.value)} className="field-input">
                  {PRIORIDADES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </Field>
              <Field label="Score (0-10)">
                <input type="number" min={0} max={10} step={0.5}
                  value={form.lead_score} onChange={e => set('lead_score', parseFloat(e.target.value) || 0)}
                  className="field-input" />
              </Field>
              <Field label="Fuente">
                <select value={form.source} onChange={e => set('source', e.target.value)} className="field-input">
                  {FUENTES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Fecha de seguimiento">
                <input type="date" value={form.followup_date}
                  onChange={e => set('followup_date', e.target.value)} className="field-input" />
              </Field>
            </div>
          </Section>

          <Section label="Notas">
            <textarea value={form.notes} onChange={e => set('notes', e.target.value)}
              rows={3} placeholder="Observaciones, contexto, señales..."
              className="field-input resize-none" />
          </Section>

          {error && (
            <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 px-3 py-2 rounded-lg">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-6 py-4 border-t border-jarvis-border">
          <button onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-jarvis-border rounded-xl text-sm
                       text-jarvis-muted hover:bg-jarvis-surface transition-colors font-medium">
            Cancelar
          </button>
          <button onClick={handleSubmit} disabled={mutation.isPending}
            className="flex-1 px-4 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00] rounded-xl text-sm
                       font-semibold text-white transition-colors disabled:opacity-50 shadow-lg
                       shadow-[#FF8C00]/20">
            {mutation.isPending ? 'Guardando...' : 'Guardar lead'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Section({ label, children }) {
  return (
    <div className="space-y-3">
      <p className="text-[11px] font-semibold text-jarvis-muted uppercase tracking-widest">{label}</p>
      {children}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-jarvis-muted">{label}</label>
      {children}
    </div>
  )
}
