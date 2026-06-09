"""Wake-phrase listener using Whisper phrase spotting.

Continuously records short audio chunks, transcribes them with the
existing faster-whisper pipeline, and looks for the configured wake
phrase (default ``"betty"``).  When the wake phrase is found in a
chunk, the chunk's *own* transcription is reused as the command
(after stripping the wake phrase).

This avoids the "silence after wake" problem — the user says
"Betty status" in one utterance and both parts land in the same
listening window.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WakePhraseListener:
    """Listen for a wake phrase using Whisper transcription.

    Runs in a background thread.  Records short chunks, transcribes each
    one, and fires *on_command* with the normalised command text when the
    wake phrase is detected.

    Detections are rate-limited via *cooldown_seconds*.
    """

    def __init__(
        self,
        speech_components: tuple,
        phrase: str = "betty",
        chunk_seconds: float = 2.0,
        cooldown_seconds: float = 2.0,
        model_name: str = "tiny.en",
        device: str = "auto",
        compute_type: str = "auto",
        on_command: Optional[Callable[[str], None]] = None,
    ):
        self._record_audio, self._transcribe, self._normalize = speech_components
        self._phrase = phrase.lower()
        self._chunk_seconds = chunk_seconds
        self._cooldown_seconds = cooldown_seconds
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._on_command = on_command

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_detection: float = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(
            f"[wakephrase] Listening for '{self._phrase}' "
            f"(chunk={self._chunk_seconds}s, cooldown={self._cooldown_seconds}s)"
        )

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _loop(self) -> None:
        from .speech_input import contains_wake_phrase, strip_wake_phrases

        while not self._stop_event.is_set():
            now = time.monotonic()
            if now - self._last_detection < self._cooldown_seconds:
                time.sleep(0.1)
                continue

            try:
                audio = self._record_audio(duration=self._chunk_seconds)
            except Exception as e:
                logger.warning("[wakephrase] Record error: %s", e)
                time.sleep(0.5)
                continue

            try:
                text = self._transcribe(
                    audio,
                    model_name=self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
            except Exception as e:
                logger.warning("[wakephrase] Transcribe error: %s", e)
                continue

            if not text:
                continue

            if not contains_wake_phrase(text, self._phrase):
                continue

            print(f"[wakephrase] Wake phrase detected: {text}")
            self._last_detection = time.monotonic()

            clean = strip_wake_phrases(text)
            if not clean:
                print("[wakephrase] Wake phrase only, no command.")
                continue

            normalized = self._normalize(clean)
            if normalized != clean:
                print(f"[wakephrase] Normalized: {normalized}")

            if self._on_command:
                self._on_command(normalized)

        self._running = False
