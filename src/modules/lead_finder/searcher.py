# src/modules/lead_finder/searcher.py
import time
import random
from bs4 import BeautifulSoup
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

class GoogleSearcher:
    """
    Busca negocios en Google Maps y búsqueda orgánica.
    No usa APIs — usa Playwright para navegar como un humano.
    """

    def __init__(self, browser: BrowserEngine):
        self.browser = browser

    def search_businesses(
        self,
        category: str,
        city: str,
        max_results: int = 20
    ) -> list[dict]:
        """
        Busca negocios por rubro y ciudad.
        Devuelve lista de prospectos crudos para procesar.
        """
        results = []

        # Estrategia 1: Google Maps
        maps_results = self._search_google_maps(category, city, max_results)
        results.extend(maps_results)

        # Estrategia 2: búsqueda orgánica si Maps no alcanza
        if len(results) < max_results:
            organic = self._search_organic(category, city, max_results - len(results))
            results.extend(organic)

        logger.info(f"LeadFinder: {len(results)} resultados para '{category}' en '{city}'")
        return results[:max_results]

    def _search_google_maps(self, category: str, city: str, limit: int) -> list[dict]:
        """Busca en Google Maps y extrae datos de negocios."""
        query = f"{category} en {city}"
        url   = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

        try:
            logger.info(f"Buscando en Google Maps: {query}")
            self.browser.navigate(url, wait_until="networkidle")
            time.sleep(2)

            results = []
            page    = self.browser.page

            # Scroll para cargar más resultados
            for _ in range(3):
                page.evaluate("document.querySelector('[role=feed]')?.scrollBy(0, 1000)")
                time.sleep(1.5)

            # Extraer tarjetas de negocios
            cards = page.query_selector_all('[role=feed] > div > div > a')

            for card in cards[:limit]:
                try:
                    name = card.get_attribute("aria-label") or ""
                    href = card.get_attribute("href") or ""
                    if not name:
                        continue

                    # Click para ver detalles
                    card.click()
                    time.sleep(1.5)

                    data = self._extract_place_details(page)
                    data["company_name"] = name
                    data["source"]       = "google_maps"
                    data["category"]     = category
                    data["city"]         = city
                    results.append(data)

                    # Pausa humana entre clicks
                    time.sleep(random.uniform(0.8, 1.8))

                except Exception as e:
                    logger.debug(f"Error extrayendo tarjeta: {e}")
                    continue

            return results

        except BrowserError as e:
            logger.warning(f"Error en Google Maps: {e.message}")
            return []

    def _extract_place_details(self, page) -> dict:
        """Extrae detalles de un lugar en Google Maps."""
        data = {}

        extractors = {
            "phone":    ['[data-tooltip="Copiar número de teléfono"]',
                         'button[data-item-id^="phone"]'],
            "website":  ['a[data-item-id="authority"]',
                         '[data-tooltip="Abrir sitio web"]'],
            "address":  ['button[data-item-id="address"]',
                         '[data-tooltip="Copiar dirección"]'],
        }

        for field, selectors in extractors.items():
            for sel in selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        data[field] = el.inner_text().strip()
                        break
                except Exception:
                    continue

        # Rating
        try:
            rating_el = page.query_selector('[jsaction*="pane.rating"]')
            if rating_el:
                data["rating"] = rating_el.inner_text().strip()
        except Exception:
            pass

        return data

    def _search_organic(self, category: str, city: str, limit: int) -> list[dict]:
        """Búsqueda orgánica en Google como fallback."""
        query = f'"{category}" "{city}" contacto OR teléfono OR whatsapp'
        url   = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=20"

        try:
            logger.info(f"Búsqueda orgánica: {query}")
            self.browser.navigate(url)
            time.sleep(1.5)

            html = self.browser.page.content()
            soup = BeautifulSoup(html, "html.parser")

            results = []
            for result in soup.select("div.g")[:limit]:
                try:
                    title_el = result.select_one("h3")
                    link_el  = result.select_one("a")
                    desc_el  = result.select_one("div.VwiC3b")

                    if not title_el:
                        continue

                    results.append({
                        "company_name": title_el.get_text(),
                        "website":      link_el["href"] if link_el else "",
                        "notes":        desc_el.get_text() if desc_el else "",
                        "source":       "google_organic",
                        "category":     category,
                        "city":         city,
                    })
                except Exception:
                    continue

            return results

        except BrowserError as e:
            logger.warning(f"Error en búsqueda orgánica: {e.message}")
            return []