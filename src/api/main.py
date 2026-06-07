# src/api/main.py
import asyncio
import json
import uuid as _uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
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
    phone:            Optional[str] = None
    whatsapp:         Optional[str] = None
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

#--
FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "../../ui/dist")

if os.path.exists(FRONTEND_BUILD):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_BUILD}/assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(f"{FRONTEND_BUILD}/index.html")