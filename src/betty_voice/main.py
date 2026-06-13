"""BettyVoice main entry point - terminal dashboard + command loop."""

import argparse
import queue
import threading

from .config import Config
from .state_store import StateStore
from .telemetry_receiver import TelemetryReceiver
from .intent_router import IntentRouter
from .llm_formatter import LocalLLMFormatter
from .rule_engine import RuleEngine
from .tts import get_tts, respond


CALL_OUT_POLL_SECONDS = 0.25


def _build_config() -> tuple[Config, argparse.Namespace]:
    defaults = Config()
    parser = argparse.ArgumentParser(description="BettyVoice - VTOL VR voice assistant")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice input (requires sounddevice, soundfile, faster-whisper)",
    )
    parser.add_argument(
        "--voice-record-seconds",
        type=float,
        default=3.0,
        help="Recording duration in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--voice-device",
        type=str,
        default="auto",
        help="Whisper device: auto, cpu, or cuda (default: auto)",
    )
    parser.add_argument(
        "--voice-compute-type",
        type=str,
        default="auto",
        help="Whisper compute type: auto, float16, int8_float16, int8 (default: auto)",
    )
    parser.add_argument(
        "--wake-word",
        action="store_true",
        help="Enable wake-word detection (requires openwakeword, sounddevice, faster-whisper)",
    )
    parser.add_argument(
        "--wake-word-model",
        type=str,
        default=defaults.wake_word.model,
        help=(
            "openWakeWord model name or path to a custom .onnx/.tflite model "
            f"(default: {defaults.wake_word.model})"
        ),
    )
    parser.add_argument(
        "--wake-word-threshold",
        type=float,
        default=defaults.wake_word.threshold,
        help=f"Wake-word detection threshold (default: {defaults.wake_word.threshold})",
    )
    parser.add_argument(
        "--wake-word-cooldown",
        type=float,
        default=2.0,
        help="Cooldown between wake-word detections in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--wake-word-mode",
        type=str,
        default="off",
        choices=["off", "whisper"],
        help="Wake phrase detection mode: off or whisper (default: off)",
    )
    parser.add_argument(
        "--wake-word-chunk-seconds",
        type=float,
        default=2.0,
        help="Recording chunk length for wake phrase spotting in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="Enable TTS output via Piper (requires piper executable + voice model)",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable TTS (overrides --tts)",
    )
    parser.add_argument(
        "--tts-engine",
        type=str,
        default="piper",
        choices=["piper"],
        help="TTS engine (default: piper)",
    )
    parser.add_argument(
        "--tts-voice",
        type=str,
        default=None,
        help="Path to Piper voice model (.onnx file)",
    )
    parser.add_argument(
        "--tts-speed",
        type=float,
        default=defaults.tts.length_scale,
        help=(
            "Piper speech speed as length scale "
            f"(default: {defaults.tts.length_scale}; lower is faster)"
        ),
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        default=None,
        help="Enable local LLM formatting/routing via OpenAI-compatible API",
    )
    parser.add_argument(
        "--no-llm",
        action="store_false",
        dest="llm",
        help="Disable local LLM formatting/routing",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default=defaults.llm.base_url,
        help=f"Local LLM OpenAI-compatible base URL (default: {defaults.llm.base_url})",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=defaults.llm.model,
        help=f"Local LLM model name (default: {defaults.llm.model})",
    )
    args, _ = parser.parse_known_args()

    config = defaults
    config.voice.enabled = args.voice
    config.voice.record_seconds = args.voice_record_seconds
    config.voice.device = args.voice_device
    config.voice.compute_type = args.voice_compute_type
    config.wake_word.enabled = args.wake_word
    config.wake_word.model = args.wake_word_model
    config.wake_word.threshold = args.wake_word_threshold
    config.wake_word.cooldown_seconds = args.wake_word_cooldown
    config.wake_phrase.enabled = args.wake_word_mode == "whisper"
    config.wake_phrase.chunk_seconds = args.wake_word_chunk_seconds
    config.wake_phrase.cooldown_seconds = args.wake_word_cooldown
    config.tts.enabled = args.tts and not args.no_tts
    config.tts.engine = args.tts_engine
    config.tts.voice_model_path = args.tts_voice
    config.tts.length_scale = args.tts_speed
    config.llm.enabled = config.llm.enabled if args.llm is None else args.llm
    config.llm.base_url = args.llm_base_url
    config.llm.model = args.llm_model
    return config, args


