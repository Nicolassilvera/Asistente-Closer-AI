# main.py
import sys
import os
import time
import queue
import threading
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from src.core.config import config
from src.core.database import init_db
from src.core.logger import logger
from src.core.exceptions import ConfigError, DatabaseError, JarvisError
from src.core.repositories import LeadRepository, LeadEventRepository
from src.core.personality import say

console = Console()

# Cola compartida entre el wake word y el loop principal
instruction_queue = queue.Queue()

def smoke_test():
    repo       = LeadRepository()
    event_repo = LeadEventRepository()
    lead_id    = repo.create({
        "company_name": "Test",
        "source":       "test",
        "lead_score":   5,
        "lead_status":  "nuevo",
        "priority":     "media",
    })
    event_repo.log(lead_id, "test", "Smoke test", "sistema")
    stats = repo.get_stats()

    table = Table(title="Base de datos — verificación", show_lines=True)
    table.add_column("Métrica", style="dim")
    table.add_column("Valor",   style="bold green")
    table.add_row("Total leads",      str(stats["total"]))
    table.add_row("Leads calientes",  str(stats["hot"]))
    table.add_row("Seguimientos hoy", str(stats["followups"]))
    console.print(table)

    from src.core.database import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM lead_events WHERE lead_id=?", (lead_id,))
        conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    console.print("[green]✓ Base de datos OK[/green]\n")

def run_api_server():
    import subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    )
    return proc

def open_crm():
    import subprocess
    time.sleep(2.5)
    try:
        subprocess.Popen(["cmd", "/c", "start", "msedge",
                          "--new-window", "http://localhost:8000"])
    except Exception:
        import webbrowser
        webbrowser.open("http://localhost:8000")

# Flag global — bloquea el wake word durante confirmaciones
_confirming = False

