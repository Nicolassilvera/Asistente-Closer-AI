# src/api/main.py
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
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

# ── FRONTEND ──────────────────────────────────────────────────────────────────
FRONTEND_BUILD = os.path.join(os.path.dirname(__file__), "../../ui/dist")

if os.path.exists(FRONTEND_BUILD):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_BUILD}/assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(f"{FRONTEND_BUILD}/index.html")