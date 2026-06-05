# src/modules/lead_finder/scorer.py
import json
from src.core.logger import logger

class LeadScorer:
    """
    Puntúa prospectos del 0 al 10 basándose en los datos disponibles.
    Funciona sin OpenAI — lógica de reglas + bonus por datos.
    Cuando OpenAI esté disponible, puede mejorar el scoring con IA.
    """

    def score(self, lead: dict) -> float:
        """Calcula el score de un lead. Devuelve float 0-10."""
        score = 5.0  # base

        # ── Bonus por datos disponibles ──────────────────────────────────
        if lead.get("phone"):    score += 1.0
        if lead.get("whatsapp"): score += 1.0
        if lead.get("website"):  score += 0.5
        if lead.get("instagram"):score += 0.5
        if lead.get("email"):    score += 0.5

        # ── Bonus por fuente ──────────────────────────────────────────────
        source_bonus = {
            "google_maps":    1.0,
            "facebook":       0.8,
            "instagram":      0.6,
            "google_organic": 0.4,
            "manual":         0.2,
        }
        score += source_bonus.get(lead.get("source", ""), 0)

        # ── Bonus por rating de Google ─────────────────────────────────────
        rating = lead.get("rating", "")
        if rating:
            try:
                r = float(rating.replace(",", ".").split()[0])
                if r >= 4.5: score += 1.0
                elif r >= 4.0: score += 0.5
            except ValueError:
                pass

        # ── Penalización por datos faltantes ──────────────────────────────
        if not lead.get("phone") and not lead.get("whatsapp"):
            score -= 1.5  # sin contacto directo, difícil llegar

        return round(min(max(score, 0), 10), 1)

    def classify_priority(self, score: float) -> str:
        """Convierte score en prioridad."""
        if score >= 8:   return "alta"
        elif score >= 6: return "media"
        else:            return "baja"

    def classify_status(self, score: float) -> str:
        """Estado inicial según score."""
        if score >= 8:   return "prioritario"
        elif score >= 5: return "nuevo"
        else:            return "analizado"

    def score_batch(self, leads: list[dict]) -> list[dict]:
        """Puntúa una lista de leads y agrega score + prioridad."""
        for lead in leads:
            lead["lead_score"] = self.score(lead)
            lead["priority"]   = self.classify_priority(lead["lead_score"])
            lead["lead_status"]= self.classify_status(lead["lead_score"])
        return sorted(leads, key=lambda x: x["lead_score"], reverse=True)