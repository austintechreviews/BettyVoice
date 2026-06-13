"""Runtime controller for embedding BettyVoice in a UI."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from .config import Config
from .intent_router import IntentRouter
from .llm_formatter import LocalLLMFormatter
from .main import (
    CALL_OUT_POLL_SECONDS,
    SpeechCommandPipeline,
    _handle_voice_input,
    _init_speech,
    _init_wake_phrase,
    _init_wake_word,
)
from .rule_engine import RuleEngine
from .state_store import StateStore
from .telemetry_receiver import TelemetryReceiver
from .tts import get_tts, respond


LogCallback = Callable[[str], None]


class BettyRuntime:
    """Startable BettyVoice runtime for GUI and other embedded frontends."""

    def __init__(self, config: Config, log: Optional[LogCallback] = None):
        self.config = config
        self._log = log or (lambda message: None)
        self._stop_event = threading.Event()
        self._callout_thread: Optional[threading.Thread] = None
        self._online_logged = False
        self._running = False

        self.state = StateStore(
            stale_seconds=config.telemetry.stale_seconds,
            offline_seconds=config.telemetry.offline_seconds,
        )
        formatter = LocalLLMFormatter(config.llm) if config.llm.enabled else None
        self.router = IntentRouter(state_store=self.state, llm_formatter=formatter)
        self.rules = RuleEngine(state_store=self.state)
        self.tts = get_tts(config.tts)
        self.speech = _init_speech(config) if config.voice.enabled else None
        self.voice_pipeline = (
            SpeechCommandPipeline(self.speech, config, self.router, self.tts)
            if self.speech
            else None
        )
        self.receiver = TelemetryReceiver(
            state_store=self.state,
            host=config.telemetry.host,
            port=config.telemetry.port,
            on_packet=self._on_telemetry_packet,
        )
        self.wake_word_listener = None
        self.wake_phrase_listener = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self.receiver.start()
        self._running = True
        self._log(
            f"Telemetry listening on {self.config.telemetry.host}:"
            f"{self.config.telemetry.port}."
        )

        self.wake_word_listener = _init_wake_word(self.config, self.router, self.tts)
        self.wake_phrase_listener = _init_wake_phrase(self.config, self.router, self.tts)
        if self.wake_word_listener and self.wake_word_listener.is_running:
            self._log("Wake-word listener started.")
        if self.wake_phrase_listener and self.wake_phrase_listener.is_running:
            self._log("Wake phrase listener started.")
        if self.speech:
            self._log("Push-to-talk voice input ready.")
        if self.config.llm.enabled:
            self._log(
                f"Local LLM formatter enabled: {self.config.llm.model} "
                f"at {self.config.llm.base_url}."
            )

        self._callout_thread = threading.Thread(target=self._callout_loop, daemon=True)
        self._callout_thread.start()
        self._log("Betty runtime started.")

    def stop(self) -> None:
        if not self._running:
            return
        self._stop_event.set()
        if self.wake_phrase_listener:
            self.wake_phrase_listener.stop()
        if self.wake_word_listener:
            self.wake_word_listener.stop()
        self.receiver.stop()
        if self._callout_thread:
            self._callout_thread.join(timeout=2.0)
        if hasattr(self.tts, "close"):
            self.tts.close()
        self._running = False
        self._log("Betty runtime stopped.")

    def handle_text(self, command: str) -> str | None:
        command = command.strip()
        if not command:
            return None
        self._log(f"Pilot typed: {command}")
        result = self.router.handle(command)
        if result == "__QUIT__":
            self.stop()
            return result
        if result:
            self._log(f"Betty says: {result}")
            respond(result, self.tts)
        return result

    def trigger_voice(self) -> str | None:
        if not self.voice_pipeline:
            message = "Voice input is not enabled or dependencies are missing."
            self._log(message)
            return message
        self._log("Push-to-talk recording started.")
        result = _handle_voice_input(self.voice_pipeline, self.config)
        if result and result != "__QUIT__":
            self._log(f"Betty says: {result}")
            respond(result, self.tts)
        return result

    def status_label(self) -> str:
        return self.state.get_status_label()

    def _callout_loop(self) -> None:
        while not self._stop_event.is_set():
            if self.config.callouts.enabled:
                for callout in self.rules.check():
                    self._log(f"Betty says: {callout}")
                    respond(callout, self.tts)
            self._stop_event.wait(CALL_OUT_POLL_SECONDS)

    def _on_telemetry_packet(self, packet: dict) -> None:
        if not self._online_logged:
            self._online_logged = True
            self._log("Telemetry connection established.")
