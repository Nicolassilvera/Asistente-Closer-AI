# src/api/main.py
import asyncio
import csv
import io
import json
import threading
import uuid as _uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, List
import os

from src.core.repositories import LeadRepository, LeadEventRepository, ConversationRepository
from src.core.logger import logger
from src.core.exceptions import DatabaseError

app = FastAPI(title="Jarvis CRM", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

leads_repo  = LeadRepository()
events_repo = LeadEventRepository()
convs_repo  = ConversationRepository()

# ── WebSocket ─────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: str, data: dict):
        message      = json.dumps({"event": event, "data": data, "ts": datetime.now().isoformat()})
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self.active:
                self.active.remove(ws)

manager = ConnectionManager()

async def emit(event: str, data: dict):
    await manager.broadcast(event, data)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ── HEALTH ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Jarvis CRM"}

# ── STATS ─────────────────────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    try:
        return leads_repo.get_stats()
    except DatabaseError as e:
        raise HTTPException(500, e.message)

# ── LEADS ─────────────────────────────────────────────────────────────────────
class LeadCreate(BaseModel):
    company_name:     str
    contact_name:     Optional[str] = None
    category:         Optional[str] = None
    city:             Optional[str] = None
    province:         Optional[str] = None
    phone:            Optional[str] = None
    whatsapp:         Optional[str] = None
    instagram:        Optional[str] = None
    website:          Optional[str] = None
    email:            Optional[str] = None
    source:           Optional[str] = "manual"
    notes:            Optional[str] = None
    lead_score:       Optional[float] = 0
    lead_status:      Optional[str] = "nuevo"
    priority:         Optional[str] = "media"
    business_type:    Optional[str] = None
    tags:             Optional[str] = None
    followup_date:    Optional[str] = None

class LeadUpdate(BaseModel):
    company_name:     Optional[str] = None
    contact_name:     Optional[str] = None
    category:         Optional[str] = None
    city:             Optional[str] = None
    province:         Optional[str] = None
    phone:            Optional[str] = None
    whatsapp:         Optional[str] = None
    email:            Optional[str] = None
    instagram:        Optional[str] = None
    website:          Optional[str] = None
    notes:            Optional[str] = None
    lead_score:       Optional[float] = None
    lead_status:      Optional[str] = None
    priority:         Optional[str] = None
    followup_date:    Optional[str] = None
    tags:             Optional[str] = None

class StatusUpdate(BaseModel):
    status: str
    notes:  Optional[str] = ""

@app.get("/api/leads")
def list_leads(
    status:   Optional[str] = None,
    priority: Optional[str] = None,
    search:   Optional[str] = None,
    limit:    int = 100
):
    try:
        if search:
            return leads_repo.search(search)
        return leads_repo.get_all(status=status, priority=priority, limit=limit)
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.get("/api/leads/hot")
def hot_leads():
    try:
        return leads_repo.get_hot()
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.get("/api/leads/followups")
def pending_followups():
    try:
        return leads_repo.get_pending_followup()
    except DatabaseError as e:
        raise HTTPException(500, e.message)

_find_jobs: dict = {}

class _FindRequest(BaseModel):
    categories:          List[str]
    cities:              List[str]
    max_per_combination: int = 10

@app.post("/api/leads/find")
def start_lead_find(data: _FindRequest):
    if not data.categories or not data.cities:
        raise HTTPException(400, "Se requiere al menos un rubro y una zona")

    job_id = str(_uuid.uuid4())
    _find_jobs[job_id] = {
        "id":     job_id,
        "status": "running",
        "done":   0,
        "total":  len(data.categories) * len(data.cities),
        "found":  0,
        "logs":   [],
    }

    def _run():
        from src.modules.lead_finder.finder import LeadFinder
        finder = LeadFinder()

        def _on_progress(done, total, cat, city, found, error=None):
            job = _find_jobs[job_id]
            job["done"] = done
            if error:
                job["logs"].append({"cat": cat, "city": city, "found": 0, "error": error})
            else:
                job["found"] += found
                job["logs"].append({"cat": cat, "city": city, "found": found})

        try:
            finder.find_batch(
                data.categories,
                data.cities,
                data.max_per_combination,
                _on_progress,
            )
        except Exception as e:
            _find_jobs[job_id]["error"] = str(e)
        finally:
            _find_jobs[job_id]["status"] = "done"
            try:
                finder.close()
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True, name=f"lead-finder-{job_id[:8]}").start()
    return {"id": job_id, "total": _find_jobs[job_id]["total"]}

