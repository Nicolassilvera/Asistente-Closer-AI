# src/core/gpt_engine.py
import json
import re
from src.core.config import config
from src.core.logger import logger
from src.core.retry import with_retry
from src.core.exceptions import GPTError, GPTQuotaError, GPTConnectionError, GPTParseError
from src.core.personality import PERSONALITY_PROMPT

SYSTEM_PROMPT = f"""
{PERSONALITY_PROMPT}

TAREA PRINCIPAL:
Analizá instrucciones del usuario y devolvé un plan de acción estructurado.

REGLA CRÍTICA — DATOS FALTANTES:
Si la instrucción no tiene todos los datos necesarios para ejecutarse,
NO generes tareas incompletas. En cambio, devolvé:
{{
  "intent": "descripción de lo que quiere hacer",
  "needs_clarification": true,
  "missing": ["campo1", "campo2"],
  "question": "pregunta concisa al estilo Jarvis para obtener lo que falta"
}}

Ejemplos de cuándo pedir clarificación:
- "mandále un mensaje a Martin" → falta plataforma (whatsapp/messenger/mail)
- "contactá al cliente" → falta nombre del contacto
- "avisale que llego tarde" → falta a quién y por qué plataforma

Si tiene TODOS los datos, devolvé el plan normal:
{{
  "intent": "descripción corta",
  "tasks": [
    {{
      "description": "qué hace en lenguaje humano",
      "action_type": "browser|app|file|whatsapp|facebook|messenger|system|message|crm|lead_finder",
      "params": {{}}
    }}
  ]
}}

Datos necesarios por tipo de acción:
- whatsapp: contacto + mensaje
- mail: destinatario + asunto + cuerpo
- llamada: contacto + teléfono
- instagram: usuario + mensaje
- crm: qué buscar o actualizar
- messenger: enviar mensaje por Messenger chat normal
- messenger con "marketplace": true: mensajes de Marketplace de Facebook
  Ejemplos:
  "respondé a Francisco de Marketplace" → action: send_message, marketplace: true, contact: Francisco
  "abrí los mensajes de Marketplace"   → action: get_pending, marketplace: true
  "mandá mensaje a Juan por Messenger" → action: send_message, marketplace: false
- lead_finder: buscar prospectos/compradores/clientes potenciales en Google Maps.
  Params: {{"category": "rubro exacto de empresa", "city": "ciudad o zona", "max_results": 15}}
  REGLA: siempre generá UNA sola tarea lead_finder, no múltiples. Elegí la categoría más útil.
  Para balanzas/básculas industriales los compradores típicos son:
  frigoríficos, supermercados, plantas industriales, logística y distribución, depósitos
  Ejemplos:
  "buscame compradores de balanzas en CABA"          → lead_finder, category: "frigoríficos", city: "CABA"
  "encontrá clientes para básculas en Rosario"       → lead_finder, category: "supermercados mayoristas", city: "Rosario"
  "buscame posibles compradores en CABA"             → lead_finder, category: "plantas industriales", city: "CABA"
  "prospectos para balanzas industriales en Córdoba" → lead_finder, category: "distribuidoras", city: "Córdoba"

REGLAS FIJAS — nunca cambiar:
- messenger → SIEMPRE action_type: "messenger", NUNCA "app"
- marketplace → SIEMPRE action_type: "messenger" con "marketplace": true
- whatsapp → SIEMPRE action_type: "whatsapp", NUNCA "app" ni "browser"
- Si el usuario dice "Messenger", "mensajes de Marketplace", "Marketplace de Facebook"
  → messenger con marketplace: true
- spotify → SIEMPRE action_type: "spotify", NUNCA "browser", NUNCA "app"
  La app de Spotify se abre automáticamente con el URI scheme.
  Ejemplos:
  "poné Beat It de Michael Jackson" → action_type: spotify, params: {{song: "Beat It", artist: "Michael Jackson"}}
  "poné música tranquila para trabajar" → action_type: spotify, params: {{query: "música tranquila para trabajar"}}
  "shuffle de rock" → action_type: spotify, params: {{query: "rock"}}
  "poné algo random" → action_type: spotify, params: {{query: "mix del día"}}
- "mandá el mensaje de recién" / "intentá de nuevo" / "el mensaje anterior" / "Quiero reenviar lo que acabo de decir" / "Reenviá el último mensaje" / "Repetí la última tarea"
   → action_type: "retomar_tarea"

Respondé SOLO con el JSON, sin texto adicional, sin markdown.
"""

