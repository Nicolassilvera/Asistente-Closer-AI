# src/core/voice.py
import os
import io
import time
import threading
import numpy as np
import speech_recognition as sr
from src.core.logger import logger
from src.core.personality import say
from src.core.exceptions import JarvisError

class VoiceError(JarvisError):
    pass

#-->

class TTSEngine:
    """Text-to-Speech: Edge TTS (principal) → ElevenLabs → pyttsx3 fallback."""

    def __init__(self):
        self._elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self._voice_id       = os.getenv("ELEVENLABS_VOICE_ID", "")
        self._edge_voice     = os.getenv("EDGE_TTS_VOICE", "es-MX-JorgeNeural")
        self._fallback       = None
        self._ready          = False
        self._provider       = None
        self._init()

    def _init(self):
        # Prioridad 1: Edge TTS
        try:
            import edge_tts
            import pygame
            pygame.mixer.init()
            self._ready    = True
            self._provider = "edge_tts"
            logger.info(f"TTS: Edge TTS listo — voz: {self._edge_voice}")
            return
        except Exception as e:
            logger.warning(f"Edge TTS no disponible: {e}")

        # Prioridad 2: ElevenLabs
        if self._elevenlabs_key:
            try:
                from elevenlabs.client import ElevenLabs
                self._client   = ElevenLabs(api_key=self._elevenlabs_key)
                self._ready    = True
                self._provider = "elevenlabs"
                logger.info("TTS: ElevenLabs listo.")
                return
            except Exception as e:
                logger.warning(f"ElevenLabs no disponible: {e}")

        # Prioridad 3: pyttsx3 offline
        try:
            import pyttsx3
            self._fallback = pyttsx3.init()
            self._fallback.setProperty("rate", 165)
            voices = self._fallback.getProperty("voices")
            for v in voices:
                if "spanish" in v.name.lower() or "es" in v.id.lower():
                    self._fallback.setProperty("voice", v.id)
                    break
            self._ready    = True
            self._provider = "pyttsx3"
            logger.info("TTS: pyttsx3 fallback listo.")
        except Exception as e:
            logger.error(f"TTS no disponible: {e}")

    def speak(self, text: str, blocking: bool = True):
        if not self._ready:
            from rich.console import Console
            Console().print(f"[yellow]Jarvis:[/yellow] {text}")
            return

        logger.debug(f"TTS [{self._provider}]: {text[:60]}...")

        if self._provider == "edge_tts":
            self._speak_edge(text, blocking)
        elif self._provider == "elevenlabs":
            self._speak_elevenlabs(text, blocking)
        elif self._provider == "pyttsx3":
            self._speak_pyttsx3(text, blocking)

    #-->

    def _speak_edge(self, text: str, blocking: bool):
        import asyncio
        import edge_tts
        import pygame
        import io

        async def _generate():
            tts        = edge_tts.Communicate(text, voice=self._edge_voice)
            audio_data = b""
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        def _play():
            try:
                # Crear loop completamente aislado en este hilo
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    audio_data = loop.run_until_complete(_generate())
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

                if pygame.mixer.get_init():
                    pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

                sound = pygame.mixer.Sound(io.BytesIO(audio_data))
                sound.play()

                while pygame.mixer.get_busy():
                    time.sleep(0.05)

            except Exception as e:
                logger.warning(f"Edge TTS error: {e}")
                if self._fallback:
                    self._speak_pyttsx3(text, blocking)

        # Siempre en hilo dedicado para aislar asyncio de Playwright u otros loops
        t = threading.Thread(target=_play, daemon=True)
        t.start()
        if blocking:
            t.join()

    #-->

    def _speak_elevenlabs(self, text: str, blocking: bool):
        try:
            import pygame
            from elevenlabs import VoiceSettings

            audio = self._client.text_to_speech.convert(
                voice_id=self._voice_id or "pNInz6obpgDQGcFmaJgB",
                text=text,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.1,
                    use_speaker_boost=True
                )
            )

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            audio_data = b"".join(audio)
            sound      = pygame.mixer.Sound(io.BytesIO(audio_data))
            sound.play()

            if blocking:
                while pygame.mixer.get_busy():
                    time.sleep(0.05)

        except Exception as e:
            logger.warning(f"ElevenLabs error: {e}. Usando fallback.")
            if self._fallback:
                self._speak_pyttsx3(text, blocking)

    def _speak_pyttsx3(self, text: str, blocking: bool):
        try:
            if blocking:
                self._fallback.say(text)
                self._fallback.runAndWait()
            else:
                threading.Thread(
                    target=lambda: (self._fallback.say(text), self._fallback.runAndWait()),
                    daemon=True
                ).start()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")

    def stop(self):
        try:
            if self._fallback:
                self._fallback.stop()
        except Exception:
            pass