@app.get("/api/leads/find/{job_id}")
def get_lead_find_status(job_id: str):
    job = _find_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    return job

@app.post("/api/leads/import")
def import_leads_csv(payload: dict):
    """Recibe { rows: [{col: val,...},...] } parseado en el frontend."""
    rows = payload.get("rows", [])
    if not rows:
        raise HTTPException(400, "Sin filas")

    # Mapeo de cabeceras ES → campos internos
    col_map = {
        "empresa":          "company_name",
        "contacto":         "contact_name",
        "categoría":        "category",
        "categoria":        "category",
        "ciudad":           "city",
        "provincia":        "province",
        "país":             "country",
        "pais":             "country",
        "teléfono":         "phone",
        "telefono":         "phone",
        "whatsapp":         "whatsapp",
        "instagram":        "instagram",
        "website":          "website",
        "email":            "email",
        "fuente":           "source",
        "estado":           "lead_status",
        "score":            "lead_score",
        "prioridad":        "priority",
        "notas":            "notes",
        # también acepta nombres en inglés directamente
        "company_name":     "company_name",
        "contact_name":     "contact_name",
        "phone":            "phone",
        "lead_status":      "lead_status",
    }

    created, skipped = 0, 0
    for row in rows:
        data = {}
        for k, v in row.items():
            mapped = col_map.get(k.strip().lower())
            if mapped and v:
                data[mapped] = v.strip()

        if not data.get("company_name"):
            skipped += 1
            continue
        try:
            leads_repo.create(data)
            created += 1
        except Exception:
            skipped += 1

    return {"created": created, "skipped": skipped}

@app.get("/api/leads/export")
def export_leads_csv(
    status:   Optional[str] = None,
    priority: Optional[str] = None,
    search:   Optional[str] = None,
):
    try:
        if search:
            rows = leads_repo.search(search)
        else:
            rows = leads_repo.get_all(status=status, priority=priority, limit=99999)
    except DatabaseError as e:
        raise HTTPException(500, e.message)

    fields = [
        "company_name","contact_name","category","city","province","country",
        "phone","whatsapp","instagram","website","email","source",
        "lead_status","lead_score","priority","notes",
        "last_contact_at","last_reply_at","followup_date","created_at",
    ]
    headers_es = [
        "Empresa","Contacto","Categoría","Ciudad","Provincia","País",
        "Teléfono","WhatsApp","Instagram","Website","Email","Fuente",
        "Estado","Score","Prioridad","Notas",
        "Último contacto","Última respuesta","Seguimiento","Creado",
    ]

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers_es)
    for lead in rows:
        w.writerow([lead.get(f) or '' for f in fields])

    return Response(
        content=buf.getvalue().encode('utf-8-sig'),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="leads.csv"'},
    )

@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str):
    try:
        lead = leads_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(404, "Lead no encontrado")
        return lead
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.post("/api/leads", status_code=201)
async def create_lead(data: LeadCreate):
    try:
        lead_id = leads_repo.create(data.model_dump())
        events_repo.log(lead_id, "lead_creado", "Creado manualmente", "humano")
        await manager.broadcast("lead_created", {"id": lead_id, **data.model_dump()})
        return {"id": lead_id, "message": "Lead creado correctamente"}
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.patch("/api/leads/{lead_id}")
async def update_lead(lead_id: str, data: LeadUpdate):
    try:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        leads_repo.update(lead_id, updates)
        events_repo.log(lead_id, "lead_actualizado", f"Campos: {list(updates.keys())}", "humano")
        await manager.broadcast("lead_updated", {"id": lead_id, **updates})
        return {"message": "Lead actualizado"}
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.delete("/api/leads/{lead_id}", status_code=204)
async def delete_lead(lead_id: str):
    try:
        leads_repo.delete(lead_id)
        await manager.broadcast("lead_deleted", {"id": lead_id})
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.patch("/api/leads/{lead_id}/status")
async def update_status(lead_id: str, body: StatusUpdate):
    try:
        leads_repo.update_status(lead_id, body.status, body.notes)
        events_repo.log(lead_id, "estado_cambiado", f"→ {body.status}: {body.notes}", "humano")
        await manager.broadcast("lead_status_changed", {"id": lead_id, "status": body.status})
        return {"message": f"Estado actualizado a {body.status}"}
    except DatabaseError as e:
        raise HTTPException(500, e.message)

