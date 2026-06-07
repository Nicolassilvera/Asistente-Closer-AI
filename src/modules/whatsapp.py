# src/modules/whatsapp.py
import re
import time
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

WHATSAPP_URL = "https://web.whatsapp.com"

def _looks_like_phone(text: str) -> bool:
    """True si text parece número de teléfono (≥6 dígitos, sin letras)."""
    digits = re.sub(r'[\s\+\-\(\)]', '', text)
    return digits.isdigit() and len(digits) >= 6

def _normalize_phone_ar(phone: str) -> str:
    """
    Normaliza número argentino al formato internacional E.164 (sin +).
    Ej: '1140591621' → '541140591621', '011-4059-1621' → '541140591621'
    """
    d = re.sub(r'\D', '', phone)
    if d.startswith('54'):
        return d
    if d.startswith('0'):
        d = d[1:]   # quitar 0 de discado local
    return '54' + d

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
        """
        Envía un mensaje de WhatsApp.
        Si contact_name parece un número de teléfono, abre el chat directamente
        por URL (sin necesitar que el número esté en contactos).
        """
        logger.info(f"Enviando mensaje a {contact_name}...")
        try:
            if _looks_like_phone(contact_name):
                return self._send_by_phone(_normalize_phone_ar(contact_name), message)
            return self._send_by_name(contact_name, message)
        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"enviar mensaje a {contact_name}", str(e))

    def _send_by_phone(self, phone_e164: str, message: str) -> bool:
        """Abre el chat por número E.164 sin necesitar el contacto guardado."""
        url = f"https://web.whatsapp.com/send?phone={phone_e164}"
        logger.info(f"WhatsApp: navegando a chat directo → {url}")
        self.browser.navigate(url)
        return self._type_and_send(message, phone_e164)

    def _send_by_name(self, contact_name: str, message: str) -> bool:
        """Busca el contacto por nombre en la barra de búsqueda."""
        # Selectores de búsqueda (probados en WhatsApp Web es/en 2024-2025)
        search_selectors = [
            '[data-testid="chat-list-search"]',
            '[aria-label="Buscar un chat o iniciar uno nuevo"]',
            '[aria-label="Search or start new chat"]',
        ]
        search_box = None
        for sel in search_selectors:
            try:
                self.browser.wait_for(sel, timeout=4000)
                search_box = sel
                break
            except BrowserError:
                continue

        if not search_box:
            raise BrowserError(f"enviar mensaje a {contact_name}",
                               "No se encontró la barra de búsqueda de WhatsApp")

        self.browser.click(search_box)
        self.browser.page.keyboard.press("Control+A")
        self.browser.page.keyboard.press("Delete")
        self.browser.type_text(search_box, contact_name, delay=80)
        time.sleep(2)

        # Intentar click en resultado exacto o primer resultado
        result_selectors = [
            f'span[title="{contact_name}"]',
            '[data-testid="cell-frame-container"]',
            '[aria-label="Lista de resultados de búsqueda."] [role="listitem"]',
            '[role="listitem"]',
        ]
        clicked = False
        for sel in result_selectors:
            try:
                self.browser.wait_for(sel, timeout=3000)
                self.browser.page.query_selector(sel).click()
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            self.browser.page.keyboard.press("Enter")

        return self._type_and_send(message, contact_name)

    def _type_and_send(self, message: str, label: str = "") -> bool:
        """Espera el campo de mensaje, escribe y envía con Enter."""
        time.sleep(1)
        msg_selectors = [
            '[data-testid="conversation-compose-box-input"]',
            '[aria-label="Escribe un mensaje"]',
            '[aria-label="Type a message"]',
            'div[contenteditable="true"][data-tab="10"]',
        ]
        msg_box = None
        for sel in msg_selectors:
            try:
                self.browser.wait_for(sel, timeout=8000)
                msg_box = sel
                break
            except BrowserError:
                continue

        if not msg_box:
            raise BrowserError(f"enviar mensaje a {label}",
                               "No se encontró el campo de mensaje de WhatsApp")

        self.browser.type_text(msg_box, message, delay=60)
        time.sleep(0.3)
        self.browser.page.keyboard.press("Enter")
        logger.info(f"Mensaje enviado a {label}.")
        return True

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