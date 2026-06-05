# src/modules/facebook.py
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

MARKETPLACE_URL = "https://www.facebook.com/marketplace"
INBOX_URL       = "https://www.facebook.com/messages"

class FacebookModule:
    """
    Módulo para Facebook Marketplace y mensajes.
    
    Primera vez: requiere login manual del usuario.
    Después: usa la sesión guardada automáticamente.
    """

    def __init__(self, browser: BrowserEngine):
        self.browser = browser

    def open_marketplace(self) -> bool:
        """Abre Facebook Marketplace."""
        try:
            logger.info("Abriendo Facebook Marketplace...")
            self.browser.navigate(MARKETPLACE_URL)

            # Detectar si pide login
            if self._needs_login():
                logger.warning("Facebook requiere login.")
                return False

            # Esperar que cargue el Marketplace
            self.browser.wait_for('[aria-label="Marketplace"]', timeout=15000)
            logger.info("Marketplace abierto correctamente.")
            return True

        except BrowserError as e:
            logger.error(f"Error abriendo Marketplace: {e.message}")
            raise

    def open_inbox(self) -> bool:
        """Abre los mensajes de Facebook."""
        try:
            logger.info("Abriendo mensajes de Facebook...")
            self.browser.navigate(INBOX_URL)

            if self._needs_login():
                return False

            self.browser.wait_for('[aria-label="Chats"]', timeout=15000)
            logger.info("Mensajes abiertos correctamente.")
            return True

        except BrowserError:
            raise

    def get_unread_messages(self) -> list[dict]:
        """
        Lee los mensajes no leídos del inbox.
        Devuelve lista de {sender, preview, url}
        """
        try:
            self.open_inbox()

            # Esperar lista de conversaciones
            self.browser.wait_for('[role="navigation"]', timeout=10000)

            # Buscar conversaciones con indicador de no leído
            page = self.browser.page
            conversations = page.query_selector_all('[aria-label*="unread"]')

            messages = []
            for conv in conversations[:10]:  # máximo 10
                try:
                    sender  = conv.query_selector('[data-testid="mwthreadlist-item-title"]')
                    preview = conv.query_selector('[data-testid="mwthreadlist-item-preview"]')
                    link    = conv.get_attribute("href") or ""

                    messages.append({
                        "sender":  sender.inner_text()  if sender  else "Desconocido",
                        "preview": preview.inner_text() if preview else "",
                        "url":     f"https://www.facebook.com{link}"
                    })
                except Exception:
                    continue

            logger.info(f"Se encontraron {len(messages)} mensajes no leídos.")
            return messages

        except BrowserError:
            raise

    def send_message(self, conversation_url: str, message: str) -> bool:
        """Envía un mensaje a una conversación específica."""
        try:
            logger.info(f"Enviando mensaje a: {conversation_url}")
            self.browser.navigate(conversation_url)

            # Esperar el campo de texto
            self.browser.wait_for('[aria-label="Message"]', timeout=10000)
            self.browser.type_text('[aria-label="Message"]', message)

            # Enviar con Enter
            self.browser.page.keyboard.press("Enter")
            logger.info("Mensaje enviado correctamente.")
            return True

        except BrowserError:
            raise

    def search_marketplace(self, query: str, location: str = "") -> list[dict]:
        """Busca productos en Marketplace."""
        try:
            search_url = f"{MARKETPLACE_URL}/search?query={query}"
            if location:
                search_url += f"&location={location}"

            self.browser.navigate(search_url)
            self.browser.wait_for('[data-testid="marketplace_feed_item"]', timeout=15000)

            page = self.browser.page
            items = page.query_selector_all('[data-testid="marketplace_feed_item"]')

            results = []
            for item in items[:10]:
                try:
                    title = item.query_selector('[data-testid="marketplace_listing_title"]')
                    price = item.query_selector('[data-testid="marketplace_listing_price"]')
                    results.append({
                        "title": title.inner_text() if title else "",
                        "price": price.inner_text() if price else ""
                    })
                except Exception:
                    continue

            logger.info(f"Marketplace: {len(results)} resultados para '{query}'.")
            return results

        except BrowserError:
            raise

    def _needs_login(self) -> bool:
        """Detecta si Facebook está pidiendo login."""
        try:
            current_url = self.browser.page.url
            return "login" in current_url or "checkpoint" in current_url
        except Exception:
            return False