# ── EVENTOS ───────────────────────────────────────────────────────────────────
@app.get("/api/leads/{lead_id}/events")
def get_events(lead_id: str):
    try:
        return events_repo.get_for_lead(lead_id)
    except DatabaseError as e:
        raise HTTPException(500, e.message)

# ── CONVERSACIONES ────────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    sender:   str
    message:  str
    platform: Optional[str] = "whatsapp"
    approved: Optional[bool] = False

@app.get("/api/leads/{lead_id}/conversations")
def get_conversations(lead_id: str):
    try:
        return convs_repo.get_for_lead(lead_id)
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.post("/api/leads/{lead_id}/conversations", status_code=201)
async def save_message(lead_id: str, data: MessageCreate):
    try:
        conv_id = convs_repo.save(
            lead_id, data.sender, data.message,
            data.platform, data.approved
        )
        await manager.broadcast("new_message", {
            "lead_id": lead_id,
            "conv_id": conv_id,
            "sender":  data.sender,
            "message": data.message
        })
        return {"id": conv_id}
    except DatabaseError as e:
        raise HTTPException(500, e.message)

@app.patch("/api/conversations/{conv_id}/approve")
async def approve_message(conv_id: str):
    try:
        convs_repo.approve(conv_id)
        await manager.broadcast("message_approved", {"conv_id": conv_id})
        return {"message": "Mensaje aprobado"}
    except DatabaseError as e:
        raise HTTPException(500, e.message)

# ── MONITOR WHATSAPP ──────────────────────────────────────────────────────────
def _monitor_db_get() -> bool:
    from src.core.database import get_connection
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key='monitor_enabled'"
        ).fetchone()
        return row is None or row[0] == '1'

def _monitor_db_set(enabled: bool):
    from src.core.database import get_connection
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('monitor_enabled',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ('1' if enabled else '0',)
        )

@app.get("/api/monitor/status")
def monitor_status():
    try:
        return {"enabled": _monitor_db_get()}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/monitor/toggle")
def monitor_toggle():
    try:
        current = _monitor_db_get()
        _monitor_db_set(not current)
        return {"enabled": not current}
    except Exception as e:
        raise HTTPException(500, str(e))

# ── SETTINGS ──────────────────────────────────────────────────────────────────
_SETTINGS_DEFAULTS = {
    "company_name":        "Balanzas Caballito",
    "monitor_interval":    "5",
    "auto_followup":       "0",
    "groq_api_key":        "",
    "gemini_api_key":      "",
    "elevenlabs_api_key":  "",
    "elevenlabs_voice_id": "",
    "edge_tts_voice":      "es-MX-JorgeNeural",
}

def _settings_get_all() -> dict:
    from src.core.database import get_connection
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    db  = {r[0]: r[1] for r in rows}
    out = dict(_SETTINGS_DEFAULTS)
    out.update({k: v for k, v in db.items() if k in _SETTINGS_DEFAULTS})
    return out

def _settings_set(key: str, value: str):
    from src.core.database import get_connection
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )

@app.get("/api/settings")
def get_settings():
    try:
        return _settings_get_all()
    except Exception as e:
        raise HTTPException(500, str(e))

_API_KEY_ENV = {
    "groq_api_key":        "GROQ_API_KEY",
    "gemini_api_key":      "GEMINI_API_KEY",
    "elevenlabs_api_key":  "ELEVENLABS_API_KEY",
    "elevenlabs_voice_id": "ELEVENLABS_VOICE_ID",
    "edge_tts_voice":      "EDGE_TTS_VOICE",
}

