# src/core/retry.py
import time
import functools
from src.core.logger import logger
from src.core.exceptions import JarvisError

def with_retry(
    max_attempts: int = 3,
    delay_seconds: float = 2.0,
    backoff: float = 2.0,        # cada reintento espera el doble
    recoverable_only: bool = True # solo reintenta errores recuperables
):
    """
    Decorador para reintentos automáticos con backoff exponencial.
    
    Uso:
        @with_retry(max_attempts=3, delay_seconds=2)
        def mi_funcion():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            wait = delay_seconds

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except JarvisError as e:
                    last_error = e
                    # Si el error no es recuperable, falla inmediatamente
                    if recoverable_only and not e.recoverable:
                        logger.error(f"Error no recuperable en {func.__name__}: {e.message}")
                        raise

                    if attempt < max_attempts:
                        logger.warning(
                            f"Intento {attempt}/{max_attempts} fallido en "
                            f"{func.__name__}: {e.message}. "
                            f"Reintentando en {wait:.0f}s..."
                        )
                        time.sleep(wait)
                        wait *= backoff
                    else:
                        logger.error(
                            f"Todos los intentos fallidos en {func.__name__}: {e.message}"
                        )

                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Intento {attempt}/{max_attempts} fallido en "
                            f"{func.__name__}: {e}. Reintentando en {wait:.0f}s..."
                        )
                        time.sleep(wait)
                        wait *= backoff
                    else:
                        logger.error(f"Error inesperado en {func.__name__}: {e}")

            raise last_error

        return wrapper
    return decorator