# src/api/server.py
import uvicorn
import threading
import subprocess
import time
import webbrowser
from src.core.logger import logger

CRM_URL  = "http://localhost:8000"
API_PORT = 8000

def open_edge(url: str, delay: float = 2.5):
    def _open():
        time.sleep(delay)
        try:
            subprocess.Popen(["cmd", "/c", "start", "msedge", "--new-window", url])
            logger.info(f"Edge abierto en {url}")
        except Exception:
            webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()

def start_server(open_browser: bool = True):
    if open_browser:
        open_edge(CRM_URL)
    logger.info(f"Iniciando servidor en {CRM_URL}")
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=API_PORT,
        log_level="warning",
        reload=False
    )

def start_server_background():
    thread = threading.Thread(
        target=start_server,
        kwargs={"open_browser": True},
        daemon=True
    )
    thread.start()
    logger.info("Servidor API iniciado en background.")
    return thread