import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional
from src.core.database import get_connection

class CheckpointManager:

    # ── CP 1: guardar input raw ──────────────────────────────────────────
    def create_session(self, raw_input: str) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?)",
                (session_id, raw_input, None, "pending", now, now)
            )
        print(f"[CP1] ✓ Sesión creada")
        return session_id

    # ── CP 2: guardar plan de tareas ─────────────────────────────────────
    def save_tasks(self, session_id: str, parsed_intent: str, tasks: list[dict]):
        now = datetime.now().isoformat()
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET parsed_intent=?, updated_at=? WHERE id=?",
                (parsed_intent, now, session_id)
            )
            for i, task in enumerate(tasks):
                conn.execute(
                    "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), session_id, i + 1,
                        task["description"],
                        task["action_type"],
                        json.dumps(task.get("params", {})),
                        "pending", None, None, 0, now, now
                    )
                )
        print(f"[CP2] ✓ Plan guardado: {len(tasks)} tareas")

    # ── CP 3: confirmar sesión ───────────────────────────────────────────
    def confirm_session(self, session_id: str):
        self._update_session(session_id, status="running")
        print(f"[CP3] ✓ Sesión confirmada")

    # ── CP 4: actualizar tareas durante ejecución ────────────────────────
    def start_task(self, task_id: str):
        self._update_task(task_id, status="running")

    def complete_task(self, task_id: str, result: str = "ok"):
        self._update_task(task_id, status="done", result=result)
        print(f"[CP4] ✓ Tarea completada")

    def fail_task(self, task_id: str, error: str):
        with get_connection() as conn:
            conn.execute(
                """UPDATE tasks SET status='failed', error=?,
                   retries=retries+1, updated_at=? WHERE id=?""",
                (error, datetime.now().isoformat(), task_id)
            )
        print(f"[CP4] ✗ Tarea fallida: {error}")

    def complete_session(self, session_id: str):
        self._update_session(session_id, status="done")
        print(f"[CP4] ✓ Sesión completada")

    # ── Consultas ────────────────────────────────────────────────────────
    def get_next_task(self, session_id: str) -> Optional[dict]:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM tasks
                   WHERE session_id=?
                   AND status IN ('pending','failed')
                   AND retries < 3
                   ORDER BY step_number LIMIT 1""",
                (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_pending_sessions(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM sessions
                   WHERE status IN ('pending','running')
                   ORDER BY created_at DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def get_session_tasks(self, session_id: str) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE session_id=? ORDER BY step_number",
                (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Helpers ──────────────────────────────────────────────────────────
    def _update_task(self, task_id: str, **kwargs):
        kwargs["updated_at"] = datetime.now().isoformat()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE tasks SET {fields} WHERE id=?",
                (*kwargs.values(), task_id)
            )

    def _update_session(self, session_id: str, **kwargs):
        kwargs["updated_at"] = datetime.now().isoformat()
        fields = ", ".join(f"{k}=?" for k in kwargs)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE sessions SET {fields} WHERE id=?",
                (*kwargs.values(), session_id)
            )