def _init_speech(config) -> object | None:
    try:
        from .speech_input import _check_deps, record_audio, transcribe, normalize

        _check_deps()
        return (record_audio, transcribe, normalize)
    except ImportError as e:
        print(f"[voice] {e}")
        return None


def _transcription_error_message(prefix: str, error: Exception) -> str:
    msg = f"[{prefix}] Transcription failed: {error}"
    if "libcublas" in str(error) or "cublas" in str(error).lower():
        msg += "\n  Hint: Install cuBLAS or use --voice-device cpu to run on CPU."
    return msg


class SpeechCommandPipeline:
    """Shared record/transcribe/route path for all speech command modes."""

    def __init__(self, speech: tuple, config: Config, router, tts=None):
        self._record_audio, self._transcribe, self._normalize = speech
        self._config = config
        self._router = router
        self._tts = tts

    def record_transcribe_route(
        self,
        duration: float,
        prefix: str = "voice",
        speak: bool = False,
    ) -> str | None:
        print(f"[{prefix}] Recording for {duration}s...")
        try:
            audio = self._record_audio(duration=duration)
        except Exception as e:
            return self._emit(f"[{prefix}] Recording failed: {e}", speak)

        print(f"[{prefix}] Transcribing...")
        try:
            raw = self._transcribe(
                audio,
                model_name=self._config.voice.model,
                device=self._config.voice.device,
                compute_type=self._config.voice.compute_type,
            )
        except Exception as e:
            return self._emit(_transcription_error_message(prefix, e), speak)

        return self.route_transcript(raw, prefix=prefix, speak=speak)

    def route_transcript(
        self,
        raw: str,
        prefix: str = "voice",
        speak: bool = False,
    ) -> str | None:
        if not raw:
            return self._emit(f"[{prefix}] No speech detected.", speak)

        print(f"[{prefix}] Recognized: {raw}")
        normalized = self._normalize(raw)
        return self.route_normalized(normalized, raw=raw, prefix=prefix, speak=speak)

    def route_normalized(
        self,
        normalized: str,
        raw: str | None = None,
        prefix: str = "voice",
        speak: bool = False,
    ) -> str | None:
        if not normalized:
            return None

        if raw is not None and normalized != raw:
            print(f"[{prefix}] Normalized: {normalized}")

        result = self._router.handle(normalized)
        return self._emit(result, speak)

    def _emit(self, result: str | None, speak: bool) -> str | None:
        if result and speak and result != "__QUIT__":
            respond(result, self._tts)
        return result


def _handle_voice_input(
    pipeline_or_speech: SpeechCommandPipeline | tuple,
    config,
    router=None,
) -> str | None:
    pipeline = pipeline_or_speech
    if not isinstance(pipeline, SpeechCommandPipeline):
        if router is None:
            raise TypeError("router is required when passing raw speech components")
        pipeline = SpeechCommandPipeline(pipeline, config, router)

    return pipeline.record_transcribe_route(
        duration=config.voice.record_seconds,
        prefix="voice",
    )


