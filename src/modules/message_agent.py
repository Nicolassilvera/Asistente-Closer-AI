# src/modules/message_agent.py
import json
import re
from src.core.logger import logger
from src.core.exceptions import JarvisError

# Plantillas base por rubro — Jarvis las personaliza con IA
RUBRO_CONTEXT = {
    "gastronomia":    "negocios gastronómicos como restaurantes, bares, rotiserías y deliveries",
    "carniceria":     "carnicerías y negocios de venta de carne",
    "supermercado":   "supermercados, almacenes y negocios de alimentación",
    "ferreteria":     "ferreterías y negocios de construcción",
    "logistica":      "empresas de logística, transporte y depósitos",
    "industria":      "empresas industriales y manufactureras",
    "farmacia":       "farmacias y negocios de salud",
    "verduleria":     "verdulerías, fruterías y negocios de alimentos frescos",
    "panaderia":      "panaderías y negocios de panificación",
    "default":        "negocios y comercios"
}

class MessageAgent:
    """
    Redacta mensajes de prospección saliente personalizados por rubro.
    Analiza respuestas de clientes y detecta intención de compra.
    """

    def __init__(self, gpt_engine):
        self.gpt = gpt_engine

    def draft_outbound(
        self,
        company_name: str,
        category: str = "",
        city: str = "",
        contact_name: str = "",
        product_context: str = "balanzas industriales y comerciales"
    ) -> str:
        """
        Redacta mensaje inicial de prospección saliente.
        Personalizado por rubro y ciudad.
        """
        rubro_desc = self._get_rubro_desc(category)

        prompt = f"""
Sos un vendedor profesional de una empresa que vende {product_context}.
Redactá un mensaje inicial de WhatsApp para un prospecto.

DATOS DEL PROSPECTO:
- Empresa: {company_name}
- Rubro: {category or 'comercio general'}
- Ciudad: {city or 'Argentina'}
- Contacto: {contact_name or 'el responsable'}
- Contexto del rubro: {rubro_desc}

REGLAS:
- Mensaje corto (máximo 4 líneas)
- Presentate brevemente como vendedor
- Mencioná el producto en contexto con su rubro específico
- Generá curiosidad sin revelar precio todavía
- Invitá a conversar
- Tono: directo, profesional, sin ser invasivo
- Sin emojis excesivos (máximo 1-2)
- No digas que sos una IA

Respondé SOLO con el mensaje de WhatsApp, sin explicaciones.
"""
        try:
            return self.gpt.ask(prompt).strip()
        except JarvisError as e:
            logger.error(f"MessageAgent outbound error: {e}")
            raise

    def analyze_response(self, message: str, product: str = "") -> dict:
        """
        Analiza la respuesta de un cliente y detecta intención.
        Devuelve estado sugerido y si hay que generar llamada.
        """
        prompt = f"""
Analizá este mensaje de un cliente potencial que recibió una oferta de {product or 'balanzas'}.

MENSAJE DEL CLIENTE: "{message}"

Devolvé SOLO este JSON:
{{
  "intent": "interesado|consulta_precio|quiere_comprar|no_interesado|pide_mas_info|otro",
  "lead_status": "interesado|caliente|contactado|descartado",
  "ready_to_call": true/false,
  "urgency": "alta|media|baja",
  "summary": "resumen en una línea de qué quiere el cliente",
  "suggested_action": "llamar|enviar_info|enviar_precio|esperar|descartar"
}}

Criterios:
- ready_to_call: true si preguntó precio, disponibilidad o mostró interés claro
- lead_status "caliente": tono muy positivo o pregunta de compra directa
- lead_status "interesado": mostró interés pero sin urgencia
- lead_status "descartado": respuesta negativa clara
"""
        try:
            raw = self.gpt.ask(prompt)
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw).strip()
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"analyze_response parse error: {e}")
            return {
                "intent": "otro",
                "lead_status": "contactado",
                "ready_to_call": False,
                "urgency": "media",
                "summary": message[:60],
                "suggested_action": "esperar"
            }

    def draft_shipping_bot(self, contact_name: str, product: str = "la balanza") -> str:
        """Primer mensaje del bot de datos de envío."""
        return (
            f"¡Perfecto {contact_name}! Para coordinar el envío de {product} "
            f"necesito algunos datos. ¿Me podés decir tu nombre completo y "
            f"a qué dirección lo enviamos? (calle, número, localidad y provincia)"
        )

    def _get_rubro_desc(self, category: str) -> str:
        if not category:
            return RUBRO_CONTEXT["default"]
        cat_lower = category.lower()
        for key, desc in RUBRO_CONTEXT.items():
            if key in cat_lower:
                return desc
        return RUBRO_CONTEXT["default"]