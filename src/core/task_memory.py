# src/core/task_memory.py
import json
import os

MEMORY_FILE = "data/last_task.json"

def save_last_task(intent: str, tasks: list, platform: str = ""):
    """Guarda la última tarea para poder retomar."""
    os.makedirs("data", exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "intent":   intent,
            "tasks":    tasks,
            "platform": platform
        }, f, ensure_ascii=False, indent=2)

def get_last_task() -> dict | None:
    """Recupera la última tarea guardada."""
    if not os.path.exists(MEMORY_FILE):
        return None
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def clear_last_task():
    """Limpia la memoria después de ejecutar."""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
        