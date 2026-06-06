const API = "http://localhost:8000/api/browser"

const SERVICES = {
  whatsapp:  "web.whatsapp.com",
  messenger: "messenger.com",
  facebook:  "facebook.com",
}

function detectService(url) {
  if (!url) return null
  for (const [svc, pattern] of Object.entries(SERVICES)) {
    if (url.includes(pattern)) return svc
  }
  return null
}

// ── Reportar inventario de TODAS las pestañas ──────────────────────────────
async function reportTabs() {
  try {
    const tabs = await chrome.tabs.query({})
    const inventory = tabs
      .filter(t => t.url && !t.url.startsWith("chrome://") && !t.url.startsWith("edge://"))
      .map(t => ({
        id:       t.id,
        windowId: t.windowId,
        url:      t.url,
        title:    t.title,
        active:   t.active,
        service:  detectService(t.url),
      }))

    await fetch(`${API}/tabs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tabs: inventory })
    })
  } catch (_) {}
}

// ── Enviar resultado al backend ────────────────────────────────────────────
async function postResult(cmdId, result) {
  try {
    await fetch(`${API}/commands/${cmdId}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result)
    })
  } catch (_) {}
}

// ── Polling de comandos pendientes ─────────────────────────────────────────
async function pollCommands() {
  try {
    const res = await fetch(`${API}/commands/pending`)
    if (!res.ok) return
    const commands = await res.json()
    for (const cmd of commands) {
      executeCommand(cmd)
    }
  } catch (_) {}
}

async function executeCommand(cmd) {
  try {
    if (cmd.type === "focus_tab") {
      await chrome.tabs.update(cmd.tab_id, { active: true })
      if (cmd.window_id) await chrome.windows.update(cmd.window_id, { focused: true })
      await postResult(cmd.id, { success: true })

    } else if (cmd.type === "new_tab") {
      const tab = await chrome.tabs.create({ url: cmd.url, active: true })
      await postResult(cmd.id, { success: true, tab_id: tab.id, window_id: tab.windowId })

    } else if (cmd.type === "navigate_tab") {
      await chrome.tabs.update(cmd.tab_id, { url: cmd.url })
      await postResult(cmd.id, { success: true })

    } else if (cmd.type === "execute_in_tab") {
      // No esperamos la respuesta del content script aquí — el content script
      // reportará el resultado vía chrome.runtime.sendMessage → background → backend.
      // El service worker no necesita quedarse vivo esperando la ejecución larga.
      chrome.tabs.sendMessage(cmd.tab_id, {
        type:   "EXECUTE_ACTION",
        action: cmd.action,
        params: cmd.params || {},
        cmd_id: cmd.id,
      }, () => {
        if (chrome.runtime.lastError) {
          // Content script no disponible — reportar error inmediatamente
          postResult(cmd.id, { success: false, error: chrome.runtime.lastError.message })
        }
        // Si no hay error: content script recibió el mensaje y reportará el resultado
      })
      return  // No esperar — el content script maneja el resultado

    } else {
      await postResult(cmd.id, { success: false, error: `Tipo desconocido: ${cmd.type}` })
    }
  } catch (e) {
    await postResult(cmd.id, { success: false, error: e.message })
  }
}

// ── Resultado del content script → backend ─────────────────────────────────
// El content script envía COMMAND_RESULT cuando termina de ejecutar.
// Esto despierta el service worker si estaba suspendido (evento de runtime).
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "COMMAND_RESULT") {
    postResult(msg.cmd_id, msg.result)
    sendResponse({ ok: true })
  }
})

// ── Ciclos ──────────────────────────────────────────────────────────────────
setInterval(reportTabs,   3000)
setInterval(pollCommands, 1000)

chrome.tabs.onActivated.addListener(reportTabs)
chrome.tabs.onUpdated.addListener((_, info) => { if (info.status === "complete") reportTabs() })
chrome.tabs.onRemoved.addListener(reportTabs)

reportTabs()
