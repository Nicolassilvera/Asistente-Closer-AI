# src/core/task_executor.py
import json
import time
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError, TaskExecutionError
from src.modules.facebook import FacebookModule
from src.modules.whatsapp import WhatsAppModule
from src.modules.messenger import MessengerModule

# URLs fijas — sin interpretación del LLM
PLATFORM_URLS = {
    "whatsapp":    "https://web.whatsapp.com",
    "messenger":   "https://www.messenger.com/marketplace",
    "marketplace": "https://www.messenger.com/marketplace",
    "facebook":    "https://www.facebook.com/marketplace",
}

PLATFORM_KEYWORDS = {
    "whatsapp":  ["whatsapp", "wsp", "wasap", "wassap"],
    "messenger": ["messenger", "messen", "msn", "mensanger"],
    "facebook":  ["facebook", "face", "fb"],
}

MODO_FOCO_KEYWORDS = [
    "activar modo foco", "activar modo trabajo", "activar foco", "modo concentración",
    "empezar a trabajar", "iniciar trabajo", "activar trabajo",
    "modo ventas", "entorno de trabajo", "Modo ventas"
]

class TaskExecutor:
    def __init__(self):
        self.browser      = BrowserEngine()
        self.facebook     = None
        self.whatsapp     = None
        self.messenger    = None
        self.executor_gpt = None
        self._started     = False

    def start(self):
        if not self._started:
            from src.core.gpt_engine import GPTEngine
            self.browser      = BrowserEngine()
            self.browser.start(headless=False)
            self.facebook     = FacebookModule(self.browser)
            self.whatsapp     = WhatsAppModule(self.browser)
            self.messenger    = MessengerModule(self.browser)
            self.executor_gpt = GPTEngine()
            self._started     = True
            logger.info("TaskExecutor iniciado.")

    def _detect_platform(self, text: str) -> str | None:
        text_lower = str(text).lower()
        for platform, keywords in PLATFORM_KEYWORDS.items():
            if any(k in text_lower for k in keywords):
                return platform
        return None

    def _is_modo_foco(self, text: str) -> bool:
        text_lower = str(text).lower()
        return any(k in text_lower for k in MODO_FOCO_KEYWORDS)

    def execute(self, action_type: str, params: dict) -> str:
        # Spotify no necesita navegador
        if action_type == "spotify":
            return self._handle_spotify(params)

        # Construir texto completo para detección
        all_text = f"{action_type} {json.dumps(params, ensure_ascii=False)}".lower()

        # ── Modo Foco — intercepción ANTES de todo ────────────────────────
        if self._is_modo_foco(all_text):
            if not self._started:
                self.start()
            return self._handle_modo_foco()

        # ── Intercepción por plataforma ───────────────────────────────────
        platform = self._detect_platform(all_text)

        if platform == "whatsapp":
            if not self._started:
                self.start()
            contact = self._extract_contact(params)
            message = self._extract_message(params)
            if contact and message:
                return self._handle_whatsapp({**params, "action": "send_message"})
            return self._handle_whatsapp({"action": "open"})

        if platform in ("messenger", "marketplace"):
            if not self._started:
                self.start()
            contact = self._extract_contact(params)
            message = self._extract_message(params)
            if contact and message:
                return self._handle_messenger({
                    **params,
                    "marketplace": True,
                    "action": "send_message"
                })
            return self._handle_messenger({"action": "get_pending", "marketplace": True})

        if platform == "facebook":
            if not self._started:
                self.start()
            return self._handle_facebook({"action": "open_marketplace"})

        # ── Resto normal ──────────────────────────────────────────────────
        if not self._started:
            self.start()

        logger.info(f"Ejecutando tarea: {action_type} | {params}")

        handlers = {
            "browser":   self._handle_browser,
            "whatsapp":  self._handle_whatsapp,
            "facebook":  self._handle_facebook,
            "messenger": self._handle_messenger,
            "app":       self._handle_app,
            "system":    self._handle_system,
        }

        handler = handlers.get(action_type)
        if not handler:
            raise TaskExecutionError(action_type, f"Tipo desconocido: {action_type}")

        try:
            return handler(params)
        except BrowserError as e:
            raise TaskExecutionError(e.task_desc, e.reason)

    # ── Handlers ──────────────────────────────────────────────────────────

    def _handle_modo_foco(self) -> str:
        console = Console()
        from rich.console import Console
        console.print("[yellow]Activando Modo Trabajo...[/yellow]")
        resultados = []
        urls = [
            ("WhatsApp",  "https://web.whatsapp.com"),

            ("Messenger", "https://www.messenger.com/marketplace"),
            ("Facebook",  "https://www.facebook.com/marketplace"),
        ]
        for i, (nombre, url) in enumerate(urls):
            try:

                if i == 0:
                    # Primera URL — navegar en la pestaña actual
                    self.browser._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                else:
                    # Pestañas siguientes — Ctrl+T para abrir nueva pestaña
                    self.browser._page.keyboard.press("Control+t")
                    time.sleep(0.8)
                    # Obtener la nueva pestaña activa
                    pages = self.browser._context.pages
                    new_page = pages[-1]
                    # Actualizar la página activa
                    self.browser._page = new_page
                    new_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(1.5)
                resultados.append(f"{nombre} ✓")

                logger.info(f"Modo Trabajo: {nombre} abierto")
            except Exception as e:
                resultados.append(f"{nombre} ✗")

                logger.warning(f"Modo Trabajo: {nombre} falló: {e}")

        resumen = "Modo Trabajo activado: " + " | ".join(resultados)
        console.print(f"[green]{resumen}[/green]")
        return resumen

    def _handle_browser(self, params: dict) -> str:
        url      = params.get("url", "")
        platform = params.get("platform", "").lower()
        song     = params.get("song") or params.get("track") or params.get("cancion") or ""

        # Spotify
        if platform == "spotify" or (song and "spotify" in str(params).lower()):
            return self._handle_spotify(params)

        # WhatsApp — siempre módulo web
        if "whatsapp" in url.lower() or "whatsapp" in platform:
            return self._handle_whatsapp({"action": "open"})

        # Messenger — siempre marketplace
        if "messenger" in url.lower() or "messenger" in platform:
            return self._handle_messenger({"action": "get_pending", "marketplace": True})

        # Facebook — marketplace
        if "facebook" in url.lower() and "marketplace" not in url.lower():
            return self._handle_facebook({"action": "open_marketplace"})

        if not url:
            raise TaskExecutionError("abrir navegador", "Falta el parámetro 'url'")

        self.browser.navigate(url)
        return f"Página abierta: {url}"

    def _handle_spotify(self, params: dict) -> str:
        import subprocess
        import urllib.parse
        import pyautogui

        song   = params.get("song") or params.get("track") or params.get("cancion") or ""
        artist = params.get("artist") or params.get("artista") or ""
        query  = params.get("query") or params.get("playlist") or ""

        if song and artist:
            search = f"{song} {artist}"
        elif song:
            search = song
        elif query:
            search = query
        else:
            search = "música"

        encoded     = urllib.parse.quote(search)
        spotify_uri = f"spotify:search:{encoded}"

        try:
            subprocess.Popen(["cmd", "/c", "start", "", spotify_uri])
            logger.info(f"Spotify: buscando '{search}'")
            time.sleep(4)

            try:
                import pygetwindow as gw
                windows = [w for w in gw.getAllWindows()
                           if "spotify" in w.title.lower() and w.width > 100]
                if windows:
                    windows[0].activate()
                    time.sleep(1)
            except Exception:
                screen_w, screen_h = pyautogui.size()
                pyautogui.click(screen_w // 2, screen_h // 2)
                time.sleep(0.3)

            pyautogui.press("enter")
            time.sleep(0.5)
            logger.info("Spotify: reproducción iniciada")
            return f"Reproduciendo '{search}' en Spotify"

        except Exception as e:
            logger.error(f"Spotify error: {e}")
            raise TaskExecutionError("abrir Spotify", str(e))

    def _handle_whatsapp(self, params: dict) -> str:
        action  = params.get("action", "send_message")
        contact = self._extract_contact(params)
        message = self._extract_message(params)

        current_url = ""
        try:
            current_url = self.browser.page.url
        except Exception:
            pass

        if "web.whatsapp.com" not in current_url:
            self.whatsapp.open()

        if action == "open":
            return "WhatsApp Web abierto"

        elif action in ("send_message", ""):
            if not contact or not message:
                raise TaskExecutionError(
                    "enviar WhatsApp",
                    f"No encontré contacto o mensaje en: {params}"
                )
            self.whatsapp.send_message(contact, message)
            return f"Mensaje enviado a {contact}"

        elif action == "get_unread":
            chats = self.whatsapp.get_unread_chats()
            return f"{len(chats)} chats no leídos"

        raise TaskExecutionError("WhatsApp", f"Acción desconocida: {action}")

    def _handle_facebook(self, params: dict) -> str:
        action = params.get("action", "open_marketplace")

        if action == "open_marketplace":
            self.facebook.open_marketplace()
            return "Marketplace abierto"
        elif action == "open_inbox":
            self.facebook.open_inbox()
            return "Inbox abierto"
        elif action == "get_messages":
            msgs = self.facebook.get_unread_messages()
            return f"{len(msgs)} mensajes no leídos"
        elif action == "send_message":
            url = params.get("conversation_url", "")
            msg = params.get("message", "")
            if not url or not msg:
                raise TaskExecutionError("enviar mensaje FB", "Faltan url o message")
            self.facebook.send_message(url, msg)
            return "Mensaje enviado"
        elif action == "search":
            query   = params.get("query", "")
            results = self.facebook.search_marketplace(query)
            return f"{len(results)} resultados"

        raise TaskExecutionError("Facebook", f"Acción desconocida: {action}")

    def _handle_messenger(self, params: dict) -> str:
        action  = params.get("action", "get_pending")
        contact = self._extract_contact(params)
        message = self._extract_message(params)

        # SIEMPRE Marketplace — URL hardcodeada
        current_url = ""
        try:
            current_url = self.browser.page.url
        except Exception:
            pass

        if "messenger.com/marketplace" not in current_url:
            self.browser.navigate(
                "https://www.messenger.com/marketplace",
                wait_until="domcontentloaded"
            )
            time.sleep(3)
            try:
                self.browser.page.wait_for_selector(
                    '[aria-label^="Chat en grupo:"]',
                    timeout=15000
                )
            except Exception:
                pass

        if action in ("open", "open_marketplace"):
            return "Messenger Marketplace abierto"

        elif action in ("get_pending", "summarize", "get_conversations",
                        "get_chats", "get_messages"):
            summary = self.messenger.summarize_marketplace(self.executor_gpt)
            from rich.console import Console
            Console().print(f"\n[yellow]Jarvis:[/yellow] {summary}\n")
            return summary

        elif action in ("send_message", "send_marketplace_message"):
            if not contact or not message:
                summary = self.messenger.summarize_marketplace(self.executor_gpt)
                from rich.console import Console
                Console().print(f"\n[yellow]Jarvis:[/yellow] {summary}\n")
                return summary
            self.messenger.send_marketplace_message(contact, message)
            return f"Mensaje enviado a {contact} en Marketplace"

        # Default → resumir
        summary = self.messenger.summarize_marketplace(self.executor_gpt)
        from rich.console import Console
        Console().print(f"\n[yellow]Jarvis:[/yellow] {summary}\n")
        return summary

    def _handle_app(self, params: dict) -> str:
        import subprocess

        app = (
            params.get("app") or
            params.get("app_name") or
            params.get("application") or
            params.get("nombre") or
            ""
        )

        if not app:
            raise TaskExecutionError("abrir app", "Falta el parámetro 'app'")

        app_lower = app.lower()

        # Modo foco
        if self._is_modo_foco(app_lower):
            return self._handle_modo_foco()

        # Plataformas
        if "whatsapp" in app_lower:
            return self._handle_whatsapp({"action": "open"})
        if "messenger" in app_lower or "marketplace" in app_lower:
            return self._handle_messenger({"action": "get_pending", "marketplace": True})
        if "facebook" in app_lower or "face" in app_lower:
            return self._handle_facebook({"action": "open_marketplace"})
        if "spotify" in app_lower:
            return self._handle_spotify({"query": "música"})

        apps_map = {
            "notepad":  "notepad.exe",
            "explorer": "explorer.exe",
            "chrome":   "chrome.exe",
            "excel":    "excel.exe",
            "word":     "winword.exe",
            "edge":     "msedge.exe",
        }
        executable = apps_map.get(app_lower, app)
        try:
            subprocess.Popen(executable)
            return f"Aplicación abierta: {app}"
        except FileNotFoundError:
            raise TaskExecutionError(f"abrir {app}", "Aplicación no encontrada")

    def _handle_system(self, params: dict) -> str:
        action  = params.get("action", "")
        message = (
            params.get("message") or
            params.get("output") or
            params.get("text") or
            ""
        )

        # Verificar modo foco en el action
        all_text = f"{action} {message}".lower()
        if self._is_modo_foco(all_text):
            return self._handle_modo_foco()

        if message:
            from rich.console import Console
            Console().print(f"\n[yellow]Jarvis:[/yellow] {message}\n")
            return f"Mensaje mostrado: {message}"

        if action == "screenshot":
            path = self.browser.screenshot("screenshot_jarvis.png")
            return f"Screenshot guardado en {path}"

        if action == "notify":
            msg = params.get("message", "")
            from rich.console import Console
            Console().print(f"\n[yellow]Jarvis:[/yellow] {msg}\n")
            return f"Notificación: {msg}"

        logger.debug(f"System handler: params recibidos: {params}")
        return "OK"

    # ── Extractores ───────────────────────────────────────────────────────

    def _extract_contact(self, params: dict) -> str:
        for key in [
            "contact", "phone_number", "contact_name",
            "name", "number", "recipient", "to",
            "contacto", "nombre", "destinatario", "para"
        ]:
            if params.get(key):
                return params[key]

        skip = {
            "message", "text", "body", "content", "msg", "action",
            "url", "mensaje", "texto", "contenido", "asunto",
            "platform", "plataforma", "marketplace"
        }
        for key, val in params.items():
            if key not in skip and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def _extract_message(self, params: dict) -> str:
        for key in ["message", "text", "body", "content", "msg",
                    "mensaje", "texto", "contenido", "cuerpo"]:
            if params.get(key):
                return params[key]
        return ""

    def close(self):
        if self._started:
            self.browser.close()
            self._started = False