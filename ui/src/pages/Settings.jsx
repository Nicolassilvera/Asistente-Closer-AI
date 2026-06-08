import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Eye, EyeOff, Building2, Key, Clock, Zap, Mic } from 'lucide-react'
import { getSettings, updateSettings } from '../api'

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-jarvis-card border border-jarvis-border rounded-xl p-5 space-y-4">
      <h2 className="font-heading font-semibold text-sm text-jarvis-text flex items-center gap-2">
        <Icon size={15} className="text-[#FF8C00]" /> {title}
      </h2>
      {children}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-jarvis-muted">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-jarvis-muted/60">{hint}</p>}
    </div>
  )
}

function ApiKeyInput({ value, onChange, placeholder = 'sk-...' }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="field-input pr-10"
      />
      <button
        type="button"
        onClick={() => setShow(s => !s)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-jarvis-muted hover:text-jarvis-text transition-colors">
        {show ? <EyeOff size={13} /> : <Eye size={13} />}
      </button>
    </div>
  )
}

const EDGE_VOICES = [
  { value: 'es-MX-JorgeNeural',     label: 'Jorge — México (masculino)' },
  { value: 'es-MX-DaliaNeural',     label: 'Dalia — México (femenino)' },
  { value: 'es-AR-TomasNeural',     label: 'Tomás — Argentina (masculino)' },
  { value: 'es-AR-ElenaNeural',     label: 'Elena — Argentina (femenino)' },
  { value: 'es-ES-AlvaroNeural',    label: 'Álvaro — España (masculino)' },
  { value: 'es-ES-ElviraNeural',    label: 'Elvira — España (femenino)' },
]

