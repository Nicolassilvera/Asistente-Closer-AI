# src/core/logger.py
import logging
import os
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console

console = Console()

def setup_logger(name: str = "jarvis") -> logging.Logger:
    os.makedirs("logs", exist_ok=True)

    log_file = f"logs/jarvis_{datetime.now().strftime('%Y%m%d')}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evitar handlers duplicados si se llama más de una vez
    if logger.handlers:
        return logger

    # Handler para archivo — guarda TODO (debug, info, errores)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Handler para consola — solo INFO y arriba, con Rich (colores)
    console_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True
    )
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Logger global — todos los módulos lo importan de acá
logger = setup_logger()