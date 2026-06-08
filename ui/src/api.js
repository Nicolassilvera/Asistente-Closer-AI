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

// ── LeadFinder ─────────────────────────────────────────
export const startLeadFind = (categories, cities, maxPerCombination = 10) =>
  api.post('/leads/find', { categories, cities, max_per_combination: maxPerCombination }).then(r => r.data)

export const getLeadFindStatus = (jobId) =>
  api.get(`/leads/find/${jobId}`).then(r => r.data)

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