def main():
    console.print(f"\n[bold purple]🤖 {config.APP_NAME}[/bold purple] [dim]iniciando...[/dim]")

    try:
        config.validate()
    except ConfigError as e:
        console.print(f"\n[bold red]Error de configuración:[/bold red] {e.message}\n")
        sys.exit(1)

    try:
        init_db()
        smoke_test()
    except DatabaseError as e:
        console.print(f"\n[bold red]Error de base de datos:[/bold red] {e.message}\n")
        sys.exit(1)

    # Limpiar sesiones pendientes
    try:
        from src.core.database import get_connection
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status='done' WHERE status IN ('pending','running')"
            )
    except Exception:
        pass

    console.print("[yellow]Iniciando servidor CRM...[/yellow]")
    api_proc = run_api_server()
    threading.Thread(target=open_crm, daemon=True).start()

    from src.core.orchestrator import Orchestrator
    try:
        orchestrator = Orchestrator()
    except JarvisError as e:
        console.print(f"\n[bold red]Error al iniciar:[/bold red] {e.message}\n")
        api_proc.terminate()
        sys.exit(1)

    # ── Motor de voz ──────────────────────────────────────────────────────
    tts        = None
    stt        = None
    voice_ctrl = None

    try:
        from src.core.voice import TTSEngine, STTEngine
        tts = TTSEngine()
        stt = STTEngine()

        # VoiceController modificado — usa la cola en vez de llamar directo
        from src.core.voice import WakeWordDetector

        class QueueVoiceController:
            def __init__(self, tts, stt):
                self.tts      = tts
                self.stt      = stt
                self.detector = WakeWordDetector(on_detected=self._on_wake, wake_word="eren")
                self._active  = True
                self._lock    = threading.Lock()
                self._busy    = False

            def start(self):
                self.detector.start()
                logger.info("VoiceController con cola iniciado.")

            def stop(self):
                self._active = False
                self.detector.stop()

            def listen_now(self):
                threading.Thread(target=self._on_wake, daemon=True).start()

            def _on_wake(self):
                global _confirming
                if _confirming:
                    return  # no interrumpir durante confirmaciones
                
                with self._lock:
                    if self._busy:
                        return
                    self._busy = True

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

                    # Limpiar palabras de activación
                    activation_words = [
                        "jarvis", "jarvi", "jarbes", "harvey", "harvis",
                        "asistente", "oye jarvis", "hola jarvis"
                    ]
                    text_lower = text.lower().strip()
                    for word in sorted(activation_words, key=len, reverse=True):
                        if text_lower.startswith(word):
                            text = text[len(word):].strip(" ,.")
                            break

                    if not text:
                        msg = "¿En qué puedo ayudarle?"
                        console.print(f"[purple]Jarvis:[/purple] {msg}")
                        self.tts.speak(msg, blocking=True)
                        text = self.stt.listen(timeout=8, phrase_limit=30)
                        if not text:
                            self.tts.speak(say("not_understood"))
                            return
                        console.print(f"[dim]Entendí:[/dim] {text}")

                    # Poner en cola — el thread principal lo procesa
                    instruction_queue.put(("voice", text))

                except Exception as e:
                    logger.error(f"Error en ciclo de voz: {e}")
                finally:
                    self._busy = False
                    if self._active:
                        console.print("[dim]Jarvis escuchando...[/dim]")

        voice_ctrl = QueueVoiceController(tts, stt)
        voice_ctrl.start()
        console.print("[green]✓ Módulo de voz activo[/green]")

    except Exception as e:
        logger.warning(f"Módulo de voz no disponible: {e}")
        console.print(f"[yellow]⚠ Voz no disponible: {e}[/yellow]")

    # Saludo
    greeting = say("greeting")
    console.print(f"\n[purple]Jarvis:[/purple] {greeting}")
    if tts:
        tts.speak(greeting)

    voice_hint = "decí [purple]'Jarvis'[/purple] o " if voice_ctrl else ""
    console.print(
        f"\n[bold]CRM:[/bold] [link=http://localhost:8000]http://localhost:8000[/link] | "
        f"[bold]Instrucciones:[/bold] {voice_hint}escribí aquí\n"
    )
    logger.info("Jarvis iniciado correctamente.")

    # ── Loop principal — único lugar donde se ejecuta Playwright ──────────
    while True:
        try:
            # Verificar si hay instrucciones de voz en la cola
            try:
                source, user_input = instruction_queue.get_nowait()
                via_voice = (source == "voice")
            except queue.Empty:
                # No hay instrucciones de voz — leer del teclado con timeout
                # Usamos un input con timeout para no bloquear la cola
                import select
                user_input = None
                via_voice  = False

                # En Windows no hay select para stdin, usamos prompt normal
                try:
                    console.print("[purple]Vos:[/purple] ", end="")
                    # Timeout de 0.5s para no bloquear — revisamos la cola frecuentemente
                    import msvcrt
                    chars = []
                    start = time.time()
                    while True:
                        # Revisar cola de voz mientras esperamos input
                        try:
                            source, voice_text = instruction_queue.get_nowait()
                            # Llegó una instrucción de voz — procesarla primero
                            user_input = voice_text
                            via_voice  = True
                            console.print()  # nueva línea
                            break
                        except queue.Empty:
                            pass

                        if msvcrt.kbhit():
                            ch = msvcrt.getwche()
                            if ch in ('\r', '\n'):
                                console.print()
                                user_input = ''.join(chars).strip()
                                break
                            elif ch == '\x08':  # backspace
                                if chars:
                                    chars.pop()
                                    console.print('\b \b', end='')
                            elif ch == '\x03':  # Ctrl+C
                                raise KeyboardInterrupt
                            else:
                                chars.append(ch)

                        time.sleep(0.05)

                except Exception:
                    # Fallback: input normal si msvcrt falla
                    user_input = Prompt.ask("[purple]Vos[/purple]").strip()
                    via_voice  = False

            if not user_input:
                continue

            if user_input.lower() in ("salir", "exit", "quit"):
                msg = "Hasta luego, señor."
                console.print(f"[purple]Jarvis:[/purple] {msg}")
                if tts: tts.speak(msg)
                break

            if user_input.lower() in ("escuchar", "voz", "mic", "jarvis"):
                if voice_ctrl:
                    threading.Thread(target=voice_ctrl.listen_now, daemon=True).start()
                continue

            orchestrator.run(user_input, via_voice=via_voice, tts=tts)

        except KeyboardInterrupt:
            msg = "Interrumpido. Hasta luego."
            console.print(f"\n[dim]{msg}[/dim]")
            if tts: tts.speak(msg)
            break
        except Exception as e:
            logger.exception(f"Error inesperado: {e}")
            console.print(f"[red]Error inesperado: {e}[/red]")

    if voice_ctrl:
        voice_ctrl.stop()
    try:
        api_proc.terminate()
    except Exception:
        pass

if __name__ == "__main__":
    main()