def _write_dotenv(env_key: str, value: str):
    """Persiste una clave en .env para que esté disponible en el próximo arranque."""
    env_path = os.path.join(os.getcwd(), ".env")
    lines, found = [], False
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{env_key}="):
                    lines.append(f"{env_key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{env_key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

@app.patch("/api/settings")
def patch_settings(data: dict = Body(...)):
    try:
        for k, v in data.items():
            if k not in _SETTINGS_DEFAULTS:
                continue
            _settings_set(k, str(v))
            # API keys: actualizar entorno en caliente + .env para el próximo reinicio
            env_key = _API_KEY_ENV.get(k)
            if env_key and v:
                os.environ[env_key] = str(v)
                try:
                    _write_dotenv(env_key, str(v))
                except Exception:
                    pass
        return _settings_get_all()
    except Exception as e:
        raise HTTPException(500, str(e))

# ── PROSPECCIÓN ───────────────────────────────────────────────────────────────
class ProspectRequest(BaseModel):
    lead_id:         str
    product_context: Optional[str] = "balanzas industriales y comerciales"

@app.post("/api/leads/{lead_id}/prospect")
async def prospect_lead(lead_id: str, data: ProspectRequest):
    try:
        lead = leads_repo.get_by_id(lead_id)
        if not lead:
            raise HTTPException(404, "Lead no encontrado")

        from src.modules.message_agent import MessageAgent
        from src.core.gpt_engine import GPTEngine

        agent   = MessageAgent(GPTEngine())
        message = agent.draft_outbound(
            company_name    = lead["company_name"],
            category        = lead.get("category", ""),
            city            = lead.get("city", ""),
            contact_name    = lead.get("contact_name", ""),
            product_context = data.product_context,
        )

        events_repo.log(
            lead_id,
            "mensaje_generado",
            "Mensaje de prospección generado por Jarvis",
            "jarvis",
        )

        return {"message": message, "lead": lead}

    except DatabaseError as e:
        raise HTTPException(500, e.message)

# ── COLA DE TAREAS WHATSAPP (CRM → Jarvis) ────────────────────────────────────
_wa_tasks: dict = {}

class _WaSendRequest(BaseModel):
    contact: str
    message: str
    lead_id: Optional[str] = None

@app.post("/api/whatsapp/send")
def wa_queue_send(data: _WaSendRequest):
    task_id = str(_uuid.uuid4())
    _wa_tasks[task_id] = {
        "id":      task_id,
        "contact": data.contact,
        "message": data.message,
        "lead_id": data.lead_id,
        "status":  "pending",
    }
    return {"id": task_id, "status": "queued"}

@app.get("/api/whatsapp/tasks/pending")
def wa_get_pending():
    pending = [t for t in _wa_tasks.values() if t["status"] == "pending"]
    for t in pending:
        t["status"] = "running"
    return pending

@app.post("/api/whatsapp/tasks/{task_id}/result")
async def wa_task_result(task_id: str, request: Request):
    data = await request.json()
    task = _wa_tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Tarea no encontrada")
    task["status"] = "done"
    task["result"] = data

    # Auto-avanzar estado del lead a "contactado" si el mensaje se envió OK
    if data.get("success") and task.get("lead_id"):
        try:
            lead = leads_repo.get_by_id(task["lead_id"])
            if lead and lead.get("lead_status") in ("nuevo", "analizado"):
                leads_repo.update_status(task["lead_id"], "contactado",
                                         "Mensaje enviado por Jarvis")
                events_repo.log(task["lead_id"], "estado_cambiado",
                                "→ contactado: mensaje enviado por Jarvis", "jarvis")
                await manager.broadcast("lead_status_changed",
                                        {"id": task["lead_id"], "status": "contactado"})
        except Exception:
            pass

    return {"ok": True}

@app.get("/api/whatsapp/tasks/{task_id}")
def wa_get_task(task_id: str):
    task = _wa_tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Tarea no encontrada")
    return task

# ── BROWSER / EXTENSION API ───────────────────────────────────────────────────
# Estado en memoria — la extensión lo actualiza cada 3 segundos
_browser_tabs: list  = []
_commands:     dict  = {}   # cmd_id → {id, type, params, status, result}

class _TabInventory(BaseModel):
    tabs: list[dict]

class _BrowserCommand(BaseModel):
    id:        Optional[str]  = None
    type:      str
    tab_id:    Optional[int]  = None
    window_id: Optional[int]  = None
    url:       Optional[str]  = None
    action:    Optional[str]  = None
    params:    Optional[dict] = None

@app.post("/api/browser/tabs")
def browser_update_tabs(payload: _TabInventory):
    global _browser_tabs
    _browser_tabs = payload.tabs
    return {"ok": True}

@app.get("/api/browser/tabs")
def browser_get_tabs():
    return {"tabs": _browser_tabs}

@app.post("/api/browser/command")
def browser_queue_command(cmd: _BrowserCommand):
    cmd_id = str(_uuid.uuid4())
    _commands[cmd_id] = {
        "id":        cmd_id,
        "type":      cmd.type,
        "tab_id":    cmd.tab_id,
        "window_id": cmd.window_id,
        "url":       cmd.url,
        "action":    cmd.action,
        "params":    cmd.params or {},
        "status":    "pending",
        "result":    None,
    }
    # Limpiar comandos viejos (> 200 entradas)
    if len(_commands) > 200:
        oldest = list(_commands.keys())[:50]
        for k in oldest:
            _commands.pop(k, None)
    return {"id": cmd_id}

@app.get("/api/browser/commands/pending")
def browser_get_pending():
    pending = [c for c in _commands.values() if c["status"] == "pending"]
    for c in pending:
        c["status"] = "running"
    return pending

@app.get("/api/browser/commands/{cmd_id}/result")
def browser_get_result(cmd_id: str):
    cmd = _commands.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "Comando no encontrado")
    return {"status": cmd["status"], "result": cmd.get("result")}

