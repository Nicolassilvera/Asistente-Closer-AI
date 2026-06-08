# src/core/database.py
import sqlite3
import os
from src.core.config import config
from src.core.logger import logger
from src.core.exceptions import DatabaseError

def get_connection() -> sqlite3.Connection:
    try:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"No se pudo conectar a la base de datos: {e}")

def init_db():
    try:
        with get_connection() as conn:
            conn.executescript("""

                -- ── SESIONES Y TAREAS (ya existía) ──────────────────────
                CREATE TABLE IF NOT EXISTS sessions (
                    id            TEXT PRIMARY KEY,
                    raw_input     TEXT NOT NULL,
                    parsed_intent TEXT,
                    status        TEXT DEFAULT 'pending',
                    created_at    TEXT,
                    updated_at    TEXT
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id            TEXT PRIMARY KEY,
                    session_id    TEXT NOT NULL,
                    step_number   INTEGER NOT NULL,
                    description   TEXT NOT NULL,
                    action_type   TEXT NOT NULL,
                    action_params TEXT NOT NULL,
                    status        TEXT DEFAULT 'pending',
                    result        TEXT,
                    error         TEXT,
                    retries       INTEGER DEFAULT 0,
                    created_at    TEXT,
                    updated_at    TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                -- ── LEADS ────────────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS leads (
                    id                TEXT PRIMARY KEY,
                    company_name      TEXT NOT NULL,
                    contact_name      TEXT,
                    category          TEXT,
                    city              TEXT,
                    province          TEXT,
                    country           TEXT DEFAULT 'Argentina',
                    phone             TEXT,
                    whatsapp          TEXT,
                    instagram         TEXT,
                    website           TEXT,
                    email             TEXT,
                    source            TEXT,
                    notes             TEXT,
                    lead_score        REAL DEFAULT 0,
                    lead_status       TEXT DEFAULT 'nuevo',
                    last_contact_at   TEXT,
                    last_reply_at     TEXT,
                    assigned_to       TEXT DEFAULT 'jarvis',
                    tags              TEXT,
                    priority          TEXT DEFAULT 'media',
                    business_type     TEXT,
                    activity_level    TEXT,
                    estimated_volume  TEXT,
                    rejection_reason  TEXT,
                    followup_date     TEXT,
                    created_at        TEXT,
                    updated_at        TEXT
                );

                -- ── HISTORIAL DE EVENTOS POR LEAD ────────────────────────
                CREATE TABLE IF NOT EXISTS lead_events (
                    id                TEXT PRIMARY KEY,
                    lead_id           TEXT NOT NULL,
                    event_type        TEXT NOT NULL,
                    event_description TEXT,
                    created_at        TEXT,
                    created_by        TEXT DEFAULT 'jarvis',
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                );

                -- ── CONVERSACIONES ────────────────────────────────────────
                CREATE TABLE IF NOT EXISTS conversations (
                    id               TEXT PRIMARY KEY,
                    lead_id          TEXT NOT NULL,
                    sender           TEXT NOT NULL,
                    message          TEXT NOT NULL,
                    platform         TEXT DEFAULT 'whatsapp',
                    approved_by_user INTEGER DEFAULT 0,
                    created_at       TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                );

                -- ── ÍNDICES para búsquedas frecuentes ────────────────────
                CREATE INDEX IF NOT EXISTS idx_leads_status
                    ON leads(lead_status);
                CREATE INDEX IF NOT EXISTS idx_leads_priority
                    ON leads(priority);
                CREATE INDEX IF NOT EXISTS idx_leads_followup
                    ON leads(followup_date);
                CREATE INDEX IF NOT EXISTS idx_lead_events_lead
                    ON lead_events(lead_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_lead
                    ON conversations(lead_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_session
                    ON tasks(session_id);

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id         TEXT PRIMARY KEY,
                    title      TEXT DEFAULT 'Nueva conversación',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id         TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS calendar_events (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL,
                    date       TEXT NOT NULL,
                    type       TEXT DEFAULT 'tarea',
                    notes      TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS postits (
                    id         TEXT PRIMARY KEY,
                    content    TEXT NOT NULL,
                    color      TEXT DEFAULT 'orange',
                    sort_order INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sales (
                    id             TEXT PRIMARY KEY,
                    date           TEXT NOT NULL,
                    client         TEXT,
                    product        TEXT,
                    quantity       INTEGER DEFAULT 1,
                    price          REAL    DEFAULT 0,
                    profit         REAL    DEFAULT 0,
                    payment_method TEXT    DEFAULT 'efectivo',
                    notes          TEXT,
                    created_at     TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);

            """)
        # Migraciones — agregan columnas sin perder datos existentes
        migrations = [
            "ALTER TABLE calendar_events ADD COLUMN product TEXT",
            "ALTER TABLE calendar_events ADD COLUMN quantity INTEGER DEFAULT 1",
            "ALTER TABLE calendar_events ADD COLUMN delivery_type TEXT",
            "ALTER TABLE calendar_events ADD COLUMN detail TEXT",
            "ALTER TABLE calendar_events ADD COLUMN contact TEXT",
            "ALTER TABLE calendar_events ADD COLUMN completed INTEGER DEFAULT 0",
            "ALTER TABLE calendar_events ADD COLUMN wa_sent INTEGER DEFAULT 0",
            "ALTER TABLE calendar_events ADD COLUMN price REAL DEFAULT 0",
            "ALTER TABLE calendar_events ADD COLUMN profit REAL DEFAULT 0",
            "ALTER TABLE calendar_events ADD COLUMN payment_method TEXT DEFAULT 'efectivo'",
        ]
        for sql in migrations:
            try:
                with get_connection() as conn:
                    conn.execute(sql)
            except Exception:
                pass  # columna ya existe

        logger.info("Base de datos inicializada correctamente.")
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(f"Error al inicializar la base de datos: {e}")