export default function Settings() {
  const qc = useQueryClient()
  const { data: saved, isLoading } = useQuery({ queryKey: ['settings'], queryFn: getSettings })

  const [form, setForm] = useState({
    company_name:        '',
    monitor_interval:    '5',
    auto_followup:       '0',
    groq_api_key:        '',
    gemini_api_key:      '',
    elevenlabs_api_key:  '',
    elevenlabs_voice_id: '',
    edge_tts_voice:      'es-MX-JorgeNeural',
  })

  useEffect(() => {
    if (saved) setForm(f => ({ ...f, ...saved }))
  }, [saved])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const saveMutation = useMutation({
    mutationFn: () => updateSettings(form),
    onSuccess: (data) => {
      qc.setQueryData(['settings'], data)
      setSavedOk(true)
      setTimeout(() => setSavedOk(false), 2500)
    },
  })
  const [savedOk, setSavedOk] = useState(false)

  if (isLoading) return (
    <div className="p-8 text-jarvis-muted text-sm">Cargando ajustes…</div>
  )

  const hasElevenLabs = !!form.elevenlabs_api_key

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div>
        <h1 className="font-heading font-bold text-2xl text-jarvis-text">Ajustes</h1>
        <p className="text-jarvis-muted text-sm mt-0.5">Configuración general de Jarvis CRM</p>
      </div>

      {/* Empresa */}
      <Section icon={Building2} title="Empresa">
        <Field label="Nombre de la empresa" hint="Se muestra en el sidebar y en los reportes.">
          <input
            value={form.company_name}
            onChange={e => set('company_name', e.target.value)}
            className="field-input"
            placeholder="Mi Empresa"
          />
        </Field>
      </Section>

      {/* Monitor WA */}
      <Section icon={Clock} title="Monitor WhatsApp">
        <Field label="Intervalo de chequeo (minutos)" hint="Cada cuántos minutos Jarvis revisa mensajes nuevos.">
          <input
            type="number"
            min={1}
            max={60}
            value={form.monitor_interval}
            onChange={e => set('monitor_interval', e.target.value)}
            className="field-input w-32"
          />
        </Field>
      </Section>

      {/* Auto-seguimiento */}
      <Section icon={Zap} title="Seguimiento automático">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-jarvis-text font-medium">Enviar WA automático al llegar la fecha</p>
            <p className="text-xs text-jarvis-muted mt-0.5">
              Cuando un lead tiene fecha de seguimiento = hoy, Jarvis le manda el mensaje sin que tengas que hacerlo vos.
            </p>
          </div>
          <button
            onClick={() => set('auto_followup', form.auto_followup === '1' ? '0' : '1')}
            className={`w-11 h-6 rounded-full relative transition-colors flex-shrink-0 ml-4
                        ${form.auto_followup === '1' ? 'bg-[#FF8C00]' : 'bg-jarvis-border'}`}>
            <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all
                             ${form.auto_followup === '1' ? 'left-[22px]' : 'left-0.5'}`} />
          </button>
        </div>
      </Section>

      {/* Voz */}
      <Section icon={Mic} title="Voz">

        {/* Proveedor activo */}
        <div className="flex items-center gap-3">
          <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold
                           ${hasElevenLabs
                             ? 'bg-purple-500/15 text-purple-400 border border-purple-500/25'
                             : 'bg-teal-500/15 text-teal-400 border border-teal-500/25'}`}>
            {hasElevenLabs ? '★ ElevenLabs activo' : '✓ Edge TTS activo (gratis)'}
          </span>
          <span className="text-[10px] text-jarvis-muted">
            {hasElevenLabs
              ? 'ElevenLabs tiene prioridad sobre Edge TTS'
              : 'Jarvis habla con voz neural de Microsoft, sin costo'}
          </span>
        </div>

        {/* Edge TTS — voz */}
        <Field
          label="Voz de Edge TTS"
          hint="Voz gratuita de Microsoft. Funciona sin ninguna cuenta ni API key.">
          <select
            value={form.edge_tts_voice}
            onChange={e => set('edge_tts_voice', e.target.value)}
            className="field-input">
            {EDGE_VOICES.map(v => (
              <option key={v.value} value={v.value}>{v.label}</option>
            ))}
          </select>
        </Field>

        {/* Separador ElevenLabs */}
        <div className="border-t border-jarvis-border pt-3 space-y-3">
          <div>
            <p className="text-xs font-semibold text-jarvis-text">ElevenLabs — voz premium (opcional)</p>
            <p className="text-[10px] text-jarvis-muted mt-0.5">
              Voz ultrarrealista. Gratis hasta 10.000 caracteres/mes.
              Creá tu cuenta en <span className="text-[#FF8C00]">elevenlabs.io</span> → My Account → API Key.
              El Voice ID lo encontrás en la página de cada voz.
            </p>
          </div>

          <Field label="ElevenLabs API Key">
            <ApiKeyInput
              value={form.elevenlabs_api_key}
              onChange={v => set('elevenlabs_api_key', v)}
              placeholder="tu api key de elevenlabs..."
            />
          </Field>

          <Field
            label="ElevenLabs Voice ID"
            hint='Ejemplo: "pNInz6obpgDQGcFmaJgB" — lo copiás desde la web de ElevenLabs.'>
            <input
              value={form.elevenlabs_voice_id}
              onChange={e => set('elevenlabs_voice_id', e.target.value)}
              className="field-input"
              placeholder="pNInz6obpgDQGcFmaJgB"
            />
          </Field>
        </div>
      </Section>

      {/* API Keys IA */}
      <Section icon={Key} title="Claves de API — Inteligencia Artificial">
        <p className="text-xs text-jarvis-muted -mt-1">
          Las claves se guardan en tu <code className="bg-jarvis-surface px-1 rounded">.env</code> y toman efecto inmediatamente.
          Nunca salen de tu equipo.
        </p>
        <Field label="Groq API Key" hint="Usada para el Asistente IA (Chat). Gratis en console.groq.com.">
          <ApiKeyInput value={form.groq_api_key} onChange={v => set('groq_api_key', v)} />
        </Field>
        <Field label="Gemini API Key" hint="Alternativa a Groq. Gratis en aistudio.google.com.">
          <ApiKeyInput value={form.gemini_api_key} onChange={v => set('gemini_api_key', v)} />
        </Field>
      </Section>

      {/* Guardar */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#FF8C00] hover:bg-[#e07d00]
                     rounded-xl text-sm font-semibold text-white transition-colors
                     shadow-lg shadow-[#FF8C00]/20 disabled:opacity-50">
          <Save size={14} />
          {saveMutation.isPending ? 'Guardando…' : 'Guardar cambios'}
        </button>
        {savedOk && (
          <span className="text-sm text-teal-400 font-medium animate-pulse">
            ✓ Cambios guardados
          </span>
        )}
      </div>
    </div>
  )
}
