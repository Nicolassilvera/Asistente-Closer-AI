import os
from dotenv import load_dotenv
from src.core.exceptions import ConfigError

load_dotenv()

class Config:
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
    GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    APP_NAME         = os.getenv("APP_NAME", "Jarvis")
    DEBUG            = os.getenv("DEBUG", "false").lower() == "true"
    DB_PATH          = "data/jarvis.db"
    LOG_PATH         = "logs/jarvis.log"
    MAX_TASK_RETRIES = 3
    MICROPHONE_INDEX = int(os.getenv("MICROPHONE_INDEX", "0"))

    def validate(self):
        if not any([self.GROQ_API_KEY, self.GEMINI_API_KEY, self.OPENAI_API_KEY]):
            raise ConfigError("Necesitás al menos una API key — GROQ_API_KEY, GEMINI_API_KEY o OPENAI_API_KEY")

config = Config()