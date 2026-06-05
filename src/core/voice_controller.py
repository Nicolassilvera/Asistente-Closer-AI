# src/core/voice_controller.py
import threading
import time
from rich.console import Console
from src.core.voice import TTSEngine, STTEngine, WakeWordDetector
from src.core.personality import say
from src.core.logger import logger

console = Console()

# Palabras que activan a Jarvis además del wake word
ACTIVATION_WORDS = [
    "subaru", "jarvis", "jarvi", "jarbes", "harvey", "harvis", "yarbis", "sharvis" # variantes fonéticas
    "asistente", "che jarvis", "oye jarvis", "hola jarvis",
    "necesito ayuda", "jarvis estás",
]

class VoiceController:
    def __init__(self, orchestrator, tts: TTSEngine, stt: STTEngine):
        self.orchestrator = orchestrator
        self.tts          = tts
        self.stt          = stt
        self.detector     = WakeWordDetector(on_detected=self._on_wake)
        self._listening   = False
        self._active      = True
        self._lock        = threading.Lock()

    def start(self):
        self.detector.start()
        logger.info("VoiceController iniciado.")

        def _auto_activate():
            time.sleep(2)
            if self._active:
                console.print("[dim]Jarvis escuchando — decí 'Jarvis' para activar[/dim]")

        threading.Thread(target=_auto_activate, daemon=True).start()

    def stop(self):
        self._active = False
        self.detector.stop()

    def listen_now(self):
        """Activación manual."""
        self._on_wake()

    def _on_wake(self):
        with self._lock:
            if self._listening:
                return
            self._listening = True

        try:
            response = say("wake_detected")
            console.print(f"\n[purple]Jarvis:[/purple] {response}")
            self.tts.speak(response, blocking=True)

            console.print("[dim]Escuchando...[/dim]")
            text = self.stt.listen(timeout=8, phrase_limit=30)

            if not text:
                msg = say("not_understood")
                console.print(f"[purple]Jarvis:[/purple] {msg}")
                self.tts.speak(msg)
                return

            console.print(f"[dim]Entendí:[/dim] {text}")

            # Verificar si lo que dijo es solo una palabra de activación
            # sin instrucción real — en ese caso escuchar de nuevo
            text_lower = text.lower().strip()
            solo_activacion = any(
                text_lower == word or text_lower == f"{word}." or text_lower == f"{word}!"
                for word in ACTIVATION_WORDS
            )

            if solo_activacion:
                # Solo dijo "Jarvis" — pedir la instrucción
                msg = "¿En qué puedo ayudarle, señor?"
                console.print(f"[purple]Jarvis:[/purple] {msg}")
                self.tts.speak(msg, blocking=True)
                console.print("[dim]Escuchando...[/dim]")
                text = self.stt.listen(timeout=8, phrase_limit=30)
                if not text:
                    self.tts.speak(say("not_understood"))
                    return
                console.print(f"[dim]Entendí:[/dim] {text}")

            # Limpiar palabras de activación del inicio de la instrucción
            for word in sorted(ACTIVATION_WORDS, key=len, reverse=True):
                if text_lower.startswith(word):
                    text = text[len(word):].strip(" ,.")
                    break

            if not text:
                return

            try:
                self.orchestrator.run(text, via_voice=True, tts=self.tts)
            except Exception as e:
                logger.error(f"Error procesando voz: {e}")
                msg = say("task_failed")
                console.print(f"[purple]Jarvis:[/purple] {msg}")
                self.tts.speak(msg)

        except Exception as e:
            logger.error(f"Error en ciclo de voz: {e}")
        finally:
            self._listening = False
            if self._active:
                console.print("[dim]Jarvis escuchando...[/dim]")