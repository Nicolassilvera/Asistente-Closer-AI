# src/core/orchestrator.py
import json
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from src.core.checkpoints import CheckpointManager
from src.core.gpt_engine import GPTEngine
from src.core.logger import logger
from src.core.exceptions import JarvisError, GPTQuotaError
from src.core.personality import say
from src.core.task_executor import TaskExecutor
import requests
ctx = requests.get("http://localhost:8000/api/browser/context").json()

console = Console()

CONFIRMACIONES = [
    "sí", "si", "dale", "confirmá", "confirma", "ok", "perfecto",
    "adelante", "hacelo", "mandalo", "mándaselo", "envialo",
    "sigue", "seguí", "procede", "procedé", "claro", "obvio",
    "por supuesto", "va", "vamos", "listo", "afirmativo", "correcto",
    "eso", "así", "exacto", "bueno", "bien", "por favor", "pásaselo"
]

class Orchestrator:
    def __init__(self):
        self.cp       = CheckpointManager()
        self.gpt      = GPTEngine()
        self.executor = TaskExecutor()

    def run(self, user_input: str, via_voice: bool = False, tts=None):
        logger.info(f"Nueva instrucción: {user_input[:60]}...")

        # STT local para confirmaciones por voz
        _stt = None
        if via_voice:
            try:
                from src.core.voice import STTEngine
                _stt = STTEngine()
            except Exception as e:
                logger.warning(f"STT no disponible: {e}")

        # Detectar si quiere retomar la última tarea
        retomar_keywords = [
            "respaldo","mensaje de recién", "anterior", "intentá de nuevo",
            "reintentá", "la última tarea", "lo de recién",
            "mandá lo anterior", "el de antes", "lo anterior"
        ]
        if any(k in user_input.lower() for k in retomar_keywords):
            from src.core.task_memory import get_last_task
            last = get_last_task()
            if last:
                console.print(f"\n[yellow]Jarvis:[/yellow] Retomando: {last['intent']}\n")
                if tts: tts.speak(f"Retomando: {last['intent']}", blocking=False)
                session_id = self.cp.create_session(user_input)
                self.cp.save_tasks(session_id, last["intent"], last["tasks"])
                self._show_plan({"intent": last["intent"], "tasks": last["tasks"]})
                confirmed = self._confirmar(via_voice, _stt, tts)
                if confirmed:
                    self.cp.confirm_session(session_id)
                    self._execute(session_id, tts=tts)
                return

        # ── CP 1 ──────────────────────────────────────────────────────────
        try:
            session_id = self.cp.create_session(user_input)
        except JarvisError as e:
            msg = f"Error al guardar sesión: {e.message}"
            console.print(f"[red]{msg}[/red]")
            if tts: tts.speak(msg)
            return

        # ── CP 2: parsear ─────────────────────────────────────────────────
        thinking = say("thinking")
        console.print(f"[dim]{thinking}[/dim]")
        if tts: tts.speak(thinking, blocking=False)

        try:
            plan = self.gpt.parse_instruction(user_input)
        except GPTQuotaError as e:
            console.print(f"\n[bold red]⚠ {e.message}[/bold red]\n")
            if tts: tts.speak("Sin cuota de IA disponible.")
            return
        except JarvisError as e:
            console.print(f"[red]{e.message}[/red]")
            if tts: tts.speak(e.message)
            return

        # Clarificación
        if plan.get("needs_clarification"):
            return self._handle_clarification(
                plan, user_input, session_id,
                via_voice=via_voice, _stt=_stt, tts=tts
            )

        # ── CP 2: guardar ─────────────────────────────────────────────────
        self.cp.save_tasks(session_id, plan["intent"], plan["tasks"])

        # Guardar en memoria para retomar
        try:
            from src.core.task_memory import save_last_task
            save_last_task(plan["intent"], plan["tasks"])
        except Exception:
            pass

        self._show_plan(plan)

        # ── CP 3: confirmar ───────────────────────────────────────────────
        if via_voice and _stt:
            tasks_summary = ", ".join([t["description"] for t in plan["tasks"]])
            question = f"Voy a: {tasks_summary}. ¿Confirmo, señor?"
            console.print(f"[purple]Jarvis:[/purple] {question}")
            if tts: tts.speak(question)
            confirmed = self._confirmar_voz(_stt)
        else:
            try:
                confirmed = Confirm.ask("\n¿Ejecuto este plan?")
            except KeyboardInterrupt:
                msg = say("cancel")
                console.print(f"[dim]{msg}[/dim]")
                if tts: tts.speak(msg)
                return

        if not confirmed:
            msg = say("cancel")
            console.print(f"[dim]{msg}[/dim]")
            if tts: tts.speak(msg)
            return

        self.cp.confirm_session(session_id)

        # ── CP 4: ejecutar ────────────────────────────────────────────────
        self._execute(session_id, tts=tts)

    def _handle_clarification(
        self, plan: dict, original_input: str,
        session_id: str, via_voice: bool = False,
        _stt=None, tts=None, attempt: int = 1
    ):
        question = plan.get("question", "¿Puede darme más detalles, señor?")
        console.print(f"\n[purple]Jarvis:[/purple] {question}")
        if tts: tts.speak(question)

        if via_voice and _stt:
            console.print("[dim]Escuchando...[/dim]")
            answer = _stt.listen(timeout=8)
        else:
            try:
                answer = Prompt.ask("[dim]Vos[/dim]").strip()
            except KeyboardInterrupt:
                console.print(f"[dim]{say('cancel')}[/dim]")
                return

        if not answer:
            msg = "Sin respuesta. Cancelando."
            console.print(f"[dim]{msg}[/dim]")
            if tts: tts.speak(msg)
            return

        enriched = f"{original_input} — {answer}"
        logger.info(f"Instrucción enriquecida: {enriched}")

        try:
            from src.core.database import get_connection
            from datetime import datetime
            with get_connection() as conn:
                conn.execute(
                    "UPDATE sessions SET raw_input=?, updated_at=? WHERE id=?",
                    (enriched, datetime.now().isoformat(), session_id)
                )
        except Exception:
            pass

        console.print(f"[dim]{say('thinking')}[/dim]")
        try:
            plan = self.gpt.parse_instruction(enriched)
        except JarvisError as e:
            console.print(f"[red]{e.message}[/red]")
            if tts: tts.speak(e.message)
            return

        if plan.get("needs_clarification") and attempt < 2:
            return self._handle_clarification(
                plan, enriched, session_id,
                via_voice=via_voice, _stt=_stt, tts=tts, attempt=attempt + 1
            )

        if plan.get("needs_clarification"):
            msg = "No logro entender lo que necesita. Intente de nuevo."
            console.print(f"[purple]Jarvis:[/purple] {msg}")
            if tts: tts.speak(msg)
            return

        self.cp.save_tasks(session_id, plan["intent"], plan["tasks"])

        try:
            from src.core.task_memory import save_last_task
            save_last_task(plan["intent"], plan["tasks"])
        except Exception:
            pass

        self._show_plan(plan)

        if via_voice and _stt:
            tasks_summary = ", ".join([t["description"] for t in plan["tasks"]])
            question = f"Voy a: {tasks_summary}. ¿Confirmo?"
            console.print(f"[purple]Jarvis:[/purple] {question}")
            if tts: tts.speak(question)
            confirmed = self._confirmar_voz(_stt)
        else:
            try:
                confirmed = Confirm.ask("\n¿Ejecuto este plan?")
            except KeyboardInterrupt:
                console.print(f"[dim]{say('cancel')}[/dim]")
                return

        if not confirmed:
            msg = say("cancel")
            console.print(f"[dim]{msg}[/dim]")
            if tts: tts.speak(msg)
            return

        self.cp.confirm_session(session_id)
        self._execute(session_id, tts=tts)

    def _confirmar(self, via_voice: bool, _stt, tts) -> bool:
        """Pide confirmación por voz o texto."""
        if via_voice and _stt:
            return self._confirmar_voz(_stt)
        else:
            try:
                return Confirm.ask("¿Ejecuto este plan?")
            except KeyboardInterrupt:
                return False

    def _confirmar_voz(self, _stt) -> bool:
        """Escucha la confirmación por voz."""
        try:
            console.print("[dim]Escuchando confirmación...[/dim]")
            answer = _stt.listen(timeout=6)
            if not answer:
                return False
            return any(w in answer.lower() for w in CONFIRMACIONES)
        except Exception as e:
            logger.warning(f"Error en confirmación por voz: {e}")
            return False

    def _execute(self, session_id: str, tts=None):
        msg = say("confirm")
        console.print(f"\n[green]{msg}[/green]\n")
        if tts: tts.speak(msg, blocking=False)

        completed = 0
        failed    = 0

        while True:
            try:
                task = self.cp.get_next_task(session_id)
            except JarvisError as e:
                logger.error(f"Error obteniendo tarea: {e.message}")
                break

            if not task:
                break

            console.print(f"[bold]Paso {task['step_number']}:[/bold] {task['description']}")
            self.cp.start_task(task["id"])

            try:
                result = self._execute_task(task)
                self.cp.complete_task(task["id"], result)
                done_msg = say("task_done")
                console.print(f"  [green]✓ {done_msg}[/green]")
                completed += 1

            except JarvisError as e:
                self.cp.fail_task(task["id"], e.message)
                logger.warning(f"Tarea fallida (intento {task['retries']+1}): {e.message}")

                if task["retries"] + 1 >= 3:
                    fail_msg = say("task_failed")
                    console.print(f"  [red]✗ {fail_msg} — {e.message}[/red]")
                    if tts: tts.speak(f"No pude completar: {task['description']}")
                    failed += 1
                else:
                    console.print(f"  [yellow]⚠ {e.message}. Reintentando...[/yellow]")

            except Exception as e:
                self.cp.fail_task(task["id"], str(e))
                logger.exception(f"Error inesperado: {e}")
                console.print(f"  [red]✗ Error: {e}[/red]")
                failed += 1

        self.cp.complete_session(session_id)

        # Limpiar memoria si todo salió bien
        if failed == 0:
            try:
                from src.core.task_memory import clear_last_task
                clear_last_task()
            except Exception:
                pass

        total   = completed + failed
        summary = f"{completed} de {total} tareas completadas."
        console.print(f"\n[bold]Sesión:[/bold] [green]{summary}[/green]\n")
        if tts: tts.speak(summary)
        logger.info(f"Sesión {session_id[:8]}: {completed} ok, {failed} fallidas")

    def _execute_task(self, task: dict) -> str:
        params = json.loads(task["action_params"])
        return self.executor.execute(task["action_type"], params)

    def _show_plan(self, plan: dict):
        table = Table(title=f"Plan: {plan['intent']}", show_lines=True)
        table.add_column("#",          style="dim",  width=4)
        table.add_column("Acción",     style="bold")
        table.add_column("Tipo",       style="cyan", width=12)
        table.add_column("Parámetros", style="dim")

        for i, task in enumerate(plan["tasks"], 1):
            table.add_row(
                str(i),
                task["description"],
                task["action_type"],
                json.dumps(task.get("params", {}), ensure_ascii=False)
            )
        console.print(table)

    def resume_pending(self):
        try:
            pending = self.cp.get_pending_sessions()
        except JarvisError:
            return

        if not pending:
            return

        console.print(f"\n[yellow]⚠ Hay {len(pending)} sesión(es) sin terminar.[/yellow]")
        for s in pending:
            console.print(
                f"  [dim]{s['created_at'][:16]}[/dim] — "
                f"{s['parsed_intent'] or s['raw_input'][:60]}"
            )

        try:
            if Confirm.ask("¿Retomamos la última?"):
                self._execute(pending[0]["id"])
        except KeyboardInterrupt:
            pass