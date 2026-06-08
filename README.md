# Jarvis CRM

CRM inteligente con automatización de WhatsApp, asistente IA por voz y texto, 
y herramientas de prospección para equipos de ventas.

## ¿Qué hace?

Jarvis CRM centraliza la gestión de clientes y automatiza las tareas repetitivas 
de ventas: seguimiento de leads, envío de mensajes por WhatsApp, prospección 
automática y análisis del pipeline comercial.

## Funcionalidades

### Gestión de Leads
- Alta, edición y seguimiento de clientes potenciales
- Scoring automático y priorización por estado
- Filtros por estado, prioridad y búsqueda libre
- Importar leads desde CSV
- Exportar leads a CSV para usar en otras plataformas

### WhatsApp
- Monitor en vivo — detecta respuestas de clientes automáticamente
- Envío de mensajes individuales desde el CRM
- Campañas masivas con selección múltiple de leads
- Seguimiento automático: Jarvis envía el mensaje cuando llega la fecha programada

### Asistente IA
- Chat con memoria de conversación
- Interpreta instrucciones por texto o por voz
- Activación por voz con la palabra "Eren" o "Buenas"
- Responde, agenda seguimientos y ejecuta acciones en el CRM

### Pizarrón de Ventas
- Calendario de eventos (retiros y envíos)
- Ventas agrupadas por semana con totales automáticos
- Edición inline de precios y márgenes
- Toggle de método de pago (Efectivo / Transferencia)

### LeadFinder
- Prospección automática por rubro y zona
- Extrae empresa, contacto, teléfono y web desde Google Maps

### Dashboard
- Métricas en tiempo real: leads activos, seguimientos del día, ventas del mes
- Acceso rápido a leads calientes y próximos seguimientos

### Ajustes
- Nombre de empresa personalizable
- Intervalo del monitor de WhatsApp
- Seguimiento automático activable/desactivable
- Configuración de API keys desde la interfaz

## Tecnologías

| Capa | Stack |
|---|---|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | FastAPI + SQLite |
| IA | Groq (llama3) / Gemini / OpenAI |
| Voz | Edge TTS + SpeechRecognition + ElevenLabs (opcional) |
| Automatización | Playwright (Chromium) |
| Empaquetado | PyInstaller |

## Instalación desde código fuente

**Requisitos:** Python 3.11+, Node.js 18+

```bash
# Clonar el repo
git clone https://github.com/nicolassilvera/jarvis.git
cd jarvis

# Backend
pip install -r requirements.txt
python -m playwright install chromium

# Frontend
cd ui && npm install && cd ..

# Arrancar
python main.py

Generar el ejecutable (.exe)

build.bat
El ejecutable queda en dist/JarvisCRM/JarvisCRM.exe listo para distribuir.

Configurar API Keys
Las claves se configuran desde Ajustes dentro de la app, sin tocar archivos:

Groq — Asistente IA. Gratis en console.groq.com
Gemini — Alternativa a Groq. Gratis en aistudio.google.com
ElevenLabs (opcional) — Voz premium. Gratis hasta 10k caracteres/mes en elevenlabs.io
Extensión de navegador
La carpeta Chrome_extension/ contiene Jarvis Observer, que envía
contexto del navegador al asistente IA.

Instalación:

Chrome/Edge → chrome://extensions
Activar Modo desarrollador
Cargar sin empaquetar → seleccionar carpeta Chrome_extension