@app.post("/api/browser/commands/{cmd_id}/result")
async def browser_post_result(cmd_id: str, request: Request):
    data = await request.json()
    cmd  = _commands.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "Comando no encontrado")
    cmd["status"] = "done"
    cmd["result"] = data
    return {"ok": True}

# ── FRONTEND ──────────────────────────────────────────────────────────────────

# ── BROWSER CONTEXT ───────────────────────────────────────────────────────────
from pydantic import BaseModel as PydanticBase

class BrowserContext(PydanticBase):
    url:          str
    title:        str
    visible_text: Optional[str] = ""
    html:         Optional[str] = ""

_browser_context: dict = {}

@app.post("/api/browser/context")
async def receive_context(data: BrowserContext):
    global _browser_context
    _browser_context = data.model_dump()
    _browser_context["updated_at"] = datetime.now().isoformat()
    await manager.broadcast("browser_context", _browser_context)
    return {"status": "ok"}

@app.get("/api/browser/context")
def get_context():
    return _browser_context or {"url": "", "title": "", "visible_text": ""}

# ── CHAT IA ───────────────────────────────────────────────────────────────────
from fastapi.responses import StreamingResponse

_CHAT_SYSTEM = """Sos Jarvis, el asistente IA de Balanzas Caballito (empresa de balanzas industriales y comerciales).

Tu función en el chat:
- Analizás datos del CRM, leads y métricas comerciales
- Generás recomendaciones estratégicas y de marketing
- Identificás oportunidades y tendencias
- Ayudás con campañas, ideas de contenido y planificación

Personalidad: profesional, directo, humor seco 3/10. Sin emojis salvo que el usuario los use. Español rioplatense.
No inventes datos. Si no tenés información, decilo.

DISTINCIÓN IMPORTANTE: los "leads" son prospectos (todavía no compraron). Los "clientes" son quienes ya compraron. No los mezclés.

{crm_context}"""

_chat_gpt = None
def _get_chat_gpt():
    global _chat_gpt
    if _chat_gpt is None:
        try:
            from src.core.gpt_engine import GPTEngine
            _chat_gpt = GPTEngine()
        except Exception as e:
            logger.warning(f"Chat GPT no disponible: {e}")
    return _chat_gpt

def _crm_context_str() -> str:
    try:
        stats = leads_repo.get_stats()
        return (
            f"[Contexto CRM actual] Total leads: {stats.get('total',0)} | "
            f"Calientes: {stats.get('hot',0)} | "
            f"Seguimientos pendientes hoy: {stats.get('followups',0)}"
        )
    except Exception:
        return ""

