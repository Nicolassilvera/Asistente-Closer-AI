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

class TTSEngine:
    """Text-to-Speech con ElevenLabs (natural) y pyttsx3 como fallback offline."""

    def __init__(self):
        self._elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self._voice_id       = os.getenv("ELEVENLABS_VOICE_ID", "")
        self._fallback       = None
        self._ready          = False
        self._init()

    def _init(self):
        if self._elevenlabs_key:
            try:
                from elevenlabs.client import ElevenLabs
                self._client = ElevenLabs(api_key=self._elevenlabs_key)
                self._ready  = True
                logger.info("TTS: ElevenLabs listo.")
                return
            except Exception as e:
                logger.warning(f"ElevenLabs no disponible: {e}. Usando fallback.")

        try:
            import pyttsx3
            self._fallback = pyttsx3.init()
            self._fallback.setProperty("rate", 165)
            voices = self._fallback.getProperty("voices")
            for v in voices:
                if "spanish" in v.name.lower() or "es" in v.id.lower():
                    self._fallback.setProperty("voice", v.id)
                    break
            self._ready = True
            logger.info("TTS: pyttsx3 fallback listo.")
        except Exception as e:
            logger.error(f"TTS no disponible: {e}")

    def speak(self, text: str, blocking: bool = True):
        if not self._ready:
            from rich.console import Console
            Console().print(f"[yellow]Jarvis:[/yellow] {text}")
            return

        logger.debug(f"TTS: {text[:60]}...")

        if self._elevenlabs_key and hasattr(self, "_client"):
            self._speak_elevenlabs(text, blocking)
        elif self._fallback:
            self._speak_pyttsx3(text, blocking)

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
            # Fallback SOLO si hay pyttsx3, sin llamar speak() de nuevo
            if self._fallback:
                self._speak_pyttsx3(text, blocking)
            # Si no hay fallback, ya se mostró en consola desde speak()
            # NO llamar speak() de nuevo — eso causaba la duplicación

    #-->

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


class STTEngine:
    """Speech-to-Text con SpeechRecognition + Google."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold         = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.pause_threshold                  = 1.5
        self.recognizer.operation_timeout                = None
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
    Detecta la palabra 'Jarvis' usando openWakeWord.
    Corre en background — llama al callback cuando detecta la wake word.
    """

    def __init__(self, on_detected: callable):
        self.on_detected  = on_detected
        self._running     = False
        self._thread      = None
        self._sensitivity = 0.3

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detector iniciado — escuchando 'Jarvis'")

    def stop(self):
        self._running = False
        logger.info("Wake word detector detenido.")

    def _loop(self):
        try:
            from openwakeword.model import Model
            import pyaudio

            model = Model(
                wakeword_models=["hey_jarvis_v0.1"],
                inference_framework="onnx"
            )

            audio  = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1280
            )

            logger.info("Wake word: stream de audio iniciado. Decí 'Jarvis' para activar.")

            while self._running:
                try:
                    chunk      = stream.read(1280, exception_on_overflow=False)
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    prediction = model.predict(audio_data)

                    for name, score in prediction.items():
                        if score > self._sensitivity:
                            logger.info(f"Wake word detectada: {name} (score: {score:.2f})")
                            self.on_detected()
                            time.sleep(1.5)  # cooldown
                            break

                except Exception as e:
                    logger.debug(f"Wake word loop error: {e}")
                    time.sleep(0.1)

            stream.stop_stream()
            stream.close()
            audio.terminate()

        except Exception as e:
            logger.error(f"Wake word detector falló: {e}")
            logger.info("Continuando sin wake word — usá 'escuchar' para activar el micrófono.")