class GPTEngine:
    """Motor de IA con soporte para Groq, Gemini y OpenAI. Prioridad: Groq → Gemini → OpenAI"""

    def __init__(self):
        self.provider = self._init_provider()
        logger.info(f"Motor IA iniciado con: {self.provider}")

    def _init_provider(self) -> str:
        if config.GROQ_API_KEY:
            from groq import Groq
            self._groq  = Groq(api_key=config.GROQ_API_KEY)
            self._model = config.GROQ_MODEL
            return "groq"

        if config.GEMINI_API_KEY:
            from google import genai
            from google.genai import types as gtypes
            self._genai_types = gtypes
            self._gclient     = genai.Client(api_key=config.GEMINI_API_KEY)
            self._model       = config.GEMINI_MODEL
            return "gemini"

        if config.OPENAI_API_KEY:
            from openai import OpenAI
            self._openai = OpenAI(api_key=config.OPENAI_API_KEY)
            self._model  = "gpt-4o-mini"
            return "openai"

        raise GPTError("No hay API key configurada.", recoverable=False)

    @with_retry(max_attempts=3, delay_seconds=5)
    def parse_instruction(self, user_input: str) -> dict:
        logger.debug(f"Parseando: {user_input[:60]}...")
        handlers = {
            "groq":   self._parse_groq,
            "gemini": self._parse_gemini,
            "openai": self._parse_openai,
        }
        return handlers[self.provider](user_input)

    @with_retry(max_attempts=2, delay_seconds=3)
    def ask(self, prompt: str, context: str = "") -> str:
        full = f"{context}\n\n{prompt}" if context else prompt
        handlers = {
            "groq":   self._ask_groq,
            "gemini": self._ask_gemini,
            "openai": self._ask_openai,
        }
        return handlers[self.provider](full)

    # ── Groq ──────────────────────────────────────────────────────────────

    def _parse_groq(self, user_input: str) -> dict:
        try:
            response = self._groq.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_input}
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content.strip()
            logger.debug(f"Groq raw: {raw[:100]}...")
            return self._parse_json(raw)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err or "rate" in err:
                raise GPTQuotaError(provider="Groq")
            if "connection" in err or "network" in err:
                raise GPTConnectionError()
            raise GPTError(f"Error de Groq: {e}")

    def _ask_groq(self, prompt: str) -> str:
        try:
            response = self._groq.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": (
                        "Sos Jarvis, mayordomo digital y asistente ejecutivo. "
                        "Profesional, humor seco 3/10, sin emojis. "
                        "Respondé en español, breve y con tu personalidad característica."
                    )},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise GPTError(f"Error de Groq: {e}")

    # ── Gemini ────────────────────────────────────────────────────────────

    def _parse_gemini(self, user_input: str) -> dict:
        try:
            from google.genai import types
            response = self._gclient.models.generate_content(
                model=self._model,
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=1000,
                )
            )
            raw = response.text.strip()
            return self._parse_json(raw)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err:
                raise GPTQuotaError(provider="Gemini")
            raise GPTError(f"Error de Gemini: {e}")

    def _ask_gemini(self, prompt: str) -> str:
        try:
            from google.genai import types
            response = self._gclient.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=300,
                )
            )
            return response.text.strip()
        except Exception as e:
            raise GPTError(f"Error de Gemini: {e}")

    # ── OpenAI ────────────────────────────────────────────────────────────

    def _parse_openai(self, user_input: str) -> dict:
        try:
            response = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_input}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            return self._parse_json(response.choices[0].message.content.strip())
        except Exception as e:
            if "insufficient_quota" in str(e):
                raise GPTQuotaError(provider="OpenAI")
            raise GPTError(f"Error de OpenAI: {e}")

    def _ask_openai(self, prompt: str) -> str:
        try:
            response = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sos Jarvis, mayordomo digital. Sin emojis, humor seco."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.4,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise GPTError(f"Error de OpenAI: {e}")

    # ── Chat conversacional (streaming) ──────────────────────────────────

    def chat_stream(self, messages: list):
        """
        Genera respuesta conversacional en modo streaming.
        `messages` es una lista de dicts {role, content} (historial completo).
        Yield: strings de texto (chunks).
        """
        handlers = {
            "groq":   self._chat_stream_groq,
            "gemini": self._chat_stream_gemini,
            "openai": self._chat_stream_openai,
        }
        yield from handlers[self.provider](messages)

    def _chat_stream_groq(self, messages: list):
        try:
            stream = self._groq.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as e:
            raise GPTError(f"Error de Groq (chat): {e}")

    def _chat_stream_gemini(self, messages: list):
        # Gemini: convertir historial al formato Contents + simular streaming
        try:
            from google.genai import types
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msgs  = [m for m in messages if m["role"] != "system"]
            contents   = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in user_msgs)
            response = self._gclient.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_msg or None,
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )
            yield response.text.strip()
        except Exception as e:
            raise GPTError(f"Error de Gemini (chat): {e}")

    def _chat_stream_openai(self, messages: list):
        try:
            stream = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as e:
            raise GPTError(f"Error de OpenAI (chat): {e}")

    # ── Parser JSON ───────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise GPTParseError(raw)