# src/modules/whatsapp.py
import time
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

WHATSAPP_URL = "https://web.whatsapp.com"

class WhatsAppModule:
    def __init__(self, browser: BrowserEngine):
        self.browser = browser

    def open(self) -> bool:
        try:
            logger.info("Abriendo WhatsApp Web...")
            self.browser.navigate(WHATSAPP_URL)
            time.sleep(3)

            # Detectar si hay QR para escanear
            if self._needs_qr_scan():
                from rich.console import Console
                Console().print(
                    "\n[bold yellow]📱 WhatsApp pide escanear el QR[/bold yellow]\n"
                    "[dim]Abrí WhatsApp en tu celular → "
                    "Dispositivos vinculados → Vincular dispositivo[/dim]\n"
                )

                # Esperar hasta 3 minutos con pausa humana
                ok = self.browser.wait_for_human(
                    selector='[data-testid="chat-list"]',
                    timeout_minutes=3,
                    message="Esperando que escanees el QR de WhatsApp..."
                )

                if not ok:
                    raise BrowserError("abrir WhatsApp", "QR no escaneado a tiempo")

                Console().print("[green]✓ WhatsApp conectado correctamente.[/green]\n")
                return True

            # Ya estaba logueado — esperar que cargue
            ok = self.browser.wait_for_human(
                selector='[data-testid="chat-list"]',
                timeout_minutes=1,
                message="Cargando WhatsApp Web..."
            )

            if not ok:
                raise BrowserError("abrir WhatsApp", "No cargó a tiempo")

            logger.info("WhatsApp Web listo.")
            return True

        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError("abrir WhatsApp Web", str(e))

#-------

    def send_message(self, contact_name: str, message: str) -> bool:
        try:
            logger.info(f"Enviando mensaje a {contact_name}...")
    
            # Selector real detectado en WhatsApp Web en español
            search_box = '[aria-label="Buscar un chat o iniciar uno nuevo"]'
            
            self.browser.wait_for(search_box, timeout=15000)
            self.browser.click(search_box)
    
            # Limpiar y escribir el nombre
            self.browser.page.keyboard.press("Control+A")
            self.browser.page.keyboard.press("Delete")
            self.browser.type_text(search_box, contact_name, delay=80)
            time.sleep(2)
    
            # Intentar contacto exacto por título
            result_selector = f'span[title="{contact_name}"]'
            try:
                self.browser.wait_for(result_selector, timeout=5000)
                self.browser.click(result_selector)
            except BrowserError:
                # Tomar el primer resultado de la lista
                first = '[aria-label="Lista de resultados de búsqueda."] [role="listitem"]'
                try:
                    self.browser.wait_for(first, timeout=5000)
                    self.browser.page.query_selector(first).click()
                except Exception:
                    # Último fallback — primer item genérico
                    self.browser.page.keyboard.press("Enter")
    
            time.sleep(1.5)
    
            # Campo de escritura del chat
            msg_box = '[aria-label="Escribe un mensaje"]'
            try:
                self.browser.wait_for(msg_box, timeout=10000)
            except BrowserError:
                # Fallback selector alternativo
                msg_box = '[contenteditable="true"][data-tab="10"]'
                self.browser.wait_for(msg_box, timeout=5000)
    
            self.browser.type_text(msg_box, message, delay=60)
            self.browser.page.keyboard.press("Enter")
    
            logger.info(f"Mensaje enviado a {contact_name}.")
            return True
    
        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"enviar mensaje a {contact_name}", str(e))

#-------


    def get_unread_chats(self) -> list[dict]:
        try:
            page   = self.browser.page
            unread = page.query_selector_all('[data-testid="icon-unread-count"]')
            chats  = []
            for badge in unread[:10]:
                try:
                    container = badge.evaluate_handle(
                        "el => el.closest('[data-testid=\"cell-frame-container\"]')"
                    )
                    name_el = container.query_selector('[data-testid="conversation-title"]')
                    prev_el = container.query_selector('[data-testid="last-msg"]')
                    chats.append({
                        "name":    name_el.inner_text() if name_el else "Desconocido",
                        "preview": prev_el.inner_text() if prev_el else "",
                        "unread":  badge.inner_text()
                    })
                except Exception:
                    continue
            return chats
        except Exception as e:
            raise BrowserError("leer chats no leídos", str(e))

    def _needs_qr_scan(self) -> bool:
        try:
            return self.browser.page.query_selector(
                '[data-testid="qrcode"], canvas[aria-label*="QR"]'
            ) is not None
        except Exception:
            return False