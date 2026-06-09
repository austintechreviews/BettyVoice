"""TTS interface for BettyVoice.

Provides a pluggable TTS backend system with NullTTS (no-op) and PiperTTS
(local subprocess) implementations.
"""

import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from .config import TTSConfig


class TTSBackend(ABC):
    @abstractmethod
    def speak(self, text: str) -> None: ...


class NullTTS(TTSBackend):
    def speak(self, text: str) -> None:
        pass


class PiperTTS(TTSBackend):
    def __init__(self, config: TTSConfig):
        self._cfg = config
        self._available = False
        self._player = None
        self._init()

    def _init(self):
        piper_exe = shutil.which("piper")
        if piper_exe:
            self._piper_path = piper_exe
        else:
            print("[tts] Piper executable not found on PATH.")
            print("  Install piper: https://github.com/rhasspy/piper")
            return

        model_path = self._cfg.voice_model_path
        if not model_path:
            print("[tts] No TTS voice model specified.")
            print("  Use --tts-voice <path/to/model.onnx>")
            return

        if not os.path.exists(model_path):
            print(f"[tts] Voice model not found: {model_path}")
            return

        self._model_path = model_path

        json_path = Path(model_path).with_suffix(".json")
        self._config_path = str(json_path) if json_path.exists() else None

        self._player = self._find_player()
        if not self._player:
            print("[tts] No audio player available.")
            print(
                "  Install sounddevice+soundfile (pip install sounddevice soundfile)"
                " or ensure afplay/paplay/aplay is on PATH."
            )
            return

        self._available = True
        print(f"[tts] Piper ready ({Path(model_path).name}).")

    def _find_player(self):
        try:
            import sounddevice  # noqa: F401
            import soundfile  # noqa: F401
            return "sounddevice"
        except ImportError:
            pass

        for player in ["afplay", "paplay", "aplay"]:
            if shutil.which(player):
                return player

        return None

    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str) -> None:
        if not self._available or not text:
            return

        wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = wav.name
        wav.close()

        try:
            cmd = [
                self._piper_path,
                "--model", self._model_path,
                "--output-file", wav_path,
            ]
            if self._config_path:
                cmd += ["--config", self._config_path]

            subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if self._player == "sounddevice":
                import soundfile as sf
                import sounddevice as sd
                data, sr = sf.read(wav_path)
                sd.play(data, sr)
                sd.wait()
            else:
                subprocess.run(
                    [self._player, wav_path],
                    capture_output=True,
                    timeout=30,
                )
        except Exception:
            pass
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


def _shorten_for_speech(text: str) -> str:
    if text.startswith("Commands:"):
        return "Help printed."
    return text


def respond(text: str, tts: TTSBackend = None) -> None:
    print(text)
    if tts is not None and not isinstance(tts, NullTTS):
        if len(text) > 150 or text.startswith("Commands:"):
            tts.speak(_shorten_for_speech(text))
        else:
            tts.speak(text)


def get_tts(config: TTSConfig = None) -> TTSBackend:
    if config is None or not config.enabled:
        return NullTTS()

    tts = PiperTTS(config)
    if tts.is_available():
        return tts

    print("[tts] Piper TTS unavailable. Responses will be printed only.")
    return NullTTS()
