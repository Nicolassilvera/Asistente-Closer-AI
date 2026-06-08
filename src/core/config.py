import os
import sys
from dotenv import load_dotenv
from src.core.exceptions import ConfigError

if getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
    load_dotenv(os.path.join(_base, '.env'))
else:
    _base = os.getcwd()
    load_dotenv()

class Config:
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
    GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    APP_NAME         = os.getenv("APP_NAME", "Jarvis")
    DEBUG            = os.getenv("DEBUG", "false").lower() == "true"
    DB_PATH          = os.path.join(_base, "data", "jarvis.db")
    LOG_PATH         = os.path.join(_base, "logs", "jarvis.log")
    MAX_TASK_RETRIES = 3
    MICROPHONE_INDEX = int(os.getenv("MICROPHONE_INDEX", "0"))
    WAKE_WORD_THRESHOLD = int(os.getenv("WAKE_WORD_THRESHOLD", "300"))

    def validate(self):
        if not any([self.GROQ_API_KEY, self.GEMINI_API_KEY, self.OPENAI_API_KEY]):
            raise ConfigError("Necesitás al menos una API key — GROQ_API_KEY, GEMINI_API_KEY o OPENAI_API_KEY")

config = Config()