def _callout_loop(rules, tts, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        for callout in rules.check():
            respond(callout, tts)
        stop_event.wait(CALL_OUT_POLL_SECONDS)


def _input_loop(input_queue: queue.Queue[str | None], stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            cmd = input()
        except EOFError:
            input_queue.put(None)
            return
        input_queue.put(cmd)


def _prompt_for_status(state: StateStore) -> None:
    print(f"[{state.get_status_label()}] > ", end="", flush=True)


def _init_wake_word(config, router, tts) -> object | None:
    """Initialize wake-word listener. Returns the listener or None on failure."""
    if not config.wake_word.enabled:
        return None

    try:
        from .speech_input import _check_deps as _check_voice_deps
        from .speech_input import record_audio, transcribe, normalize

        _check_voice_deps()
        speech = (record_audio, transcribe, normalize)
    except ImportError:
        print(
            "[wakeword] Voice dependencies (sounddevice, faster-whisper) required "
            "for wake-word mode."
        )
        print('  Install with: pip install "betty-voice[voice,wakeword]"')
        return None

    try:
        from .wake_word import WakeWordListener
    except ImportError:
        print("[wakeword] openwakeword not found.")
        print('  Install with: pip install "betty-voice[wakeword]"')
        return None

    pipeline = SpeechCommandPipeline(speech, config, router, tts)

    def on_detected():
        print("\n[wakeword] Wake word detected.")
        pipeline.record_transcribe_route(
            duration=config.wake_word.command_record_seconds,
            prefix="wakeword",
            speak=True,
        )

    listener = WakeWordListener(
        model=config.wake_word.model,
        threshold=config.wake_word.threshold,
        cooldown_seconds=config.wake_word.cooldown_seconds,
        on_detected=on_detected,
    )
    listener.start()
    return listener


def _init_wake_phrase(config, router, tts) -> object | None:
    """Initialize Whisper-based wake-phrase listener."""
    if not config.wake_phrase.enabled:
        return None

    try:
        from .speech_input import _check_deps as _check_voice_deps
        from .speech_input import record_audio, transcribe, normalize

        _check_voice_deps()
        speech = (record_audio, transcribe, normalize)
    except ImportError:
        print(
            "[wakephrase] Voice dependencies (sounddevice, faster-whisper) "
            "required for wake phrase mode."
        )
        print('  Install with: pip install "betty-voice[voice]"')
        return None

    try:
        from .wake_phrase import WakePhraseListener
    except ImportError:
        print("[wakephrase] wake_phrase module not found.")
        return None

    pipeline = SpeechCommandPipeline(speech, config, router, tts)

    def on_command(normalized: str):
        pipeline.route_normalized(normalized, prefix="wakephrase", speak=True)

    listener = WakePhraseListener(
        speech_components=speech,
        phrase=config.wake_phrase.phrase,
        chunk_seconds=config.wake_phrase.chunk_seconds,
        cooldown_seconds=config.wake_phrase.cooldown_seconds,
        model_name=config.voice.model,
        device=config.voice.device,
        compute_type=config.voice.compute_type,
        on_command=on_command,
    )
    listener.start()
    return listener


def main(config: Config = None) -> None:
    if config is None:
        config, _ = _build_config()

    state = StateStore(
        stale_seconds=config.telemetry.stale_seconds,
        offline_seconds=config.telemetry.offline_seconds,
    )
    receiver = TelemetryReceiver(
        state_store=state,
        host=config.telemetry.host,
        port=config.telemetry.port,
    )
    formatter = LocalLLMFormatter(config.llm) if config.llm.enabled else None
    router = IntentRouter(state_store=state, llm_formatter=formatter)
    rules = RuleEngine(state_store=state)
    tts = get_tts(config.tts)

    speech = _init_speech(config) if config.voice.enabled else None
    voice_pipeline = (
        SpeechCommandPipeline(speech, config, router, tts) if speech else None
    )
    wake_word_listener = _init_wake_word(config, router, tts)
    wake_phrase_listener = _init_wake_phrase(config, router, tts)

    receiver.start()
    stop_event = threading.Event()
    input_queue: queue.Queue[str | None] = queue.Queue()
    callout_thread = threading.Thread(
        target=_callout_loop,
        args=(rules, tts, stop_event),
        daemon=True,
    )
    input_thread = threading.Thread(
        target=_input_loop,
        args=(input_queue, stop_event),
        daemon=True,
    )
    callout_thread.start()
    input_thread.start()

    print("BettyVoice v0.2")
    print(f"Listening on {config.telemetry.host}:{config.telemetry.port}")
    print("Type help for commands.\n")
    if wake_word_listener and wake_word_listener.is_running:
        print("Wake-word listening active. Say the wake word then a command.")
    if wake_phrase_listener and wake_phrase_listener.is_running:
        print("Wake phrase listening active. Say 'Betty' then a command.")
    if speech:
        print("Voice input enabled. Type v and press Enter to speak.")
    else:
        print("Voice input disabled. Use --voice to enable.")
    if not config.tts.enabled:
        print("TTS disabled. Use --tts to enable.")
    _prompt_for_status(state)

    try:
        while True:
            try:
                cmd = input_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if cmd is None:
                break

            if not cmd.strip():
                _prompt_for_status(state)
                continue

            if voice_pipeline and cmd.strip().lower() == "v":
                result = _handle_voice_input(voice_pipeline, config)
                if result and result != "__QUIT__":
                    respond(result, tts)
                _prompt_for_status(state)
                continue

            result = router.handle(cmd)
            if result == "__QUIT__":
                break

            if result:
                respond(result, tts)
            _prompt_for_status(state)

    except KeyboardInterrupt:
        print()
    finally:
        stop_event.set()
        if wake_phrase_listener:
            wake_phrase_listener.stop()
        if wake_word_listener:
            wake_word_listener.stop()
        receiver.stop()
        if hasattr(tts, "close"):
            tts.close()
        print("BettyVoice stopped.")


if __name__ == "__main__":
    main()
