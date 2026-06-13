"""Wake-word listener using openWakeWord for hands-free voice commands."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
import time
from typing import Callable, Optional

from .config import WakeWordConfig

logger = logging.getLogger(__name__)
_DEFAULT_WAKE_WORD = WakeWordConfig()


class WakeWordListener:
    """Listens for a wake word using openWakeWord in a background thread.

    Continuously processes microphone audio. When the wake word is detected
    above the threshold, the *on_detected* callback is invoked. While the
    callback runs the microphone stream is released so the callback can
    record command audio without conflicts.

    Detections are rate-limited by *cooldown_seconds*.
    """

    def __init__(
        self,
        model: str = _DEFAULT_WAKE_WORD.model,
        threshold: float = _DEFAULT_WAKE_WORD.threshold,
        cooldown_seconds: float = 2.0,
        on_detected: Optional[Callable[[], None]] = None,
    ):
        self._model_name = model
        self._threshold = threshold
        self._cooldown = cooldown_seconds
        self._on_detected = on_detected
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_detection: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def prediction_keys(self) -> list[str]:
        return _prediction_keys(self._model_name)

    def start(self) -> None:
        if self._running:
            return
        try:
            self._check_deps()
        except ImportError as e:
            print(f"[wakeword] {e}")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(
            f"[wakeword] Listening for '{self._model_name}' "
            f"(threshold={self._threshold})"
        )

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _check_deps(self) -> None:
        missing = []
        try:
            import openwakeword  # noqa: F401
        except ImportError:
            missing.append("openwakeword")
        try:
            import sounddevice  # noqa: F401
        except ImportError:
            missing.append("sounddevice")
        try:
            import numpy  # noqa: F401
        except ImportError:
            missing.append("numpy")
        if missing:
            deps = " ".join(missing)
            raise ImportError(
                f"Missing wake-word dependencies: {deps}. "
                f"Install with: pip install \"betty-voice[wakeword]\""
            )

    def _run(self) -> None:
        import sounddevice as sd
        from openwakeword.model import Model

        SAMPLE_RATE = 16000
        CHUNK_SIZE = 1280

        try:
            model = Model(**_model_init_kwargs(self._model_name))
        except Exception as e:
            print(f"[wakeword] Failed to load model: {e}")
            self._running = False
            return

        while not self._stop_event.is_set():
            try:
                self._listen_loop(model, SAMPLE_RATE, CHUNK_SIZE)
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.warning("[wakeword] Stream error: %s", e)
                    time.sleep(0.5)
        self._running = False

    def _listen_loop(
        self,
        model: object,
        rate: int,
        chunk_size: int,
    ) -> None:
        import sounddevice as sd

        with sd.InputStream(
            samplerate=rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_size,
        ) as stream:
            while not self._stop_event.is_set():
                chunk, _ = stream.read(chunk_size)
                chunk_flat = chunk.flatten()
                prediction = model.predict(chunk_flat)
                score = max(
                    prediction.get(key, 0.0) for key in self.prediction_keys
                )
                if score >= self._threshold:
                    now = time.monotonic()
                    if now - self._last_detection >= self._cooldown:
                        self._last_detection = now
                        break

        if not self._stop_event.is_set() and self._on_detected:
            self._on_detected()


def _model_init_kwargs(model_name: str) -> dict:
    if _is_model_path(model_name):
        return {"wakeword_models": [model_name]}
    return {"wakeword_models": [model_name]}


def _prediction_keys(model_name: str) -> list[str]:
    keys = [model_name]
    if _is_model_path(model_name):
        stem = Path(model_name).stem
        keys.extend([stem, stem.replace("_", " "), os.path.basename(model_name)])
    return list(dict.fromkeys(keys))


def _is_model_path(model_name: str) -> bool:
    suffix = Path(model_name).suffix.lower()
    return suffix in {".onnx", ".tflite"} or os.path.sep in model_name