#-->

class STTEngine:
    """Speech-to-Text con SpeechRecognition + Google."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold          = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.pause_threshold                   = 1.5
        self.recognizer.operation_timeout                 = None
        logger.info("STT: SpeechRecognition listo.")

    def listen(self, timeout: int = 8, phrase_limit: int = 30) -> str:
        from src.core.config import config
        device_index = config.MICROPHONE_INDEX if config.MICROPHONE_INDEX > 0 else None

        with sr.Microphone(device_index=device_index) as source:
            logger.debug("STT: calibrando ruido ambiente...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.debug(f"STT: umbral = {self.recognizer.energy_threshold:.0f}")

            try:
                logger.debug("STT: escuchando...")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
            except sr.WaitTimeoutError:
                return ""

        try:
            text = self.recognizer.recognize_google(audio, language="es-AR")
            logger.info(f"STT reconoció: {text}")
            return text.strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.error(f"STT error de red: {e}")
            raise VoiceError(f"Sin conexión para reconocimiento de voz: {e}")


class WakeWordDetector:
    """
    Detecta la palabra de activación por STT continuo.
    Acepta cualquier palabra — no depende de modelos externos.
    """

    def __init__(self, on_detected: callable, wake_word: str = "eren"):
        self.on_detected  = on_detected
        self.wake_word    = wake_word.lower()
        self._running     = False
        self._thread      = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Wake word detector iniciado — escuchando '{self.wake_word}'")

    def stop(self):
        self._running = False
        logger.info("Wake word detector detenido.")

    def _loop(self):
        from src.core.config import config
    
        recognizer = sr.Recognizer()
        recognizer.energy_threshold          = getattr(config, 'WAKE_WORD_THRESHOLD', 500)
        recognizer.dynamic_energy_threshold  = False
        recognizer.pause_threshold           = 0.8
    
        device_index = config.MICROPHONE_INDEX if config.MICROPHONE_INDEX > 0 else None
    
        wake_variants = [
            # Eren y variantes fonéticas
            "eren", "eron", "aaron", "aron", "iron", "erren",
            "aren", "erin", "airón", "herren",
            # Activadores alternativos
            "buenas", "buen día", "buenos días", "hey",
            "hola", "oye", "escucha", "atención",
        ]
    
        logger.info(f"Wake word: escuchando '{self.wake_word}' — umbral: {recognizer.energy_threshold}")
    
        try:
            mic = sr.Microphone(device_index=device_index)
            with mic as source:
                logger.info("Wake word: micrófono abierto en modo continuo.")
                while self._running:
                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=2,
                            phrase_time_limit=2
                        )
                        text = recognizer.recognize_google(
                            audio, language="es-AR"
                        ).lower().strip()
    
                        if not text:
                            continue
                        
                        logger.debug(f"Wake loop: '{text}'")
    
                        # Detección por palabra completa o texto exacto
                        words    = text.split()
                        detected = False
    
                        for w in wake_variants:
                            if w == text.strip():          # texto exacto
                                detected = True
                                break
                            if w in words:                 # palabra completa
                                detected = True
                                break
                            if len(w) > 5 and w in text:   # substring solo para palabras largas
                                detected = True
                                break
                            
                        if detected:
                            logger.info(f"Wake word detectada: '{text}'")
                            self.on_detected()
                            time.sleep(2)
    
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        logger.warning(f"STT error: {e}")
                        time.sleep(3)
                    except Exception as e:
                        logger.debug(f"Wake loop error: {e}")
                        time.sleep(0.5)
    
        except Exception as e:
            logger.error(f"Wake word detector falló: {e}")

