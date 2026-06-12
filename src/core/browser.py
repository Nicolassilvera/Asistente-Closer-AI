# src/core/browser.py
import os
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from src.core.logger import logger
from src.core.exceptions import BrowserError

SESSION_DIR  = "data/browser_sessions"
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")

class BrowserEngine:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        os.makedirs(SESSION_DIR, exist_ok=True)

    def _kill_edge_profile(self):
        """Libera el bloqueo del perfil cerrando el contexto si existe."""
        try:
            if self._context:
                self._context.close()
                self._context = None
        except Exception as e:
            logger.debug(f"No se pudo liberar perfil: {e}")

    # --->        

    def start(self, headless: bool = False) -> "BrowserEngine":
        try:
            self._playwright = sync_playwright().start()
    
            profile_dir = os.path.join(SESSION_DIR, "edge_profile")
            os.makedirs(profile_dir, exist_ok=True)
    
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="msedge",
                headless=headless,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                viewport=None,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
                )
            )
            self._page = self._context.new_page()
            logger.info("Navegador iniciado correctamente.")
            return self
    
        except Exception as e:
            raise BrowserError("inicio del navegador", str(e))

    # --->    

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> "BrowserEngine":
        try:
            logger.info(f"Navegando a: {url}")
            self._page.goto(url, wait_until=wait_until, timeout=60000)
            return self
        except Exception as e:
            err = str(e).lower()
            if "closed" in err or "target page" in err:
                # Navegador cerrado — rearrancar limpio
                logger.warning("Navegador cerrado detectado. Reabriendo...")
                from rich.console import Console
                Console().print("[yellow]⚠ Navegador cerrado. Reabriendo...[/yellow]")
                try:
                    if self._context:
                        self._context.close()
                except Exception:
                    pass
                try:
                    if self._playwright:
                        self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
                self._context    = None
                self._page       = None
                # Rearrancar y reintentar la navegación
                self.start()
                self._page.goto(url, wait_until=wait_until, timeout=60000)
                return self
            raise BrowserError(f"navegar a {url}", str(e))

    # ---> 
    def ensure_open(self) -> bool:
        """Verifica que el navegador esté abierto. Sin magia de threads."""
        try:
            if self._page and not self._page.is_closed():
                return True
        except Exception:
            pass
        return False
    # ---> 

    def wait_for(self, selector: str, timeout: int = 30000) -> "BrowserEngine":
        try:
            self._page.wait_for_selector(selector, timeout=timeout)
            return self
        except Exception as e:
            raise BrowserError(f"esperar elemento '{selector}'", str(e))

    def wait_for_human(
        self,
        selector: str,
        timeout_minutes: int = 3,
        message: str = "Esperando acción del usuario..."
    ) -> bool:
        from rich.console import Console
        from rich.prompt import Confirm
        console = Console()

        timeout_ms = timeout_minutes * 60 * 1000
        console.print(f"\n[yellow]⏳ {message}[/yellow]")
        console.print(f"[dim]Tiempo máximo: {timeout_minutes} minutos[/dim]\n")

        try:
            self._page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            console.print(f"\n[yellow]⚠ Tiempo agotado esperando: {message}[/yellow]")
            try:
                if Confirm.ask("¿Seguimos esperando?"):
                    return self.wait_for_human(selector, timeout_minutes, message)
            except KeyboardInterrupt:
                pass
            return False

    def click(self, selector: str) -> "BrowserEngine":
        try:
            self._page.click(selector, timeout=10000)
            logger.debug(f"Click en: {selector}")
            return self
        except Exception as e:
            raise BrowserError(f"click en '{selector}'", str(e))

    def type_text(self, selector: str, text: str, delay: int = 50) -> "BrowserEngine":
        try:
            self._page.click(selector)
            self._page.type(selector, text, delay=delay)
            logger.debug(f"Texto escrito en: {selector}")
            return self
        except Exception as e:
            raise BrowserError(f"escribir en '{selector}'", str(e))

    def get_text(self, selector: str) -> str:
        try:
            return self._page.inner_text(selector, timeout=10000)
        except Exception as e:
            raise BrowserError(f"leer texto de '{selector}'", str(e))

    def get_all_texts(self, selector: str) -> list[str]:
        try:
            elements = self._page.query_selector_all(selector)
            return [el.inner_text() for el in elements]
        except Exception as e:
            raise BrowserError(f"leer textos de '{selector}'", str(e))

    def screenshot(self, filename: str = "screenshot.png") -> str:
        try:
            path = f"data/{filename}"
            self._page.screenshot(path=path)
            return path
        except Exception as e:
            raise BrowserError("tomar screenshot", str(e))

    def is_open(self) -> bool:
        try:
            return self._page is not None and not self._page.is_closed()
        except Exception:
            return False

    @property
    def page(self) -> Page:
        if not self._page:
            raise BrowserError("acceder a la página", "Navegador no iniciado")
        return self._page

    def close(self):
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        logger.info("Navegador cerrado.")

