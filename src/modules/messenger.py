# src/modules/messenger.py
import time
import random
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

MESSENGER_URL = "https://www.messenger.com"
MARKETPLACE_URL = "https://www.messenger.com/marketplace"

# Límites para comportamiento humano natural
MAX_MESSAGES_PER_SESSION = 30
MIN_DELAY_BETWEEN_ACTIONS = 1.5
MAX_DELAY_BETWEEN_ACTIONS = 3.5

class MessengerModule:
    """
    Módulo de asistencia para Messenger.
    
    Filosofía: el humano siempre supervisa y aprueba.
    Jarvis lee, resume y redacta — el usuario decide si envía.
    """

    def __init__(self, browser: BrowserEngine):
        self.browser          = browser
        self._messages_sent   = 0
        self._session_started = False

    def open(self) -> bool:
        """Abre Messenger. Si ya está logueado, carga directo."""
        try:
            logger.info("Abriendo Messenger...")
            self.browser.navigate(MESSENGER_URL, wait_until="domcontentloaded")
            self._human_delay()

            # Verificar login
            if self._needs_login():
                from rich.console import Console
                Console().print(
                    "\n[yellow]⚠ Messenger pide login.[/yellow]\n"
                    "[dim]Logueate manualmente y presioná Enter.[/dim]\n"
                )
                input()

            # Esperar que cargue la interfaz
            ok = self.browser.wait_for_human(
                selector='[aria-label="Buscar en Messenger"]',
                timeout_minutes=1,
                message="Cargando Messenger..."
            )

            if not ok:
                raise BrowserError("abrir Messenger", "No cargó a tiempo")

            self._session_started = True
            logger.info("Messenger listo.")
            return True

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("abrir Messenger", str(e))

    def get_pending_chats(self, limit: int = 10) -> list[dict]:
        """
        Lee los chats visibles en el panel izquierdo.
        Devuelve lista con nombre, preview y si tiene mensajes sin leer.
        """
        try:
            self._human_delay()
            page  = self.browser.page
            chats = []

            # Contenedores de conversaciones
            items = page.query_selector_all('[role="row"], [role="listitem"]')

            for item in items[:limit]:
                try:
                    # Nombre del contacto
                    name_el = item.query_selector(
                        'span[dir="auto"], [data-testid="thread-list-item-title"]'
                    )
                    # Preview del último mensaje
                    preview_el = item.query_selector(
                        'span[data-testid="thread-list-item-preview"],'
                        '[aria-label*="mensaje"]'
                    )
                    # Indicador de no leído
                    unread_el = item.query_selector(
                        '[data-testid="unread-count"], '
                        'span[data-visualcompletion="ignore"]'
                    )

                    name = name_el.inner_text().strip() if name_el else ""
                    if not name or len(name) < 2:
                        continue

                    chats.append({
                        "name":    name,
                        "preview": preview_el.inner_text().strip() if preview_el else "",
                        "unread":  unread_el is not None,
                        "element": item  # guardamos referencia para click
                    })
                except Exception:
                    continue

            logger.info(f"Messenger: {len(chats)} chats detectados")
            return chats

        except Exception as e:
            raise BrowserError("leer chats de Messenger", str(e))

    def open_chat(self, contact_name: str) -> bool:
        """
        Busca y abre un chat por nombre de contacto.
        """
        try:
            logger.info(f"Abriendo chat con {contact_name}...")

            # Usar el buscador
            search = '[aria-label="Buscar en Messenger"]'
            self.browser.wait_for(search, timeout=10000)
            self.browser.click(search)
            self._human_delay(0.5, 1.0)

            # Limpiar y escribir
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            self._human_delay(0.3, 0.6)
            self.browser.type_text(search, contact_name, delay=80)
            self._human_delay(1.5, 2.5)

            # Click en primer resultado
            result = self.browser.page.query_selector(
                '[role="option"], [role="listitem"] [role="link"]'
            )
            if result:
                result.click()
                self._human_delay()
                logger.info(f"Chat con {contact_name} abierto.")
                return True

            raise BrowserError(f"abrir chat con {contact_name}", "Contacto no encontrado")

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"buscar {contact_name} en Messenger", str(e))

    def read_conversation(self, max_messages: int = 10) -> list[dict]:
        """
        Lee los mensajes del chat actualmente abierto.
        Devuelve lista de {sender, text, time}.
        """
        try:
            self._human_delay()
            page     = self.browser.page
            messages = []

            # Mensajes del chat
            msg_elements = page.query_selector_all(
                '[role="row"] [dir="auto"], '
                '[data-testid*="message"] span[dir="auto"]'
            )

            for el in msg_elements[-max_messages:]:
                try:
                    text = el.inner_text().strip()
                    if not text or len(text) < 1:
                        continue

                    # Detectar si es mensaje propio o recibido
                    parent = el.evaluate_handle(
                        "el => el.closest('[class*=\"outgoing\"], [class*=\"incoming\"]')"
                    )
                    is_mine = False
                    try:
                        cls = parent.get_property("className").json_value()
                        is_mine = "outgoing" in cls.lower()
                    except Exception:
                        pass

                    messages.append({
                        "sender": "yo" if is_mine else "contacto",
                        "text":   text
                    })
                except Exception:
                    continue

            logger.info(f"Leídos {len(messages)} mensajes")
            return messages

        except Exception as e:
            raise BrowserError("leer conversación de Messenger", str(e))

    def write_message(self, message: str) -> bool:
        """
        Escribe un mensaje en el chat activo SIN enviarlo.
        El usuario debe aprobar antes de llamar a send_message().
        """
        try:
            logger.info("Escribiendo mensaje (sin enviar)...")

            # Selector del campo de texto — cambia según el chat abierto
            msg_box = '[role="textbox"]'
            self.browser.wait_for(msg_box, timeout=10000)
            self.browser.click(msg_box)
            self._human_delay(0.5, 1.0)

            # Escribir con velocidad humana
            self.browser.page.type(msg_box, message, delay=random.randint(60, 120))
            logger.info("Mensaje escrito. Esperando aprobación del usuario.")
            return True

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("escribir mensaje en Messenger", str(e))

    def send_current_message(self) -> bool:
        """
        Envía el mensaje que ya está escrito en el campo de texto.
        Solo llamar después de write_message() y aprobación humana.
        """
        if self._messages_sent >= MAX_MESSAGES_PER_SESSION:
            raise BrowserError(
                "enviar mensaje",
                f"Límite de {MAX_MESSAGES_PER_SESSION} mensajes por sesión alcanzado"
            )

        try:
            self._human_delay(0.8, 1.5)
            self.browser.page.keyboard.press("Enter")
            self._messages_sent += 1
            logger.info(f"Mensaje enviado ({self._messages_sent}/{MAX_MESSAGES_PER_SESSION})")
            self._human_delay()
            return True

        except Exception as e:
            raise BrowserError("enviar mensaje en Messenger", str(e))

    def send_message(self, contact_name: str, message: str) -> bool:
        """
        Flujo completo: busca contacto → escribe → espera aprobación → envía.
        """
        from rich.console import Console
        from rich.prompt import Confirm
        console = Console()

        # 1. Abrir chat
        self.open_chat(contact_name)
        self._human_delay()

        # 2. Leer contexto reciente
        try:
            recent = self.read_conversation(max_messages=5)
            if recent:
                console.print(f"\n[dim]Últimos mensajes con {contact_name}:[/dim]")
                for msg in recent[-3:]:
                    prefix = "[cyan]Vos:[/cyan]" if msg["sender"] == "yo" else f"[yellow]{contact_name}:[/yellow]"
                    console.print(f"  {prefix} {msg['text']}")
                console.print()
        except Exception:
            pass

        # 3. Escribir sin enviar
        self.write_message(message)

        # 4. Mostrar el mensaje y pedir confirmación — SUPERVISIÓN HUMANA
        console.print(f"\n[yellow]Jarvis redactó:[/yellow] {message}")
        console.print(f"[dim]Para: {contact_name} — vía Messenger[/dim]\n")

        try:
            confirmed = Confirm.ask("¿Enviamos este mensaje?")
        except KeyboardInterrupt:
            # Limpiar el campo de texto
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            console.print("[dim]Mensaje cancelado.[/dim]")
            return False

        if not confirmed:
            # Limpiar el campo
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            console.print("[dim]Mensaje descartado.[/dim]")
            return False

        # 5. Enviar con aprobación
        self.send_current_message()
        console.print(f"[green]✓ Mensaje enviado a {contact_name}.[/green]")
        return True

    #-->

    def summarize_pending(self, gpt_engine=None) -> str:
        """Lee y resume los chats pendientes de Messenger."""
        try:
            self._human_delay(2, 3)
            page  = self.browser.page
            chats = []
    
            # Selectores para chats normales de Messenger
            selectors = [
                '[role="row"] a[href^="/t/"]',
                '[role="listitem"] a[href^="/t/"]',
                'a[href^="/t/"]',
            ]
    
            items = []
            for sel in selectors:
                try:
                    found = page.query_selector_all(sel)
                    if found:
                        items = found
                        break
                except Exception:
                    continue
                
            for item in items[:15]:
                try:
                    label = item.get_attribute("aria-label") or ""
                    href  = item.get_attribute("href") or ""
                    if not label or not href:
                        continue
                    chats.append({
                        "name":    label.strip(),
                        "href":    href,
                        "unread":  False
                    })
                except Exception:
                    continue
                
            if not chats:
                return "No encontré chats en Messenger. Puede que la página no haya cargado."
    
            if gpt_engine:
                context = "\n".join([f"- {c['name']}" for c in chats[:10]])
                return gpt_engine.ask(
                    f"Resumí estos chats de Messenger de forma concisa para leerlos en voz alta:\n{context}",
                    context="Sos Jarvis, asistente comercial. Sé muy breve."
                )
    
            lines = [f"Tenés {len(chats)} conversaciones en Messenger:"]
            for c in chats[:8]:
                lines.append(f"  • {c['name']}")
            return "\n".join(lines)
    
        except Exception as e:
            raise BrowserError("leer chats de Messenger", str(e))
    
    #-->

    def _human_delay(self, min_s: float = None, max_s: float = None):
        """Pausa aleatoria para simular comportamiento humano."""
        min_s = min_s or MIN_DELAY_BETWEEN_ACTIONS
        max_s = max_s or MAX_DELAY_BETWEEN_ACTIONS
        time.sleep(random.uniform(min_s, max_s))

    def _needs_login(self) -> bool:
        try:
            url = self.browser.page.url
            return "login" in url or "checkpoint" in url
        except Exception:
            return False
        
