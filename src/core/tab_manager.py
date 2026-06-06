# src/core/tab_manager.py
import time
import uuid
import webbrowser
import requests
from src.core.logger import logger

_API = "http://localhost:8000/api/browser"

SERVICES = {
    "whatsapp":  "web.whatsapp.com",
    "messenger": "messenger.com",
    "facebook":  "facebook.com",
}

URLS = {
    "whatsapp":  "https://web.whatsapp.com",
    "messenger": "https://www.messenger.com/marketplace",
    "facebook":  "https://www.facebook.com/marketplace",
}


class TabManager:
    """
    Verifica → Recupera → Crea si falta → Ejecuta.
    Nunca asume que una pestaña sigue existiendo.
    """

    # ── Inventario ─────────────────────────────────────────────────────────

    def get_tabs(self) -> list[dict]:
        try:
            r = requests.get(f"{_API}/tabs", timeout=2)
            if r.ok:
                return r.json().get("tabs", [])
        except Exception:
            pass
        return []

    def find_tab(self, service: str) -> dict | None:
        pattern = SERVICES.get(service, service)
        for tab in self.get_tabs():
            if pattern in (tab.get("url") or ""):
                return tab
        return None

    def ensure_tab(self, service: str, timeout: int = 30) -> dict | None:
        """
        Encuentra la pestaña del servicio en el browser del usuario.
        Si no existe la abre con webbrowser y espera hasta `timeout` segundos.
        """
        tab = self.find_tab(service)
        if tab:
            self._focus(tab)
            return tab

        # El inventario puede estar desactualizado — reintentar hasta 3s antes de abrir nueva pestaña
        for _ in range(2):
            time.sleep(1.5)
            tab = self.find_tab(service)
            if tab:
                self._focus(tab)
                return tab

        # No está abierta — abrirla en el browser del usuario
        url = URLS.get(service, f"https://{SERVICES.get(service, service)}")
        logger.info(f"TabManager: abriendo {service} en browser del usuario → {url}")
        webbrowser.open_new_tab(url)

        # Esperar a que aparezca en el inventario
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            tab = self.find_tab(service)
            if tab:
                self._focus(tab)
                return tab

        logger.warning(f"TabManager: timeout ({timeout}s) esperando {service}")
        return None

    # ── Comandos al browser ─────────────────────────────────────────────────

    def _focus(self, tab: dict) -> bool:
        return self._send_command({
            "type":      "focus_tab",
            "tab_id":    tab["id"],
            "window_id": tab.get("windowId"),
        }, timeout=5) is not None

    def execute_in_tab(self, tab_id: int, action: str, params: dict,
                       timeout: int = 30) -> dict:
        result = self._send_command({
            "type":   "execute_in_tab",
            "tab_id": tab_id,
            "action": action,
            "params": params,
        }, timeout=timeout)
        return result or {"success": False, "error": "timeout o extensión no disponible"}

    def _send_command(self, cmd: dict, timeout: int = 10) -> dict | None:
        cmd_id = str(uuid.uuid4())
        cmd["id"] = cmd_id
        try:
            r = requests.post(f"{_API}/command", json=cmd, timeout=2)
            if not r.ok:
                return None
        except Exception as e:
            logger.warning(f"TabManager: no se pudo enviar comando: {e}")
            return None

        # Esperar resultado
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.5)
            try:
                r = requests.get(f"{_API}/commands/{cmd_id}/result", timeout=2)
                if r.ok:
                    data = r.json()
                    if data.get("status") == "done":
                        return data.get("result")
            except Exception:
                pass
        return None
