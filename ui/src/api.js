// ui/src/api.js
import axios from 'axios'

const BASE = 'http://localhost:8000/api'

const api = axios.create({ baseURL: BASE })

// ── Leads ──────────────────────────────────────────────
export const getLeads = (params) =>
  api.get('/leads', { params }).then(r => r.data)

export const getLead = (id) =>
  api.get(`/leads/${id}`).then(r => r.data)

export const getHotLeads = () =>
  api.get('/leads/hot').then(r => r.data)

export const getFollowups = () =>
  api.get('/leads/followups').then(r => r.data)

export const createLead = (data) =>
  api.post('/leads', data).then(r => r.data)

export const updateLead = (id, data) =>
  api.patch(`/leads/${id}`, data).then(r => r.data)

export const updateStatus = (id, status, notes = '') =>
  api.patch(`/leads/${id}/status`, { status, notes }).then(r => r.data)

export const deleteLead = (id) =>
  api.delete(`/leads/${id}`)

export const importLeadsCsv = (rows) =>
  api.post('/leads/import', { rows }).then(r => r.data)

export const exportLeadsCsv = (params = {}) => {
  const qs = new URLSearchParams()
  if (params.search) qs.set('search', params.search)
  if (params.status) qs.set('status', params.status)
  const a = document.createElement('a')
  a.href = `${BASE}/leads/export?${qs}`
  a.download = 'leads.csv'
  a.click()
}

// ── Stats ──────────────────────────────────────────────
export const getStats = () =>
  api.get('/stats').then(r => r.data)

// ── Eventos ────────────────────────────────────────────
export const getEvents = (leadId) =>
  api.get(`/leads/${leadId}/events`).then(r => r.data)

// ── Conversaciones ─────────────────────────────────────
export const getConversations = (leadId) =>
  api.get(`/leads/${leadId}/conversations`).then(r => r.data)

export const saveMessage = (leadId, data) =>
  api.post(`/leads/${leadId}/conversations`, data).then(r => r.data)

export const approveMessage = (convId) =>
  api.patch(`/conversations/${convId}/approve`).then(r => r.data)

// ── Prospección ────────────────────────────────────────
export const prospectLead = (leadId, productContext) =>
  api.post(`/leads/${leadId}/prospect`, {
    lead_id:         leadId,
    product_context: productContext,
  }).then(r => r.data)

// ── WhatsApp via Jarvis ────────────────────────────────
export const sendWhatsAppViaJarvis = (contact, message, leadId) =>
  api.post('/whatsapp/send', { contact, message, lead_id: leadId }).then(r => r.data)

export const getWaTask = (taskId) =>
  api.get(`/whatsapp/tasks/${taskId}`).then(r => r.data)

// Encola y espera el resultado real (polling hasta 90s)
// Resuelve con { success, error? } o rechaza con timeout
export const sendWhatsAppAndWait = async (contact, message, leadId, timeoutMs = 90000) => {
  const { id: taskId } = await sendWhatsAppViaJarvis(contact, message, leadId)
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 3000))
    const task = await getWaTask(taskId)
    if (task.status === 'done') return task.result  // { success, error? }
  }
  throw new Error('timeout')
}

// ── LeadFinder ─────────────────────────────────────────
export const startLeadFind = (categories, cities, maxPerCombination = 10, webTypes = null) =>
  api.post('/leads/find', { categories, cities, max_per_combination: maxPerCombination, web_types: webTypes }).then(r => r.data)

export const getLeadFindStatus = (jobId) =>
  api.get(`/leads/find/${jobId}`).then(r => r.data)

export const analyzeFinderLead = (lead) =>
  api.post('/leads/finder/analyze', lead).then(r => r.data)

// ── Chat IA ────────────────────────────────────────────
export const getChatSessions    = () => api.get('/chat/sessions').then(r => r.data)
export const createChatSession  = (title) => api.post('/chat/sessions', { title }).then(r => r.data)
export const deleteChatSession  = (id) => api.delete(`/chat/sessions/${id}`)
export const getChatMessages    = (id) => api.get(`/chat/sessions/${id}/messages`).then(r => r.data)

// Streaming — devuelve un fetch nativo (no axios) para leer el SSE
export const streamChatMessage = (sessionId, content) =>
  fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/messages`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ content }),
  })

// ── Calendario ─────────────────────────────────────────
export const getCalendarEvents  = (params) => api.get('/calendar/events', { params }).then(r => r.data)
export const createCalendarEvent= (data)  => api.post('/calendar/events', data).then(r => r.data)
export const updateCalendarEvent= (id, data) => api.patch(`/calendar/events/${id}`, data).then(r => r.data)
export const deleteCalendarEvent= (id)    => api.delete(`/calendar/events/${id}`)

// ── Ventas ─────────────────────────────────────────────
export const getSales    = (params)      => api.get('/sales', { params }).then(r => r.data)
export const createSale  = (data)        => api.post('/sales', data).then(r => r.data)
export const updateSale  = (id, data)    => api.patch(`/sales/${id}`, data).then(r => r.data)
export const deleteSale  = (id)          => api.delete(`/sales/${id}`)

// ── Post-its ───────────────────────────────────────────
export const getPostits    = ()           => api.get('/postits').then(r => r.data)
export const createPostit  = (data)       => api.post('/postits', data).then(r => r.data)
export const updatePostit  = (id, data)   => api.patch(`/postits/${id}`, data).then(r => r.data)
export const deletePostit  = (id)         => api.delete(`/postits/${id}`)

// ── Settings ───────────────────────────────────────────
export const getSettings    = () => api.get('/settings').then(r => r.data)
export const updateSettings = (data) => api.patch('/settings', data).then(r => r.data)

// ── Monitor WhatsApp ───────────────────────────────────
export const getMonitorStatus = () =>
  api.get('/monitor/status').then(r => r.data)

export const toggleMonitor = () =>
  api.post('/monitor/toggle').then(r => r.data)

// ── WebSocket ──────────────────────────────────────────
export function connectWS(onMessage) {
  const ws = new WebSocket('ws://localhost:8000/ws')
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)) }
    catch {}
  }
  ws.onclose = () => {
    // reconectar automáticamente después de 3 segundos
    setTimeout(() => connectWS(onMessage), 3000)
  }
  return ws
}