# ---> Marketplace y otras funciones pueden implementarse aquí siguiendo la misma filosofía de supervisión humana.

    def open_marketplace(self) -> bool:
        """Abre la sección de Marketplace dentro de Messenger."""
        try:
            logger.info("Abriendo Marketplace de Messenger...")
            self.browser.navigate(MARKETPLACE_URL, wait_until="domcontentloaded")
            self._human_delay(2, 3)

            ok = self.browser.wait_for_human(
                selector='[aria-label="Marketplace · 3 no leídas"], [href="/marketplace/"]',
                timeout_minutes=1,
                message="Cargando Marketplace..."
            )
            logger.info("Marketplace listo.")
            return True
        except Exception as e:
            raise BrowserError("abrir Marketplace Messenger", str(e))

    def get_marketplace_chats(self, only_unread: bool = False) -> list[dict]:
        """
        Lee todos los chats de Marketplace.
        Devuelve lista con nombre, producto, url e indicador de no leído.
        """
        try:
            # Asegurar que estamos en Marketplace
            if "marketplace" not in self.browser.page.url:
                self.open_marketplace()

            self._human_delay(1, 2)
            page  = self.browser.page
            chats = []

            # Selector exacto detectado
            items = page.query_selector_all('[aria-label^="Chat en grupo:"][role="link"]')

            for item in items:
                try:
                    label = item.get_attribute("aria-label") or ""
                    href  = item.get_attribute("href") or ""

                    # Parsear "Chat en grupo: NOMBRE · PRODUCTO"
                    # Formato: "Chat en grupo: Francisco · Balanza Industrial..."
                    clean = label.replace("Chat en grupo: ", "").strip()

                    if " · " in clean:
                        parts   = clean.split(" · ", 1)
                        name    = parts[0].strip()
                        product = parts[1].strip()
                    else:
                        name    = clean
                        product = ""

                    if not name:
                        continue

                    chats.append({
                        "name":    name,
                        "product": product,
                        "url":     f"https://www.messenger.com{href}",
                        "href":    href,
                    })
                except Exception:
                    continue

            # Detectar cuántos no leídos hay
            try:
                marketplace_link = page.query_selector('[href="/marketplace/"]')
                if marketplace_link:
                    label_text = marketplace_link.get_attribute("aria-label") or ""
                    # "Marketplace · 3 no leídas"
                    if "no leída" in label_text:
                        import re
                        nums = re.findall(r'\d+', label_text)
                        unread_count = int(nums[0]) if nums else 0
                        # Marcar los primeros N como no leídos
                        for i in range(min(unread_count, len(chats))):
                            chats[i]["unread"] = True
            except Exception:
                pass

            logger.info(f"Marketplace: {len(chats)} chats encontrados")
            return chats

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("leer chats de Marketplace", str(e))

    def open_marketplace_chat(self, name: str = "", url: str = "") -> dict:
        """
        Abre un chat de Marketplace por nombre o URL directa.
        Devuelve info del chat abierto.
        """
        try:
            # Si tenemos URL directa, navegamos directo
            if url:
                logger.info(f"Abriendo chat Marketplace por URL: {url}")
                self.browser.navigate(url, wait_until="domcontentloaded")
                self._human_delay(2, 3)
                return {"opened": True, "url": url}

            # Si tenemos nombre, buscar en la lista
            if name:
                chats = self.get_marketplace_chats()

                # Buscar coincidencia por nombre (parcial, case insensitive)
                match = None
                for chat in chats:
                    if name.lower() in chat["name"].lower():
                        match = chat
                        break

                if not match:
                    raise BrowserError(
                        f"abrir chat con {name}",
                        f"No encontré a '{name}' en Marketplace. "
                        f"Contactos disponibles: {[c['name'] for c in chats[:5]]}"
                    )

                logger.info(f"Abriendo chat con {match['name']} — {match['product']}")
                self.browser.navigate(match["url"], wait_until="domcontentloaded")
                self._human_delay(2, 3)
                return match

            raise BrowserError("abrir chat Marketplace", "Necesito nombre o URL del chat")

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("abrir chat Marketplace", str(e))

    def send_marketplace_message(self, name: str, message: str) -> bool:
        """
        Flujo completo para Marketplace:
        busca el chat → muestra contexto → escribe → pide confirmación → envía.
        """
        from rich.console import Console
        from rich.prompt import Confirm
        console = Console()

        # 1. Ir a Marketplace si no estamos
        if "marketplace" not in self.browser.page.url:
            self.open_marketplace()

        # 2. Buscar y abrir el chat
        chat_info = self.open_marketplace_chat(name=name)
        self._human_delay()

        # 3. Mostrar contexto del producto
        if chat_info.get("product"):
            console.print(
                f"\n[dim]Chat de Marketplace:[/dim] "
                f"[bold]{chat_info['name']}[/bold] "
                f"[dim]— {chat_info['product']}[/dim]\n"
            )

        # 4. Leer mensajes recientes
        try:
            recent = self.read_conversation(max_messages=5)
            if recent:
                console.print("[dim]Últimos mensajes:[/dim]")
                for msg in recent[-3:]:
                    prefix = "[cyan]Vos:[/cyan]" if msg["sender"] == "yo" else f"[yellow]{chat_info['name']}:[/yellow]"
                    console.print(f"  {prefix} {msg['text']}")
                console.print()
        except Exception:
            pass

        # 5. Escribir sin enviar
        msg_box = '[role="textbox"]'
        try:
            self.browser.wait_for(msg_box, timeout=10000)
            self.browser.click(msg_box)
            self._human_delay(0.5, 1.0)
            self.browser.page.type(msg_box, message, delay=random.randint(60, 120))
        except Exception as e:
            raise BrowserError("escribir en chat Marketplace", str(e))

        # 6. Confirmación humana — SIEMPRE
        console.print(f"\n[yellow]Jarvis redactó:[/yellow] {message}")
        console.print(f"[dim]Para: {chat_info['name']} — Marketplace[/dim]\n")

        try:
            confirmed = Confirm.ask("¿Enviamos este mensaje?")
        except KeyboardInterrupt:
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            console.print("[dim]Cancelado.[/dim]")
            return False

        if not confirmed:
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            console.print("[dim]Mensaje descartado.[/dim]")
            return False

        # 7. Enviar
        self._human_delay(0.8, 1.5)
        self.browser.page.keyboard.press("Enter")
        self._messages_sent += 1
        console.print(f"[green]✓ Mensaje enviado a {chat_info['name']} en Marketplace.[/green]")
        logger.info(f"Mensaje Marketplace enviado a {chat_info['name']}")
        return True

    def summarize_marketplace(self, gpt_engine=None) -> str:
        """Resume los chats pendientes de Marketplace con IA."""
        chats = self.get_marketplace_chats()

        if not chats:
            return "No hay chats en Marketplace."

        unread = [c for c in chats if c.get("unread")]
        pending = unread if unread else chats[:5]

        if gpt_engine:
            context = "\n".join([
                f"- {c['name']} pregunta por: {c['product']}"
                for c in pending
            ])
            return gpt_engine.ask(
                f"Resumí estos chats de Marketplace de forma comercial y concisa:\n{context}",
                context="Sos Jarvis, asistente comercial de ventas."
            )

        lines = [f"Tenés {len(chats)} chats en Marketplace:"]
        if unread:
            lines.append(f"  {len(unread)} sin leer:")
        for c in pending[:5]:
            lines.append(f"  • {c['name']} — {c['product'][:50]}")
        return "\n".join(lines)
    
    # Lectura de Chats Marketplace

    def get_marketplace_chats(self, only_unread: bool = False) -> list[dict]:
        try:
            # Asegurar navegador abierto
            self.browser.ensure_open()

            # Asegurar que estamos en Marketplace
            current_url = self.browser.page.url
            if "messenger.com/marketplace" not in current_url:
                self.open_marketplace()

            # Esperar que cargue el panel de chats — tiempo generoso
            self._human_delay(3, 4)

            page  = self.browser.page
            chats = []

            # Múltiples selectores — probar en orden hasta encontrar chats
            selectors_to_try = [
                '[aria-label^="Chat en grupo:"][role="link"]',
                '[href^="/marketplace/t/"]',
                'a[href*="/marketplace/t/"]',
            ]

            items = []
            for selector in selectors_to_try:
                try:
                    found = page.query_selector_all(selector)
                    if found:
                        items = found
                        logger.debug(f"Selector funcionó: {selector} — {len(found)} items")
                        break
                except Exception:
                    continue

            if not items:
                # Screenshot para debug
                try:
                    self.browser.screenshot("marketplace_debug.png")
                    logger.warning("Sin chats encontrados. Screenshot guardado en data/marketplace_debug.png")
                except Exception:
                    pass
                return []

            for item in items:
                try:
                    label = item.get_attribute("aria-label") or ""
                    href  = item.get_attribute("href") or ""

                    if not href or "/marketplace/t/" not in href:
                        continue

                    # Parsear "Chat en grupo: NOMBRE · PRODUCTO"
                    clean = label.replace("Chat en grupo:", "").strip()
                    if " · " in clean:
                        parts   = clean.split(" · ", 1)
                        name    = parts[0].strip()
                        product = parts[1].strip()
                    else:
                        name    = clean or f"Chat {href[-10:]}"
                        product = ""

                    chats.append({
                        "name":    name,
                        "product": product,
                        "url":     f"https://www.messenger.com{href}",
                        "href":    href,
                        "unread":  False
                    })
                except Exception:
                    continue

            # Detectar no leídos desde el label del tab
            try:
                tab = page.query_selector('[href="/marketplace/"]')
                if tab:
                    tab_label = tab.get_attribute("aria-label") or ""
                    import re
                    nums = re.findall(r'\d+', tab_label)
                    if nums:
                        unread_count = int(nums[0])
                        for i in range(min(unread_count, len(chats))):
                            chats[i]["unread"] = True
            except Exception:
                pass

            logger.info(f"Marketplace: {len(chats)} chats encontrados")
            return chats

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("leer chats de Marketplace", str(e))

    def summarize_marketplace(self, gpt_engine=None) -> str:
        """Resume los chats de Marketplace — siempre muestra todos, no solo no leídos."""
        chats = self.get_marketplace_chats()

        if not chats:
            return (
                "No encontré chats en Marketplace. "
                "Puede que la página no haya cargado completamente — "
                "intentá de nuevo en unos segundos."
            )

        unread = [c for c in chats if c.get("unread")]
        total  = len(chats)

        if gpt_engine and chats:
            context = "\n".join([
                f"- {c['name']} {'(NO LEÍDO)' if c.get('unread') else ''}: {c['product']}"
                for c in chats[:10]
            ])
            return gpt_engine.ask(
                f"Resumí estos chats de Marketplace. "
                f"Hay {total} en total, {len(unread)} sin leer:\n{context}",
                context="Sos Jarvis, asistente comercial. Sé conciso."
            )

        # Resumen sin IA
        lines = [f"Marketplace: {total} chats en total"]
        if unread:
            lines.append(f"  {len(unread)} sin leer:")
            for c in unread:
                lines.append(f"  • {c['name']} — {c['product'][:50]}")
        lines.append("Todos los chats:")
        for c in chats[:8]:
            marca = "🔴 " if c.get("unread") else "   "
            lines.append(f"  {marca}{c['name']} — {c['product'][:50]}")
        return "\n".join(lines)