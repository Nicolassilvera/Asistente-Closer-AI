# src/modules/lead_finder/finder.py
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.core.browser import BrowserEngine
from src.core.repositories import LeadRepository, LeadEventRepository
from src.core.logger import logger
from src.core.exceptions import JarvisError
from src.modules.lead_finder.searcher import GoogleSearcher
from src.modules.lead_finder.scorer import LeadScorer

console = Console()

class LeadFinder:
    """
    Módulo principal de prospección.
    Coordina búsqueda → scoring → deduplicación → guardado.
    """

    def __init__(self):
        self.browser    = BrowserEngine()
        self.scorer     = LeadScorer()
        self.leads_repo = LeadRepository()
        self.event_repo = LeadEventRepository()
        self._started   = False

    def start(self):
        if not self._started:
            self.browser.start(headless=False)
            self._started = True

    def find(
        self,
        category: str,
        city: str,
        max_results: int = 20,
        auto_save: bool = True
    ) -> list[dict]:
        """
        Busca prospectos, los puntúa y los guarda.
        
        Ejemplo:
            finder.find("restaurantes", "Rosario", max_results=15)
        """
        self.start()
        searcher = GoogleSearcher(self.browser)

        console.print(f"\n[yellow]🔍 Buscando:[/yellow] {category} en {city}...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("Buscando prospectos...", total=None)

            # 1. Buscar
            raw_leads = searcher.search_businesses(category, city, max_results)
            progress.update(task, description=f"Encontrados: {len(raw_leads)}. Puntuando...")

            # 2. Puntuar
            scored = self.scorer.score_batch(raw_leads)

            # 3. Deduplicar contra la BD
            deduped = self._deduplicate(scored)
            progress.update(task, description=f"Guardando {len(deduped)} leads nuevos...")

            # 4. Guardar
            if auto_save:
                saved = self._save_all(deduped, category, city)
            else:
                saved = deduped

        # 5. Mostrar resultado
        self._show_results(saved, category, city)
        return saved

    def _deduplicate(self, leads: list[dict]) -> list[dict]:
        """Filtra leads que ya existen en la BD por nombre + ciudad."""
        new_leads = []
        for lead in leads:
            existing = self.leads_repo.search(lead["company_name"])
            already  = any(
                e["city"] == lead.get("city") and
                e["company_name"].lower() == lead["company_name"].lower()
                for e in existing
            )
            if not already:
                new_leads.append(lead)
            else:
                logger.debug(f"Duplicado saltado: {lead['company_name']}")

        logger.info(f"Deduplicación: {len(leads)} → {len(new_leads)} leads nuevos")
        return new_leads

    def _save_all(self, leads: list[dict], category: str, city: str) -> list[dict]:
        """Guarda todos los leads en la BD y registra el evento."""
        saved = []
        for lead in leads:
            try:
                lead_id = self.leads_repo.create(lead)
                self.event_repo.log(
                    lead_id,
                    "lead_detectado",
                    f"Encontrado via LeadFinder — {category} en {city} "
                    f"(score: {lead['lead_score']})",
                    "jarvis"
                )
                lead["id"] = lead_id
                saved.append(lead)
            except JarvisError as e:
                logger.warning(f"Error al guardar lead {lead.get('company_name')}: {e.message}")

        logger.info(f"Guardados {len(saved)} leads nuevos en la BD.")
        return saved

    def _show_results(self, leads: list[dict], category: str, city: str):
        """Muestra los resultados en una tabla en consola."""
        if not leads:
            console.print(f"[dim]No se encontraron leads nuevos para {category} en {city}.[/dim]")
            return

        # Resumen
        alta  = sum(1 for l in leads if l.get("priority") == "alta")
        media = sum(1 for l in leads if l.get("priority") == "media")
        baja  = sum(1 for l in leads if l.get("priority") == "baja")

        console.print(
            f"\n[green]✓ {len(leads)} leads encontrados:[/green] "
            f"[red]{alta} alta[/red] · "
            f"[yellow]{media} media[/yellow] · "
            f"[dim]{baja} baja[/dim] prioridad\n"
        )

        table = Table(show_lines=True, title=f"{category.title()} — {city}")
        table.add_column("Empresa",   style="bold", max_width=30)
        table.add_column("Teléfono",  style="dim",  max_width=18)
        table.add_column("Score",     justify="center", width=8)
        table.add_column("Prioridad", justify="center", width=10)
        table.add_column("Fuente",    style="dim",  width=14)

        priority_colors = {"alta": "red", "media": "yellow", "baja": "dim"}

        for lead in leads:
            color = priority_colors.get(lead.get("priority", "baja"), "dim")
            table.add_row(
                lead.get("company_name", "")[:30],
                lead.get("phone") or lead.get("whatsapp") or "—",
                f"★ {lead.get('lead_score', 0)}",
                f"[{color}]{lead.get('priority', '—')}[/{color}]",
                lead.get("source", "—")
            )

        console.print(table)
        console.print(
            "[dim]Los leads ya están en el CRM. "
            "Abrí http://localhost:5173 para verlos.[/dim]\n"
        )

    def close(self):
        if self._started:
            self.browser.close()
            self._started = False