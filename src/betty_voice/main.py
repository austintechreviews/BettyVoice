"""BettyVoice main entry point - terminal dashboard + command loop."""

import argparse

from .config import Config
from .state_store import StateStore
from .telemetry_receiver import TelemetryReceiver
from .intent_router import IntentRouter
from .rule_engine import RuleEngine
from .tts import get_tts


def _build_config() -> Config:
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
    args, _ = parser.parse_known_args()

    config = Config()
    config.voice.enabled = args.voice
    config.voice.record_seconds = args.voice_record_seconds
    config.voice.device = args.voice_device
    config.voice.compute_type = args.voice_compute_type
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
    tts = get_tts(enabled=False)

    speech = _init_speech(config) if config.voice.enabled else None

    receiver.start()

    print("BettyVoice v0.2")
    print(f"Listening on {config.telemetry.host}:{config.telemetry.port}")
    print("Type help for commands.\n")
    if speech:
        print("Voice input enabled. Type v and press Enter to speak.")
    else:
        print("Voice input disabled. Use --voice to enable.")

    try:
        while True:
            callouts = rules.check()
            for c in callouts:
                print(c)
                tts.speak(c)

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
                if result:
                    print(result)
                    if result != "__QUIT__":
                        tts.speak(result)
                continue

            result = router.handle(cmd)
            if result == "__QUIT__":
                break

            print(result)
            if result:
                tts.speak(result)

    except KeyboardInterrupt:
        print()
    finally:
        receiver.stop()
        print("BettyVoice stopped.")


if __name__ == "__main__":
    main()