def _db_chat(sql: str, params=(), fetch="all"):
    from src.core.database import get_connection
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        if fetch == "one": return cur.fetchone()
        if fetch == "none": return None
        return cur.fetchall()

class _ChatSessionIn(BaseModel):
    title: Optional[str] = "Nueva conversación"

class _ChatMsgIn(BaseModel):
    content: str

@app.get("/api/chat/sessions")
def chat_list_sessions():
    rows = _db_chat(
        "SELECT id, title, created_at FROM chat_sessions ORDER BY created_at DESC"
    )
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]

@app.post("/api/chat/sessions", status_code=201)
def chat_create_session(data: _ChatSessionIn):
    sid = str(_uuid.uuid4())
    now = datetime.now().isoformat()
    _db_chat(
        "INSERT INTO chat_sessions(id, title, created_at) VALUES(?,?,?)",
        (sid, data.title, now), fetch="none"
    )
    return {"id": sid, "title": data.title, "created_at": now}

@app.delete("/api/chat/sessions/{session_id}", status_code=204)
def chat_delete_session(session_id: str):
    _db_chat("DELETE FROM chat_messages WHERE session_id=?", (session_id,), fetch="none")
    _db_chat("DELETE FROM chat_sessions WHERE id=?", (session_id,), fetch="none")

@app.get("/api/chat/sessions/{session_id}/messages")
def chat_get_messages(session_id: str):
    rows = _db_chat(
        "SELECT id, role, content, created_at FROM chat_messages "
        "WHERE session_id=? ORDER BY created_at",
        (session_id,)
    )
    return [{"id": r[0], "role": r[1], "content": r[2], "created_at": r[3]} for r in rows]

@app.post("/api/chat/sessions/{session_id}/messages")
def chat_send_message(session_id: str, data: _ChatMsgIn):
    gpt = _get_chat_gpt()
    if not gpt:
        raise HTTPException(503, "Motor IA no disponible")

    # Guardar mensaje del usuario
    uid = str(_uuid.uuid4())
    now = datetime.now().isoformat()
    _db_chat(
        "INSERT INTO chat_messages(id, session_id, role, content, created_at) VALUES(?,?,?,?,?)",
        (uid, session_id, "user", data.content, now), fetch="none"
    )

    # Auto-título en el primer mensaje (primeras 50 chars)
    count = _db_chat(
        "SELECT COUNT(*) FROM chat_messages WHERE session_id=?", (session_id,), fetch="one"
    )
    if count and count[0] <= 1:
        title = data.content[:50].strip()
        _db_chat("UPDATE chat_sessions SET title=? WHERE id=?", (title, session_id), fetch="none")

    # Construir historial para el modelo
    history = _db_chat(
        "SELECT role, content FROM chat_messages WHERE session_id=? ORDER BY created_at",
        (session_id,)
    )
    system_prompt = _CHAT_SYSTEM.format(crm_context=_crm_context_str())
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": r[0], "content": r[1]} for r in history]

    parts = []

    def sse():
        try:
            for chunk in gpt.chat_stream(messages):
                parts.append(chunk)
                import json as _json
                yield f"data: {_json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'error': str(e)})}\n\n"
        finally:
            full = "".join(parts)
            if full:
                aid = str(_uuid.uuid4())
                _db_chat(
                    "INSERT INTO chat_messages(id, session_id, role, content, created_at) VALUES(?,?,?,?,?)",
                    (aid, session_id, "assistant", full, datetime.now().isoformat()), fetch="none"
                )
            import json as _json
            yield f"data: {_json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ── CALENDARIO ────────────────────────────────────────────────────────────────
class _CalEventIn(BaseModel):
    title:         str
    date:          str
    type:          Optional[str] = "tarea"
    notes:         Optional[str] = None
    product:       Optional[str] = None
    quantity:      Optional[int] = 1
    delivery_type: Optional[str] = None   # 'retiro' | 'envio'
    detail:        Optional[str] = None   # dirección (envio) o horario (retiro)
    contact:       Optional[str] = None   # nombre/número para WhatsApp

