# src/modules/lead_finder/searcher.py
import re
import time
import random
from bs4 import BeautifulSoup
from src.core.browser import BrowserEngine
from src.core.logger import logger
from src.core.exceptions import BrowserError

# Rutas de Instagram/Facebook que no son handles de negocios
_IG_SKIP = {"explore", "accounts", "direct", "p", "reel", "stories", "tv", "about", "help"}
_FB_SKIP = {"sharer", "share", "dialog", "plugins", "login", "l.php",
            "events", "groups", "pages", "photo", "photos", "video", "videos"}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
# Evitar falsos positivos en emails
_EMAIL_JUNK = ("example.", "noreply", "no-reply", "wix.", "sentry.", "schema.",
               "spe.ctation", ".png", ".jpg", ".gif", "w3.org", "googleapis")


class GoogleSearcher:
    """
    Busca negocios en Google Maps y búsqueda orgánica.
    No usa APIs — usa Playwright para navegar como un humano.

    Pipeline por negocio:
      1. Google Maps → datos básicos (teléfono, web, dirección, rating, redes del panel)
      2. Sitio web propio → enriquecimiento (email, WhatsApp, Instagram, Facebook)
    """

    def __init__(self, browser: BrowserEngine):
        self.browser = browser

    # ──────────────────────────────────────────────────────────────────────────
    #  Punto de entrada
    # ──────────────────────────────────────────────────────────────────────────

    def search_businesses(self, category: str, city: str, max_results: int = 20) -> list[dict]:
        results = self._search_google_maps(category, city, max_results)

        if len(results) < max_results:
            organic = self._search_organic(category, city, max_results - len(results))
            results.extend(organic)

        logger.info(f"LeadFinder: {len(results)} resultados para '{category}' en '{city}'")
        return results[:max_results]

    # ──────────────────────────────────────────────────────────────────────────
    #  Google Maps
    # ──────────────────────────────────────────────────────────────────────────

    def _search_google_maps(self, category: str, city: str, limit: int) -> list[dict]:
        query = f"{category} en {city}"
        url   = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

        try:
            logger.info(f"Google Maps: {query}")
            self.browser.navigate(url, wait_until="load")

            page = self.browser.page

            # Esperar a que aparezca el feed de resultados (hasta 30s)
            try:
                page.wait_for_selector('[role=feed]', timeout=30000)
            except Exception:
                logger.warning("Google Maps: feed no apareció en 30s, intentando igual")
                time.sleep(3)

            results = []

            # Cargar más resultados haciendo scroll en el feed
            for _ in range(4):
                page.evaluate("document.querySelector('[role=feed]')?.scrollBy(0, 1200)")
                time.sleep(1.5)

            cards = page.query_selector_all('[role=feed] > div > div > a')

            for card in cards[:limit]:
                try:
                    name = card.get_attribute("aria-label") or ""
                    if not name:
                        continue

                    card.click()
                    time.sleep(1.5)

                    data = self._extract_place_details(page)
                    data["company_name"] = name
                    data["source"]       = "google_maps"
                    data["category"]     = category
                    data["city"]         = city

                    # Enriquecer con datos del sitio web propio
                    if data.get("website"):
                        web_data = self._scrape_website(data["website"])
                        for key, val in web_data.items():
                            if val and not data.get(key):
                                data[key] = val
                        logger.debug(
                            f"  Web '{data['company_name']}': "
                            f"email={bool(web_data.get('email'))} "
                            f"wa={bool(web_data.get('whatsapp'))} "
                            f"ig={bool(web_data.get('instagram'))} "
                            f"fb={bool(web_data.get('facebook'))}"
                        )

                    results.append(data)
                    time.sleep(random.uniform(0.8, 1.8))

                except Exception as e:
                    logger.debug(f"Error en tarjeta Maps: {e}")
                    continue

            return results

        except BrowserError as e:
            logger.warning(f"Error en Google Maps: {e.message}")
            return []

    def _extract_place_details(self, page) -> dict:
        """Extrae todos los datos del panel lateral de Google Maps."""
        data = {}

        # Campos estructurados del panel
        # data-item-id selectors son más fiables que los basados en texto locale
        extractors = {
            "phone": [
                'button[data-item-id^="phone"]',
                '[data-tooltip="Copiar número de teléfono"]',
                '[data-tooltip="Copy phone number"]',
                'button[aria-label*="teléfono"]',
                'button[aria-label*="phone"]',
            ],
            "website": [
                'a[data-item-id="authority"]',
                '[data-tooltip="Abrir sitio web"]',
                '[data-tooltip="Open website"]',
                'a[aria-label*="sitio web"]',
                'a[aria-label*="website"]',
            ],
            "address": [
                'button[data-item-id="address"]',
                '[data-tooltip="Copiar dirección"]',
                '[data-tooltip="Copy address"]',
                'button[aria-label*="Dirección"]',
                'button[aria-label*="Address"]',
            ],
        }
        for field, selectors in extractors.items():
            for sel in selectors:
                try:
                    el = page.query_selector(sel)
                    if not el:
                        continue
                    # Para website usamos el href real, no el texto visible
                    if field == "website":
                        href = el.get_attribute("href") or ""
                        if href and href.startswith("http"):
                            data[field] = href
                            break
                    else:
                        val = el.inner_text().strip()
                        if val:
                            data[field] = val
                            break
                except Exception:
                    continue

        # Si el teléfono no se encontró, intentar por aria-label en el panel
        if not data.get("phone"):
            try:
                for btn in page.query_selector_all('button[aria-label]'):
                    label = btn.get_attribute("aria-label") or ""
                    if any(kw in label.lower() for kw in ("teléfono", "phone", "tel.", "llam")):
                        txt = btn.inner_text().strip()
                        # Verificar que el texto parece un número de teléfono
                        digits = re.sub(r'\D', '', txt)
                        if 7 <= len(digits) <= 15:
                            data["phone"] = txt
                            break
            except Exception:
                pass

        # Rating de Google
        try:
            for sel in ['div.F7nice span[aria-hidden]', '[jsaction*="pane.rating"]',
                        'span[aria-label*="estrellas"]', 'span[aria-label*="stars"]']:
                el = page.query_selector(sel)
                if el:
                    txt = el.inner_text().strip()
                    if txt:
                        data["rating"] = txt
                        break
        except Exception:
            pass

        # Links a redes sociales en el panel de Maps
        try:
            social_links = page.query_selector_all(
                'a[href*="instagram.com"], a[href*="facebook.com"]'
            )
            for link in social_links:
                href = (link.get_attribute("href") or "").split("?")[0].rstrip("/")
                if not href:
                    continue

                if "instagram.com/" in href and not data.get("instagram"):
                    slug = href.split("instagram.com/")[-1].strip("/").split("/")[0]
                    if slug and slug not in _IG_SKIP:
                        data["instagram"] = f"@{slug}"

                elif "facebook.com/" in href and not data.get("facebook"):
                    slug = href.split("facebook.com/")[-1].strip("/").split("/")[0]
                    if slug and slug not in _FB_SKIP:
                        data["facebook"] = href

        except Exception:
            pass

        return data

    # ──────────────────────────────────────────────────────────────────────────
    #  Scraping del sitio web del negocio
    # ──────────────────────────────────────────────────────────────────────────

    def _scrape_website(self, url: str) -> dict:
        """
        Visita el sitio web en una pestaña nueva y extrae:
        email, whatsapp, phone, instagram, facebook.
        Cierra la pestaña al terminar — no interrumpe la sesión de Maps.
        """
        data     = {}
        new_page = None
        try:
            new_page = self.browser.page.context.new_page()
            new_page.goto(url, timeout=15000, wait_until="domcontentloaded")
            time.sleep(0.8)

            html = new_page.content()
            soup = BeautifulSoup(html, "html.parser")

            # ── Recorrer todos los <a href="..."> ─────────────────────────
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if not href:
                    continue

                # Email
                if href.lower().startswith("mailto:") and not data.get("email"):
                    email = href[7:].split("?")[0].strip()
                    if "@" in email and not any(j in email for j in _EMAIL_JUNK):
                        data["email"] = email

                # WhatsApp via wa.me
                elif "wa.me/" in href and not data.get("whatsapp"):
                    num = href.split("wa.me/")[-1].split("?")[0].strip("/")
                    if num.isdigit() and 10 <= len(num) <= 15:
                        data["whatsapp"] = f"+{num}"

                # WhatsApp via api.whatsapp.com
                elif "api.whatsapp.com/send" in href and not data.get("whatsapp"):
                    m = re.search(r"phone=(\d{10,15})", href)
                    if m:
                        data["whatsapp"] = f"+{m.group(1)}"

                # Teléfono
                elif href.lower().startswith("tel:") and not data.get("phone"):
                    phone = href[4:].strip().replace(" ", "")
                    if phone:
                        data["phone"] = phone

                # Instagram
                elif "instagram.com/" in href and not data.get("instagram"):
                    slug = href.split("instagram.com/")[-1].split("?")[0].rstrip("/").split("/")[0]
                    if slug and slug not in _IG_SKIP:
                        data["instagram"] = f"@{slug}"

                # Facebook
                elif "facebook.com/" in href and not data.get("facebook"):
                    clean = href.split("?")[0].rstrip("/")
                    slug  = clean.split("facebook.com/")[-1].strip("/").split("/")[0]
                    if slug and slug not in _FB_SKIP and not slug.startswith("http"):
                        data["facebook"] = clean

            # ── Email por regex en el texto si no se encontró por mailto ──
            if not data.get("email"):
                # Buscar en texto visible (links y párrafos)
                text_candidates = [a.get_text() for a in soup.find_all("a")]
                text_candidates.append(soup.get_text(" "))
                for text in text_candidates:
                    m = EMAIL_RE.search(text)
                    if m:
                        candidate = m.group(0)
                        if not any(j in candidate for j in _EMAIL_JUNK):
                            data["email"] = candidate
                            break

        except Exception as e:
            logger.debug(f"_scrape_website({url}): {e}")
        finally:
            if new_page:
                try:
                    new_page.close()
                except Exception:
                    pass

        return data

    # ──────────────────────────────────────────────────────────────────────────
    #  Búsqueda orgánica (fallback)
    # ──────────────────────────────────────────────────────────────────────────

    def _search_organic(self, category: str, city: str, limit: int) -> list[dict]:
        """Búsqueda orgánica en Google como fallback cuando Maps no alcanza."""
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

                    website = link_el["href"] if link_el else ""
                    entry   = {
                        "company_name": title_el.get_text(),
                        "website":      website,
                        "notes":        desc_el.get_text() if desc_el else "",
                        "source":       "google_organic",
                        "category":     category,
                        "city":         city,
                    }

                    # Intentar enriquecer el resultado orgánico también
                    if website and website.startswith("http"):
                        web_data = self._scrape_website(website)
                        for key, val in web_data.items():
                            if val and not entry.get(key):
                                entry[key] = val

                    results.append(entry)
                except Exception:
                    continue

            return results

        except BrowserError as e:
            logger.warning(f"Error en búsqueda orgánica: {e.message}")
            return []
