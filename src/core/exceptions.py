# src/core/exceptions.py

class JarvisError(Exception):
    """Base de todos los errores de Jarvis."""
    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable  # si True, se puede reintentar

class GPTError(JarvisError):
    """Error al llamar a la API de OpenAI."""
    pass

# src/core/exceptions.py
class GPTQuotaError(GPTError):
    """Sin crédito o cuota de API."""
    def __init__(self, provider: str = "Gemini"):
        super().__init__(
            f"Sin cuota disponible en {provider}. Verificá tu cuenta en aistudio.google.com",
            recoverable=False
        )

class GPTParseError(GPTError):
    """GPT no devolvió JSON válido."""
    def __init__(self, raw: str):
        super().__init__(f"GPT devolvió respuesta inválida: {raw[:80]}...")

class GPTConnectionError(GPTError):
    """Sin conexión a OpenAI."""
    def __init__(self):
        super().__init__("Sin conexión a internet o OpenAI no disponible.")

class DatabaseError(JarvisError):
    """Error de base de datos."""
    pass

class TaskExecutionError(JarvisError):
    """Error al ejecutar una tarea automatizada."""
    def __init__(self, task_desc: str, reason: str):
        super().__init__(f"No pude ejecutar '{task_desc}': {reason}")
        self.task_desc = task_desc
        self.reason = reason

class BrowserError(TaskExecutionError):
    """Error del navegador (Playwright)."""
    pass

class ConfigError(JarvisError):
    """Error de configuración del sistema."""
    def __init__(self, field: str):
        super().__init__(
            f"Falta configurar '{field}' en el archivo .env",
            recoverable=False
        )