def _row_to_event(r):
    return {
        "id": r[0], "title": r[1], "date": r[2], "type": r[3], "notes": r[4],
        "product": r[5], "quantity": r[6], "delivery_type": r[7],
        "detail": r[8], "contact": r[9],
        "completed":      bool(r[10]) if len(r) > 10 else False,
        "wa_sent":        bool(r[11]) if len(r) > 11 else False,
        "price":          (r[12] or 0) if len(r) > 12 else 0,
        "profit":         (r[13] or 0) if len(r) > 13 else 0,
        "payment_method": (r[14] or "efectivo") if len(r) > 14 else "efectivo",
    }

_EVT_SELECT = (
    "SELECT id,title,date,type,notes,product,quantity,delivery_type,detail,contact,"
    "completed,wa_sent,price,profit,payment_method FROM calendar_events"
)

@app.get("/api/calendar/events")
def calendar_list(
    month:     Optional[str] = None,
    date:      Optional[str] = None,
    start:     Optional[str] = None,
    end:       Optional[str] = None,
    completed: Optional[int] = None,
):
    conds, params = [], []
    if date:
        conds.append("date=?"); params.append(date)
    elif month:
        conds.append("date LIKE ?"); params.append(f"{month}%")
    elif start and end:
        conds.append("date>=? AND date<=?"); params += [start, end]
    if completed is not None:
        conds.append("completed=?"); params.append(completed)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    order = "ORDER BY date, created_at"
    rows  = _db_chat(f"{_EVT_SELECT} {where} {order}", tuple(params))
    return [_row_to_event(r) for r in rows]

@app.post("/api/calendar/events", status_code=201)
def calendar_create(data: _CalEventIn):
    eid = str(_uuid.uuid4())
    now = datetime.now().isoformat()
    _db_chat(
        "INSERT INTO calendar_events(id,title,date,type,notes,product,quantity,"
        "delivery_type,detail,contact,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (eid, data.title, data.date, data.type, data.notes or "",
         data.product, data.quantity or 1, data.delivery_type,
         data.detail, data.contact, now),
        fetch="none"
    )
    return _row_to_event((eid, data.title, data.date, data.type, data.notes or "",
                          data.product, data.quantity or 1, data.delivery_type,
                          data.detail, data.contact))

class _CalEventPatch(BaseModel):
    completed:      Optional[bool]  = None
    wa_sent:        Optional[bool]  = None
    price:          Optional[float] = None
    profit:         Optional[float] = None
    payment_method: Optional[str]   = None

@app.patch("/api/calendar/events/{event_id}")
def calendar_patch(event_id: str, data: _CalEventPatch):
    updates = {}
    if data.completed      is not None: updates["completed"]      = 1 if data.completed else 0
    if data.wa_sent        is not None: updates["wa_sent"]        = 1 if data.wa_sent else 0
    if data.price          is not None: updates["price"]          = data.price
    if data.profit         is not None: updates["profit"]         = data.profit
    if data.payment_method is not None: updates["payment_method"] = data.payment_method
    for col, val in updates.items():
        _db_chat(f"UPDATE calendar_events SET {col}=? WHERE id=?", (val, event_id), fetch="none")
    return {"ok": True}

@app.delete("/api/calendar/events/{event_id}", status_code=204)
def calendar_delete(event_id: str):
    _db_chat("DELETE FROM calendar_events WHERE id=?", (event_id,), fetch="none")

# ── VENTAS ────────────────────────────────────────────────────────────────────
class _SaleIn(BaseModel):
    date:           str
    client:         Optional[str]   = None
    product:        Optional[str]   = None
    quantity:       Optional[int]   = 1
    price:          Optional[float] = 0
    profit:         Optional[float] = 0
    payment_method: Optional[str]   = "efectivo"
    notes:          Optional[str]   = None

class _SalePatch(BaseModel):
    client:         Optional[str]   = None
    product:        Optional[str]   = None
    quantity:       Optional[int]   = None
    price:          Optional[float] = None
    profit:         Optional[float] = None
    payment_method: Optional[str]   = None
    notes:          Optional[str]   = None

def _row_to_sale(r):
    return {
        "id": r[0], "date": r[1], "client": r[2], "product": r[3],
        "quantity": r[4], "price": r[5], "profit": r[6],
        "payment_method": r[7], "notes": r[8],
    }

