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

    def execute(self, action_type: str, params: dict) -> str:
        # Spotify no necesita navegador
        if action_type == "spotify":
            return self._handle_spotify(params)

        # Construir texto completo para detección
        all_text = f"{action_type} {json.dumps(params, ensure_ascii=False)}".lower()

        # ── Intercepción por plataforma ───────────────────────────────────
        platform = self._detect_platform(all_text)

        if platform == "whatsapp":
            contact = self._extract_contact(params)
            message = self._extract_message(params)
            if action_type == "whatsapp" or (contact and message):
                if not self._started:
                    self.start()
                if contact and message:
                    return self._handle_whatsapp({**params, "action": "send_message"})
                return self._handle_whatsapp({"action": "get_unread"})
            # Solo abrir URL → browser del usuario
            import webbrowser
            webbrowser.open_new_tab(PLATFORM_URLS["whatsapp"])
            logger.info("WhatsApp Web abierto en browser del usuario")
            return "WhatsApp Web abierto"

        if platform in ("messenger", "marketplace"):
            contact = self._extract_contact(params)
            message = self._extract_message(params)
            # Interacción real (enviar/leer) → Playwright
            if action_type == "messenger" or (contact and message):
                if not self._started:
                    self.start()
                if contact and message:
                    return self._handle_messenger({
                        **params,
                        "marketplace": True,
                        "action": "send_message"
                    })
                return self._handle_messenger({"action": "get_pending", "marketplace": True})
            # Solo abrir → browser del usuario, sin Playwright
            import webbrowser
            webbrowser.open_new_tab(PLATFORM_URLS["messenger"])
            logger.info("Messenger Marketplace abierto en browser del usuario")
            return "Messenger Marketplace abierto"

        if platform == "facebook":
            import webbrowser
            webbrowser.open_new_tab(PLATFORM_URLS["facebook"])
            logger.info("Facebook Marketplace abierto en browser del usuario")
            return "Facebook Marketplace abierto"

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

    def _handle_browser(self, params: dict) -> str:
        url      = params.get("url", "")
        platform = params.get("platform", "").lower()
        song     = params.get("song") or params.get("track") or params.get("cancion") or ""

        # Spotify
        if platform == "spotify" or (song and "spotify" in str(params).lower()):
            return self._handle_spotify(params)

        if not url:
            raise TaskExecutionError("abrir navegador", "Falta el parámetro 'url'")

        # Siempre abrir en el browser del usuario — sin Playwright
        import webbrowser
        webbrowser.open_new_tab(url)
        logger.info(f"URL abierta en browser del usuario: {url}")
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
        action = params.get("action", "send_message")

        if action == "open":
            import webbrowser
            webbrowser.open_new_tab(PLATFORM_URLS["whatsapp"])
            logger.info("WhatsApp Web abierto en browser del usuario")
            return "WhatsApp Web abierto"

        contact = self._extract_contact(params)
        message = self._extract_message(params)

        if action in ("send_message", ""):
            if not contact or not message:
                raise TaskExecutionError(
                    "enviar WhatsApp",
                    f"No encontré contacto o mensaje en: {params}"
                )
            # Navegar a WhatsApp en el browser de Playwright si no está ya ahí
            try:
                if "web.whatsapp.com" not in self.browser.page.url:
                    self.whatsapp.open()
            except Exception:
                self.whatsapp.open()
            self.whatsapp.send_message(contact, message)
            logger.info(f"WhatsApp: mensaje enviado a {contact}")
            return f"Mensaje enviado a {contact} por WhatsApp"

        elif action == "get_unread":
            chats = self.whatsapp.get_unread_chats()
            return f"{len(chats)} chats no leídos"

        raise TaskExecutionError("WhatsApp", f"Acción desconocida: {action}")

    def _handle_facebook(self, params: dict) -> str:
        import subprocess
        action = params.get("action", "open_marketplace")

        if action == "open_marketplace":
            # Abrir en nueva pestaña del Edge existente
            subprocess.Popen([
                "cmd", "/c", "start", "msedge",
                "--new-tab", "https://www.facebook.com/marketplace"
            ])
            logger.info("Facebook Marketplace abierto en nueva pestaña")
            return "Facebook Marketplace abierto"

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

        raise TaskExecutionError("Facebook", f"Acción desconocida: {action}")

    def _handle_messenger(self, params: dict) -> str:
        action  = params.get("action", "get_pending")

        # Solo abrir → browser del usuario, sin Playwright
        if action in ("open", "open_marketplace"):
            import webbrowser
            webbrowser.open_new_tab(PLATFORM_URLS["messenger"])
            logger.info("Messenger Marketplace abierto en browser del usuario")
            return "Messenger Marketplace abierto"

        contact = self._extract_contact(params)
        message = self._extract_message(params)

        # Para lectura/envío → Playwright
        ctx = self.browser._context
        current_url = ""
        try:
            current_url = self.browser._page.url
        except Exception:
            pass

        if "messenger.com/marketplace" not in current_url:
            # Buscar si ya existe una pestaña con Messenger
            messenger_page = None
            try:
                for p in ctx.pages:
                    if "messenger.com" in p.url:
                        messenger_page = p
                        break
            except Exception:
                pass

            if messenger_page:
                # Ya existe — traerla al frente y actualizar referencia
                messenger_page.bring_to_front()
                self.browser._page = messenger_page
                if "marketplace" not in messenger_page.url:
                    messenger_page.goto(
                        "https://www.messenger.com/marketplace",
                        wait_until="domcontentloaded"
                    )
            else:
                # No existe — abrir en nueva pestaña si ya hay otras abiertas
                try:
                    pages = ctx.pages
                    if len(pages) > 1 or (len(pages) == 1 and pages[0].url not in ("about:blank", "")):
                        new_page = ctx.new_page()
                        new_page.goto(
                            "https://www.messenger.com/marketplace",
                            wait_until="domcontentloaded",
                            timeout=30000
                        )
                        self.browser._page = new_page
                    else:
                        self.browser.navigate(
                            "https://www.messenger.com/marketplace",
                            wait_until="domcontentloaded"
                        )
                except Exception:
                    self.browser.navigate(
                        "https://www.messenger.com/marketplace",
                        wait_until="domcontentloaded"
                    )
            time.sleep(3)
            try:
                self.browser._page.wait_for_selector(
                    '[aria-label^="Chat en grupo:"]', timeout=15000
                )
            except Exception:
                pass

        if action in ("get_pending", "summarize", "get_conversations",
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

        # Plataformas — siempre abrir en browser del usuario
        import webbrowser
        if "whatsapp" in app_lower:
            webbrowser.open_new_tab(PLATFORM_URLS["whatsapp"])
            return "WhatsApp Web abierto"
        if "messenger" in app_lower or "marketplace" in app_lower:
            webbrowser.open_new_tab(PLATFORM_URLS["messenger"])
            return "Messenger Marketplace abierto"
        if "facebook" in app_lower or "face" in app_lower:
            webbrowser.open_new_tab(PLATFORM_URLS["facebook"])
            return "Facebook Marketplace abierto"
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
        mode = params.get("mode", "")

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