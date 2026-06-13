"""TTS interface for BettyVoice.

Provides a pluggable TTS backend system with NullTTS (no-op) and PiperTTS
(local subprocess) implementations.
"""

import os
import queue
import shutil
import subprocess
import tempfile
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from .config import TTSConfig


class TTSBackend(ABC):
    @abstractmethod
    def speak(self, text: str) -> None: ...

    def close(self) -> None:
        pass


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
                "--length-scale", str(self._cfg.length_scale),
                "--output-file", wav_path,
            ]
            if self._config_path:
                cmd += ["--config", self._config_path]

            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", errors="replace").strip()
                print(f"[tts] Piper failed with exit code {result.returncode}.")
                if detail:
                    print(f"[tts] {detail}")
                return

            if self._player == "sounddevice":
                import soundfile as sf
                import sounddevice as sd
                data, sr = sf.read(wav_path)
                sd.play(data, sr)
                sd.wait()
            else:
                player_result = subprocess.run(
                    [self._player, wav_path],
                    capture_output=True,
                    timeout=30,
                )
                if player_result.returncode != 0:
                    detail = player_result.stderr.decode(
                        "utf-8", errors="replace"
                    ).strip()
                    print(
                        f"[tts] Audio player failed with exit code "
                        f"{player_result.returncode}."
                    )
                    if detail:
                        print(f"[tts] {detail}")
        except Exception as e:
            print(f"[tts] Speech output failed: {e}")
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class QueuedTTS(TTSBackend):
    """Serialize speech in a worker so command handling stays responsive."""

    def __init__(self, backend: TTSBackend):
        self._backend = backend
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def speak(self, text: str) -> None:
        if text:
            self._queue.put(text)

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=2.0)
        self._backend.close()

    def _run(self) -> None:
        while True:
            text = self._queue.get()
            if text is None:
                return
            self._backend.speak(text)


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
        return QueuedTTS(tts)

    print("[tts] Piper TTS unavailable. Responses will be printed only.")
    return NullTTS()