@app.get("/api/sales")
def sales_list(date: Optional[str] = None, month: Optional[str] = None):
    sel = "SELECT id,date,client,product,quantity,price,profit,payment_method,notes FROM sales"
    if date:
        rows = _db_chat(f"{sel} WHERE date=? ORDER BY created_at", (date,))
    elif month:
        rows = _db_chat(f"{sel} WHERE date LIKE ? ORDER BY date,created_at", (f"{month}%",))
    else:
        rows = _db_chat(f"{sel} ORDER BY date DESC,created_at DESC")
    return [_row_to_sale(r) for r in rows]

@app.post("/api/sales", status_code=201)
def sale_create(data: _SaleIn):
    sid = str(_uuid.uuid4())
    now = datetime.now().isoformat()
    _db_chat(
        "INSERT INTO sales(id,date,client,product,quantity,price,profit,payment_method,notes,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (sid, data.date, data.client, data.product, data.quantity or 1,
         data.price or 0, data.profit or 0, data.payment_method or "efectivo",
         data.notes, now),
        fetch="none"
    )
    return _row_to_sale((sid, data.date, data.client, data.product,
                         data.quantity or 1, data.price or 0, data.profit or 0,
                         data.payment_method or "efectivo", data.notes))

@app.patch("/api/sales/{sale_id}")
def sale_patch(sale_id: str, data: _SalePatch):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    for col, val in fields.items():
        _db_chat(f"UPDATE sales SET {col}=? WHERE id=?", (val, sale_id), fetch="none")
    return {"ok": True}

@app.delete("/api/sales/{sale_id}", status_code=204)
def sale_delete(sale_id: str):
    _db_chat("DELETE FROM sales WHERE id=?", (sale_id,), fetch="none")

# ── POST-ITS ──────────────────────────────────────────────────────────────────
class _PostitIn(BaseModel):
    content:    str
    color:      Optional[str] = "orange"
    sort_order: Optional[int] = 0

class _PostitUpdate(BaseModel):
    content:    Optional[str] = None
    color:      Optional[str] = None

@app.get("/api/postits")
def postits_list():
    rows = _db_chat(
        "SELECT id, content, color, sort_order FROM postits ORDER BY sort_order, created_at DESC"
    )
    return [{"id":r[0],"content":r[1],"color":r[2],"sort_order":r[3]} for r in rows]

@app.post("/api/postits", status_code=201)
def postit_create(data: _PostitIn):
    pid = str(_uuid.uuid4())
    now = datetime.now().isoformat()
    _db_chat(
        "INSERT INTO postits(id, content, color, sort_order, created_at) VALUES(?,?,?,?,?)",
        (pid, data.content, data.color, data.sort_order, now), fetch="none"
    )
    return {"id": pid, "content": data.content, "color": data.color}

@app.patch("/api/postits/{postit_id}")
def postit_update(postit_id: str, data: _PostitUpdate):
    if data.content is not None:
        _db_chat("UPDATE postits SET content=? WHERE id=?", (data.content, postit_id), fetch="none")
    if data.color is not None:
        _db_chat("UPDATE postits SET color=? WHERE id=?", (data.color, postit_id), fetch="none")
    return {"ok": True}

@app.delete("/api/postits/{postit_id}", status_code=204)
def postit_delete(postit_id: str):
    _db_chat("DELETE FROM postits WHERE id=?", (postit_id,), fetch="none")

#--
import sys as _sys
if getattr(_sys, 'frozen', False):
    # Dentro del .exe — _MEIPASS es donde PyInstaller descomprime los datos
    _base_dir = _sys._MEIPASS
else:
    _base_dir = os.path.dirname(__file__)

FRONTEND_BUILD = os.path.join(_base_dir, "ui", "dist")
# Fallback: ruta relativa al directorio de trabajo (dev)
if not os.path.exists(FRONTEND_BUILD):
    FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "dist")

if os.path.exists(FRONTEND_BUILD):
    _assets = os.path.join(FRONTEND_BUILD, "assets")
    if os.path.exists(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(FRONTEND_BUILD, "index.html"))