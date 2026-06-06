async function checkStatus() {
  try {
    const res  = await fetch("http://localhost:8000/api/browser/context")
    const data = await res.json()
    document.getElementById("dot").classList.add("active")
    document.getElementById("status").textContent = "Conectado a Jarvis"
    document.getElementById("url").textContent = data.url || "—"
  } catch {
    document.getElementById("status").textContent = "Jarvis no disponible"
  }
}

document.getElementById("btn").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (!tab?.id) return
  const response = await chrome.tabs.sendMessage(tab.id, { type: "GET_CONTEXT" })
  if (response) {
    await fetch("http://localhost:8000/api/browser/context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(response)
    })
    document.getElementById("status").textContent = "Contexto enviado ✓"
  }
})

checkStatus()