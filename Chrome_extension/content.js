// content.js — ejecuta acciones DOM en la pestaña del usuario

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// ── Dispatcher de acciones ─────────────────────────────────────────────────
async function executeAction(action, params) {
  switch (action) {
    case "whatsapp_send":
      return whatsappSend(params.contact, params.message)
    case "whatsapp_status":
      return whatsappStatus()
    case "messenger_read_chats":
      return messengerReadChats()
    case "get_context":
      return getContext()
    default:
      return { success: false, error: `Acción desconocida: ${action}` }
  }
}

// ── WhatsApp: enviar mensaje ───────────────────────────────────────────────
async function whatsappSend(contact, message) {
  try {
    // Esperar a que cargue la UI de WhatsApp
    await waitForElement('[data-testid="chat-list"]', 15000)

    // Abrir búsqueda
    const searchBtn = document.querySelector(
      '[data-testid="chat-list-search"], [aria-label*="Buscar"], [aria-label*="Search"]'
    )
    if (!searchBtn) return { success: false, error: "No se encontró el buscador de WhatsApp" }

    searchBtn.click()

    // Esperar a que aparezca el input de búsqueda (en vez de sleep fijo)
    const searchInput = await waitForElement(
      '[data-testid="search-input"], div[contenteditable="true"][data-tab="3"]',
      3000
    ).catch(() => null)
    if (!searchInput) return { success: false, error: "No se encontró el input de búsqueda" }

    searchInput.focus()
    document.execCommand("selectAll", false, null)
    document.execCommand("delete", false, null)
    document.execCommand("insertText", false, contact)

    // Esperar a que aparezca el primer resultado (en vez de sleep(1500) fijo)
    const firstResult = await waitForElement(
      '[data-testid="cell-frame-container"], [data-testid="list-item"]',
      5000
    ).catch(() => null)
    if (!firstResult) return { success: false, error: `Contacto no encontrado: ${contact}` }

    firstResult.click()

    // Esperar a que aparezca el campo de mensaje (en vez de sleep(600) fijo)
    const msgInput = await waitForElement(
      '[data-testid="conversation-compose-box-input"], div[contenteditable="true"][data-tab="10"]',
      5000
    ).catch(() => null)
    if (!msgInput) return { success: false, error: "No se encontró el campo de mensaje" }

    msgInput.focus()
    document.execCommand("insertText", false, message)
    await sleep(100)

    // Enviar con Enter
    msgInput.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true
    }))
    await sleep(200)

    return { success: true, contact, message }
  } catch (e) {
    return { success: false, error: e.message }
  }
}

// ── WhatsApp: verificar estado de carga ────────────────────────────────────
async function whatsappStatus() {
  const chatList = document.querySelector('[data-testid="chat-list"]')
  return {
    success: true,
    ready:   !!chatList,
    url:     window.location.href,
  }
}

// ── Messenger: leer chats del Marketplace ─────────────────────────────────
async function messengerReadChats() {
  try {
    await waitForElement('[aria-label*="Marketplace"], [role="grid"]', 10000)

    const chatItems = document.querySelectorAll(
      '[data-pagelet*="Marketplace"] [role="row"], ' +
      '[aria-label*="Chat en grupo:"], ' +
      'a[href*="/marketplace/"]'
    )

    if (!chatItems.length) {
      // Fallback: leer todo el texto visible de la zona de chats
      const sidebar = document.querySelector('[role="navigation"], [aria-label*="conversaciones"]')
      return {
        success: true,
        chats: [],
        visible_text: (sidebar || document.body).innerText.slice(0, 3000)
      }
    }

    const chats = Array.from(chatItems).slice(0, 30).map(el => ({
      text:   el.innerText?.replace(/\s+/g, " ").trim().slice(0, 200),
      unread: el.querySelector('[aria-label*="no leído"], [aria-label*="unread"]') !== null
    })).filter(c => c.text)

    return { success: true, chats }
  } catch (e) {
    return { success: false, error: e.message }
  }
}

// ── Contexto general ───────────────────────────────────────────────────────
function getContext() {
  return {
    success:      true,
    url:          window.location.href,
    title:        document.title,
    visible_text: document.body.innerText.replace(/\s+/g, " ").trim().slice(0, 3000),
  }
}

// ── Utilidades ─────────────────────────────────────────────────────────────
function waitForElement(selector, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const el = document.querySelector(selector)
    if (el) return resolve(el)

    const observer = new MutationObserver(() => {
      const found = document.querySelector(selector)
      if (found) {
        observer.disconnect()
        resolve(found)
      }
    })
    observer.observe(document.body, { childList: true, subtree: true })
    setTimeout(() => {
      observer.disconnect()
      reject(new Error(`Timeout esperando: ${selector}`))
    }, timeout)
  })
}

// ── Listener principal ─────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "EXECUTE_ACTION") {
    const cmdId = msg.cmd_id

    executeAction(msg.action, msg.params || {})
      .then(result => {
        sendResponse(result)
        // Reportar al background para que postee al backend.
        // Esto funciona aunque el service worker esté dormido — el mensaje lo despierta.
        if (cmdId) {
          chrome.runtime.sendMessage({ type: "COMMAND_RESULT", cmd_id: cmdId, result })
            .catch(() => {})
        }
      })
      .catch(e => {
        const result = { success: false, error: e.message }
        sendResponse(result)
        if (cmdId) {
          chrome.runtime.sendMessage({ type: "COMMAND_RESULT", cmd_id: cmdId, result })
            .catch(() => {})
        }
      })
    return true  // Mantener canal abierto para respuesta async
  }

  if (msg.type === "GET_CONTEXT") {
    sendResponse(getContext())
  }
})
