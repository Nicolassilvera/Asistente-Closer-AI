# src/modules/whatsapp_monitor.py
import threading
import time
from src.core.logger import logger
from src.core.repositories import LeadRepository, LeadEventRepository, ConversationRepository

class WhatsAppMonitor:
    """
    Monitorea WhatsApp Web cada X minutos.
    Detecta respuestas de leads y actualiza el CRM automáticamente.
    """

    def __init__(self, browser, gpt_engine, interval_minutes: int = 5):
        self.browser   = browser
        self.gpt       = gpt_engine
        self.interval  = interval_minutes * 60
        self._running  = False
        self._thread   = None
        self.leads_repo  = LeadRepository()
        self.events_repo = LeadEventRepository()
        self.convs_repo  = ConversationRepository()

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"WhatsApp Monitor iniciado — revisando cada {self.interval//60} minutos")

    def stop(self):
        self._running = False
        logger.info("WhatsApp Monitor detenido.")

    def _is_enabled(self) -> bool:
        try:
            from src.core.database import get_connection
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key='monitor_enabled'"
                ).fetchone()
                return row is None or row[0] == '1'
        except Exception:
            return True

    def _is_auto_followup_enabled(self) -> bool:
        try:
            from src.core.database import get_connection
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT value FROM settings WHERE key='auto_followup'"
                ).fetchone()
                return row is not None and row[0] == '1'
        except Exception:
            return False

    def _loop(self):
        last_followup_day = None
        while self._running:
            try:
                if self._is_enabled():
                    self._check_responses()
                else:
                    logger.debug("WhatsApp Monitor pausado por el usuario.")

                from datetime import date
                today = date.today().isoformat()
                if last_followup_day != today and self._is_auto_followup_enabled():
                    self._auto_followup_check()
                    last_followup_day = today
            except Exception as e:
                logger.warning(f"WhatsApp Monitor error: {e}")
            time.sleep(self.interval)

    def _check_responses(self):
        """Revisa chats no leídos y actualiza leads en el CRM."""
        from src.modules.whatsapp import WhatsAppModule
        from src.modules.message_agent import MessageAgent

        logger.info("WhatsApp Monitor: revisando chats...")

        try:
            # Verificar que WhatsApp esté abierto
            current_url = ""
            try:
                current_url = self.browser._page.url
            except Exception:
                return

            if "web.whatsapp.com" not in current_url:
                logger.debug("WhatsApp Monitor: WhatsApp no está abierto, saltando.")
                return

            wa = WhatsAppModule(self.browser)
            unread = wa.get_unread_chats()

            if not unread:
                logger.debug("WhatsApp Monitor: sin chats nuevos.")
                return

            agent = MessageAgent(self.gpt)
            logger.info(f"WhatsApp Monitor: {len(unread)} chats sin leer")

            for chat in unread:
                try:
                    self._process_chat(chat, agent)
                except Exception as e:
                    logger.warning(f"Error procesando chat {chat.get('name')}: {e}")

        except Exception as e:
            logger.warning(f"WhatsApp Monitor check error: {e}")

    def _process_chat(self, chat: dict, agent):
        """Procesa un chat y actualiza el lead en el CRM."""
        contact_name = chat.get("name", "")
        preview      = chat.get("preview", "")

        if not contact_name or not preview:
            return

        # Buscar el lead en el CRM por nombre
        leads = self.leads_repo.search(contact_name)
        if not leads:
            logger.debug(f"WhatsApp Monitor: {contact_name} no está en el CRM")
            return

        lead = leads[0]

        # Analizar la respuesta con IA
        analysis = agent.analyze_response(
            message=preview,
            product=lead.get("category", "balanzas")
        )

        logger.info(
            f"WhatsApp Monitor: {contact_name} → "
            f"intent: {analysis['intent']} | "
            f"status: {analysis['lead_status']} | "
            f"ready_to_call: {analysis['ready_to_call']}"
        )

        # Actualizar estado en el CRM
        old_status = lead.get("lead_status", "")
        new_status = analysis["lead_status"]

        if old_status != new_status:
            self.leads_repo.update_status(lead["id"], new_status)
            self.events_repo.log(
                lead["id"],
                "whatsapp_respuesta",
                f"Cliente respondió por WhatsApp: {analysis['summary']} "
                f"→ estado: {new_status}",
                "jarvis_monitor"
            )

        # Guardar conversación
        self.convs_repo.save(
            lead_id=lead["id"],
            sender="contacto",
            message=preview,
            platform="whatsapp",
            approved=False
        )

        # Si está listo para llamar — actualizar followup para hoy
        if analysis["ready_to_call"]:
            from datetime import date
            self.leads_repo.update(lead["id"], {
                "followup_date": date.today().isoformat(),
                "last_reply_at": __import__('datetime').datetime.now().isoformat()
            })
            self.events_repo.log(
                lead["id"],
                "listo_para_llamar",
                f"Lead listo para llamar — {analysis['summary']}. "
                f"Acción sugerida: {analysis['suggested_action']}",
                "jarvis_monitor"
            )
            logger.info(f"📞 Lead {contact_name} listo para llamar — agregado a seguimientos")

        # Emitir evento al CRM en tiempo real via API
        try:
            import requests
            requests.patch(
                f"http://localhost:8000/api/leads/{lead['id']}/status",
                json={"status": new_status, "notes": analysis["summary"]},
                timeout=2
            )
        except Exception:
            pass

    def _auto_followup_check(self):
        """Envía WA automático a todos los leads con followup_date = hoy."""
        from datetime import date
        import requests

        today = date.today().isoformat()
        logger.info(f"Auto-followup: revisando leads para {today}...")

        try:
            leads = self.leads_repo.get_all(limit=99999)
        except Exception as e:
            logger.warning(f"Auto-followup: error al obtener leads: {e}")
            return

        pending = [
            l for l in leads
            if l.get("followup_date") == today
            and l.get("lead_status") not in ("cerrado", "descartado")
        ]

        if not pending:
            logger.debug("Auto-followup: sin leads para hoy.")
            return

        logger.info(f"Auto-followup: {len(pending)} lead(s) a contactar.")

        for lead in pending:
            contact = (lead.get("whatsapp") or lead.get("phone") or
                       lead.get("contact_name") or lead.get("company_name", ""))
            name    = lead.get("contact_name") or lead.get("company_name") or "ahí"
            msg = (
                f"Hola {name}, te escribo para hacer un seguimiento y ver cómo estás. "
                f"Quedamos en retomar hoy — ¿tuviste oportunidad de pensar en lo que conversamos? "
                f"Quedamos a tu disposición. Saludos."
            )
            try:
                requests.post(
                    "http://localhost:8000/api/whatsapp/send",
                    json={"contact": contact, "message": msg, "lead_id": lead["id"]},
                    timeout=5
                )
                self.events_repo.log(
                    lead["id"],
                    "followup_automatico",
                    f"Seguimiento automático enviado por WhatsApp a {contact}.",
                    "jarvis_auto"
                )
                logger.info(f"Auto-followup: mensaje enviado a {name} ({contact})")
            except Exception as e:
                logger.warning(f"Auto-followup: error enviando a {name}: {e}")