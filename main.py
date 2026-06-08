# main.py
import sys
import os

# Cuando corre como .exe: trabajar desde el directorio del ejecutable
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

import time
import queue
import threading
from rich.console import Console
from rich.prompt import Prompt
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

def _ensure_playwright():
    """Instala Chromium automáticamente si no está disponible en esta PC."""
    import subprocess
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = p.chromium.executable_path
        if os.path.exists(exe):
            return  # ya instalado, nada que hacer
    except Exception:
        pass

    console.print("\n[yellow]► Primera vez en esta PC — instalando navegador (~150MB)...[/yellow]")
    console.print("[dim]  Esto tarda unos minutos solo la primera vez, después arranca normal.[/dim]\n")

    try:
        # Usa el driver de playwright directamente (funciona en .exe y en dev)
        from playwright._impl._driver import compute_driver_executable
        driver, cli = compute_driver_executable()
        result = subprocess.run([str(driver), str(cli), "install", "chromium"], timeout=600)
        if result.returncode == 0:
            console.print("[green]✓ Navegador instalado correctamente[/green]\n")
        else:
            console.print("[red]✗ No se pudo instalar automáticamente.[/red]")
            console.print("[dim]  Corré manualmente: python -m playwright install chromium[/dim]\n")
    except Exception as e:
        console.print(f"[red]✗ Error instalando navegador: {e}[/red]")
        console.print("[dim]  Corré manualmente: python -m playwright install chromium[/dim]\n")

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

    if getattr(sys, 'frozen', False):
        # Modo .exe — uvicorn corre en un thread (no como subprocess)
        import uvicorn
        import threading
        from src.api.main import app as _app
        def _run():
            uvicorn.run(_app, host="0.0.0.0", port=8000, log_level="warning")
        t = threading.Thread(target=_run, daemon=True, name="uvicorn")
        t.start()
        time.sleep(2)  # darle tiempo a levantar
        return t

    # Modo desarrollo — matar proceso previo en 8000 y arrancar subprocess
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid and pid != os.getpid():
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                   capture_output=True, timeout=5)
                    logger.info(f"Proceso previo en puerto 8000 terminado (PID {pid})")
                    time.sleep(1)
                    break
    except Exception:
        pass

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    )
    return proc

def open_crm():
    import subprocess
    time.sleep(2.5)
    frozen = getattr(sys, 'frozen', False)
    try:
        subprocess.Popen(["cmd", "/c", "start", "msedge",
                          "--new-window", "http://localhost:8000"])
        if not frozen:
            time.sleep(0.8)
            subprocess.Popen(["cmd", "/c", "start", "msedge",
                              "--new-tab", "http://localhost:5173"])
    except Exception:
        import webbrowser
        webbrowser.open("http://localhost:8000")
        if not frozen:
            webbrowser.open_new_tab("http://localhost:5173")

# Flag global — bloquea el wake word durante confirmaciones
_confirming = False

def main():
    console.print(f"\n[bold purple]🤖 {config.APP_NAME}[/bold purple] [dim]iniciando...[/dim]")

    _ensure_playwright()

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

    # ── Monitor de WhatsApp ───────────────────────────────────────────────
    from src.modules.whatsapp_monitor import WhatsAppMonitor
    wa_monitor = WhatsAppMonitor(
        browser          = orchestrator.executor.browser,
        gpt_engine       = orchestrator.gpt,
        interval_minutes = 5,
    )

    def _start_monitor():
        time.sleep(30)  # esperar que el usuario abra WhatsApp
        try:
            wa_monitor.start()
        except Exception as e:
            logger.warning(f"WhatsApp Monitor no pudo iniciar: {e}")

    threading.Thread(target=_start_monitor, daemon=True).start()

    # ── Tareas WhatsApp desde el CRM ─────────────────────────────────────
    # Un único hilo worker persistente — Playwright no es thread-safe;
    # todas las operaciones deben ocurrir en el mismo hilo que lo creó.
    _crm_task_queue = queue.Queue()

    def _crm_worker():
        """Hilo único que procesa todas las tareas CRM con Playwright."""
        import requests as _req
        while True:
            task = _crm_task_queue.get()   # bloquea hasta que llegue una tarea
            console.print(
                f"\n[purple]CRM → Jarvis:[/purple] "
                f"enviando WhatsApp a [bold]{task['contact']}[/bold]..."
            )
            try:
                orchestrator.executor.execute("whatsapp", {
                    "action":   "send_message",
                    "contacto": task["contact"],
                    "mensaje":  task["message"],
                })
                _req.post(
                    f"http://localhost:8000/api/whatsapp/tasks/{task['id']}/result",
                    json={"success": True}, timeout=2,
                )
                console.print(
                    f"[green]✓ Mensaje enviado a {task['contact']} por WhatsApp[/green]\n"
                )
            except Exception as e:
                _req.post(
                    f"http://localhost:8000/api/whatsapp/tasks/{task['id']}/result",
                    json={"success": False, "error": str(e)}, timeout=2,
                )
                console.print(f"[red]✗ Error enviando a {task['contact']}: {e}[/red]\n")

    threading.Thread(target=_crm_worker, daemon=True, name="crm-wa-worker").start()

    def _poll_crm_wa_tasks():
        """Polling liviano — solo encola tareas, no usa Playwright."""
        import requests as _req
        while True:
            time.sleep(3)
            try:
                r = _req.get("http://localhost:8000/api/whatsapp/tasks/pending", timeout=1)
                if r.ok:
                    for task in r.json():
                        _crm_task_queue.put(task)
            except Exception:
                pass

    threading.Thread(target=_poll_crm_wa_tasks, daemon=True, name="crm-wa-poll").start()

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
                user_input = None
                via_voice  = False

                try:
                    console.print("[purple]Vos:[/purple] ", end="")
                    import msvcrt
                    chars = []
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
    if hasattr(api_proc, 'terminate'):
        try:
            api_proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()