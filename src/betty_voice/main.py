"""BettyVoice main entry point - terminal dashboard + command loop."""

import argparse

from .config import Config
from .state_store import StateStore
from .telemetry_receiver import TelemetryReceiver
from .intent_router import IntentRouter
from .rule_engine import RuleEngine
from .tts import get_tts, respond


def _build_config() -> tuple[Config, argparse.Namespace]:
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
        "--wake-word-threshold",
        type=float,
        default=0.5,
        help="Wake-word detection threshold (default: 0.5)",
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
    args, _ = parser.parse_known_args()

    config = Config()
    config.voice.enabled = args.voice
    config.voice.record_seconds = args.voice_record_seconds
    config.voice.device = args.voice_device
    config.voice.compute_type = args.voice_compute_type
    config.wake_word.enabled = args.wake_word
    config.wake_word.threshold = args.wake_word_threshold
    config.wake_word.cooldown_seconds = args.wake_word_cooldown
    config.wake_phrase.enabled = args.wake_word_mode == "whisper"
    config.wake_phrase.chunk_seconds = args.wake_word_chunk_seconds
    config.wake_phrase.cooldown_seconds = args.wake_word_cooldown
    config.tts.enabled = args.tts and not args.no_tts
    config.tts.engine = args.tts_engine
    config.tts.voice_model_path = args.tts_voice
    return config, args


def _init_speech(config) -> object | None:
    try:
        from .speech_input import _check_deps, record_audio, transcribe, normalize

        _check_deps()
        return (record_audio, transcribe, normalize)
    except ImportError as e:
        print(f"[voice] {e}")
        return None


def _handle_voice_input(speech: tuple, config, router) -> str | None:
    record_audio, transcribe_fn, normalize = speech
    print(f"[voice] Recording for {config.voice.record_seconds}s...")
    try:
        audio = record_audio(duration=config.voice.record_seconds)
    except Exception as e:
        return f"[voice] Recording failed: {e}"
    print("[voice] Transcribing...")
    try:
        raw = transcribe_fn(
            audio,
            model_name=config.voice.model,
            device=config.voice.device,
            compute_type=config.voice.compute_type,
        )
    except Exception as e:
        msg = f"[voice] Transcription failed: {e}"
        if "libcublas" in str(e) or "cublas" in str(e).lower():
            msg += (
                "\n  Hint: Install cuBLAS or use --voice-device cpu to run on CPU."
            )
        return msg
    if not raw:
        return "[voice] No speech detected."
    print(f"[voice] Recognized: {raw}")
    normalized = normalize(raw)
    if normalized != raw:
        print(f"[voice] Normalized: {normalized}")
    result = router.handle(normalized)
    return result


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

    record_audio_fn, transcribe_fn, normalize_fn = speech

    def on_detected():
        print("\n[wakeword] Wake word detected.")
        try:
            audio = record_audio_fn(
                duration=config.wake_word.command_record_seconds
            )
        except Exception as e:
            print(f"[wakeword] Recording failed: {e}")
            return
        try:
            raw = transcribe_fn(
                audio,
                model_name=config.voice.model,
                device=config.voice.device,
                compute_type=config.voice.compute_type,
            )
        except Exception as e:
            print(f"[wakeword] Transcription failed: {e}")
            return
        if not raw:
            print("[wakeword] No speech detected.")
            return
        print(f"[wakeword] Recognized: {raw}")
        normalized = normalize_fn(raw)
        if normalized != raw:
            print(f"[wakeword] Normalized: {normalized}")
        result = router.handle(normalized)
        if result:
            respond(result, tts)

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

    def on_command(normalized: str):
        if not normalized:
            return
        print(normalized)
        result = router.handle(normalized)
        if result:
            respond(result, tts)

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
    router = IntentRouter(state_store=state)
    rules = RuleEngine(state_store=state)
    tts = get_tts(config.tts)

    speech = _init_speech(config) if config.voice.enabled else None
    wake_word_listener = _init_wake_word(config, router, tts)
    wake_phrase_listener = _init_wake_phrase(config, router, tts)

    receiver.start()

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

    try:
        while True:
            callouts = rules.check()
            for c in callouts:
                respond(c, tts)

            status = state.get_status_label()
            prompt = f"[{status}] > "

            try:
                cmd = input(prompt)
            except EOFError:
                break

            if not cmd.strip():
                continue

            if speech and cmd.strip().lower() == "v":
                result = _handle_voice_input(speech, config, router)
                if result and result != "__QUIT__":
                    respond(result, tts)
                continue

            result = router.handle(cmd)
            if result == "__QUIT__":
                break

            if result:
                respond(result, tts)

    except KeyboardInterrupt:
        print()
    finally:
        if wake_phrase_listener:
            wake_phrase_listener.stop()
        if wake_word_listener:
            wake_word_listener.stop()
        receiver.stop()
        print("BettyVoice stopped.")


if __name__ == "__main__":
    main()
