# src/core/repositories.py
import uuid
from datetime import datetime
from typing import Optional
from src.core.database import get_connection
from src.core.logger import logger
from src.core.exceptions import DatabaseError

def now() -> str:
    return datetime.now().isoformat()

# ══════════════════════════════════════════════════════
#  LEADS
# ══════════════════════════════════════════════════════

class LeadRepository:

    def create(self, data: dict) -> str:
        """Crea un lead nuevo. Devuelve su ID."""
        lead_id = str(uuid.uuid4())
        t = now()
        try:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO leads (
                        id, company_name, contact_name, category,
                        city, province, country, phone, whatsapp,
                        instagram, website, email, source, notes,
                        lead_score, lead_status, assigned_to, tags,
                        priority, business_type, activity_level,
                        estimated_volume, followup_date, created_at, updated_at
                    ) VALUES (
                        :id, :company_name, :contact_name, :category,
                        :city, :province, :country, :phone, :whatsapp,
                        :instagram, :website, :email, :source, :notes,
                        :lead_score, :lead_status, :assigned_to, :tags,
                        :priority, :business_type, :activity_level,
                        :estimated_volume, :followup_date, :created_at, :updated_at
                    )
                """, {
                    "id": lead_id,
                    "company_name":    data.get("company_name", ""),
                    "contact_name":    data.get("contact_name"),
                    "category":        data.get("category"),
                    "city":            data.get("city"),
                    "province":        data.get("province"),
                    "country":         data.get("country", "Argentina"),
                    "phone":           data.get("phone"),
                    "whatsapp":        data.get("whatsapp"),
                    "instagram":       data.get("instagram"),
                    "website":         data.get("website"),
                    "email":           data.get("email"),
                    "source":          data.get("source", "manual"),
                    "notes":           data.get("notes"),
                    "lead_score":      data.get("lead_score", 0),
                    "lead_status":     data.get("lead_status", "nuevo"),
                    "assigned_to":     data.get("assigned_to", "jarvis"),
                    "tags":            data.get("tags"),
                    "priority":        data.get("priority", "media"),
                    "business_type":   data.get("business_type"),
                    "activity_level":  data.get("activity_level"),
                    "estimated_volume":data.get("estimated_volume"),
                    "followup_date":   data.get("followup_date"),
                    "created_at":      t,
                    "updated_at":      t,
                })
            logger.debug(f"Lead creado: {lead_id[:8]} — {data.get('company_name')}")
            return lead_id
        except Exception as e:
            raise DatabaseError(f"Error al crear lead: {e}")

    def get_by_id(self, lead_id: str) -> Optional[dict]:
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM leads WHERE id = ?", (lead_id,)
                ).fetchone()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseError(f"Error al obtener lead: {e}")

    def get_all(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        business_type: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """Lista leads con filtros opcionales."""
        try:
            query  = "SELECT * FROM leads WHERE 1=1"
            params = []
            if status:
                query += " AND lead_status = ?"
                params.append(status)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            if business_type:
                query += " AND business_type = ?"
                params.append(business_type)
            query += " ORDER BY lead_score DESC, created_at DESC LIMIT ?"
            params.append(limit)

            with get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error al listar leads: {e}")

    def get_hot(self) -> list[dict]:
        """Leads calientes — score alto o estado activo."""
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM leads
                    WHERE lead_status IN ('caliente','interesado','negociacion')
                       OR (lead_score >= 7 AND lead_status NOT IN ('cerrado','descartado'))
                    ORDER BY lead_score DESC, last_contact_at DESC
                    LIMIT 20
                """).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error al obtener leads calientes: {e}")

    def get_pending_followup(self) -> list[dict]:
        """Leads con seguimiento pendiente para hoy o vencido."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM leads
                    WHERE followup_date IS NOT NULL
                      AND followup_date <= ?
                      AND lead_status NOT IN ('cerrado','descartado')
                    ORDER BY followup_date ASC
                    LIMIT 50
                """, (today,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error al obtener seguimientos: {e}")

    def update_status(self, lead_id: str, status: str, notes: str = "") -> bool:
        """Cambia el estado de un lead."""
        try:
            with get_connection() as conn:
                conn.execute("""
                    UPDATE leads
                    SET lead_status = ?, notes = COALESCE(notes,'') || ?,
                        updated_at = ?
                    WHERE id = ?
                """, (status, f"\n[{now()[:10]}] {notes}" if notes else "", now(), lead_id))
            logger.info(f"Lead {lead_id[:8]} → estado: {status}")
            return True
        except Exception as e:
            raise DatabaseError(f"Error al actualizar estado: {e}")

    def update_score(self, lead_id: str, score: float) -> bool:
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE leads SET lead_score=?, updated_at=? WHERE id=?",
                    (score, now(), lead_id)
                )
            return True
        except Exception as e:
            raise DatabaseError(f"Error al actualizar score: {e}")

    def update(self, lead_id: str, data: dict) -> bool:
        """Actualiza campos arbitrarios de un lead."""
        try:
            allowed = {
                "company_name","contact_name","category","city","province",
                "phone","whatsapp","instagram","website","email","notes",
                "lead_score","lead_status","tags","priority","business_type",
                "activity_level","estimated_volume","followup_date",
                "last_contact_at","last_reply_at","rejection_reason"
            }
            data = {k: v for k, v in data.items() if k in allowed}
            if not data:
                return False
            data["updated_at"] = now()
            fields = ", ".join(f"{k}=:{k}" for k in data)
            data["id"] = lead_id
            with get_connection() as conn:
                conn.execute(f"UPDATE leads SET {fields} WHERE id=:id", data)
            return True
        except Exception as e:
            raise DatabaseError(f"Error al actualizar lead: {e}")

    def delete(self, lead_id: str) -> bool:
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM lead_events WHERE lead_id = ?", (lead_id,))
                conn.execute("DELETE FROM conversations WHERE lead_id = ?", (lead_id,))
                conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            logger.info(f"Lead eliminado: {lead_id[:8]}")
            return True
        except Exception as e:
            raise DatabaseError(f"Error al eliminar lead: {e}")

    def search(self, query: str) -> list[dict]:
        """Búsqueda por nombre, ciudad, categoría o notas."""
        try:
            q = f"%{query}%"
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM leads
                    WHERE company_name LIKE ?
                       OR contact_name LIKE ?
                       OR city LIKE ?
                       OR category LIKE ?
                       OR notes LIKE ?
                    ORDER BY lead_score DESC LIMIT 50
                """, (q, q, q, q, q)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error en búsqueda: {e}")

    def get_stats(self) -> dict:
        """Métricas generales para el dashboard."""
        try:
            with get_connection() as conn:
                total     = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
                by_status = conn.execute("""
                    SELECT lead_status, COUNT(*) as count
                    FROM leads GROUP BY lead_status
                """).fetchall()
                hot       = conn.execute("""
                    SELECT COUNT(*) FROM leads
                    WHERE lead_status IN ('caliente','interesado','negociacion')
                """).fetchone()[0]
                followups = conn.execute("""
                    SELECT COUNT(*) FROM leads
                    WHERE followup_date <= ? AND lead_status NOT IN ('cerrado','descartado')
                """, (datetime.now().strftime("%Y-%m-%d"),)).fetchone()[0]

            return {
                "total":     total,
                "hot":       hot,
                "followups": followups,
                "by_status": {r["lead_status"]: r["count"] for r in by_status}
            }
        except Exception as e:
            raise DatabaseError(f"Error al obtener estadísticas: {e}")


# ══════════════════════════════════════════════════════
#  LEAD EVENTS
# ══════════════════════════════════════════════════════

class LeadEventRepository:

    def log(
        self,
        lead_id: str,
        event_type: str,
        description: str,
        created_by: str = "jarvis"
    ) -> str:
        """Registra un evento en el historial del lead."""
        event_id = str(uuid.uuid4())
        try:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO lead_events
                        (id, lead_id, event_type, event_description, created_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (event_id, lead_id, event_type, description, now(), created_by))
            logger.debug(f"Evento [{event_type}] para lead {lead_id[:8]}")
            return event_id
        except Exception as e:
            raise DatabaseError(f"Error al registrar evento: {e}")

    def get_for_lead(self, lead_id: str) -> list[dict]:
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM lead_events
                    WHERE lead_id = ?
                    ORDER BY created_at DESC
                """, (lead_id,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error al obtener eventos: {e}")


# ══════════════════════════════════════════════════════
#  CONVERSATIONS
# ══════════════════════════════════════════════════════

class ConversationRepository:

    def save(
        self,
        lead_id: str,
        sender: str,
        message: str,
        platform: str = "whatsapp",
        approved: bool = False
    ) -> str:
        conv_id = str(uuid.uuid4())
        try:
            with get_connection() as conn:
                conn.execute("""
                    INSERT INTO conversations
                        (id, lead_id, sender, message, platform, approved_by_user, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (conv_id, lead_id, sender, message, platform, int(approved), now()))
            return conv_id
        except Exception as e:
            raise DatabaseError(f"Error al guardar conversación: {e}")

    def get_for_lead(self, lead_id: str) -> list[dict]:
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM conversations
                    WHERE lead_id = ?
                    ORDER BY created_at ASC
                """, (lead_id,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"Error al obtener conversaciones: {e}")

    def approve(self, conv_id: str) -> bool:
        """Marca un mensaje como aprobado por el humano."""
        try:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE conversations SET approved_by_user=1 WHERE id=?",
                    (conv_id,)
                )
            return True
        except Exception as e:
            raise DatabaseError(f"Error al aprobar mensaje: {e}")