"""Tests for speech runtime plumbing."""

import sys
import threading
import types

from betty_voice.config import Config
from betty_voice import main as voice_main
from betty_voice import speech_input


class FakeRouter:
    def __init__(self):
        self.commands = []

    def handle(self, command):
        self.commands.append(command)
        return f"handled {command}"


def test_speech_pipeline_records_transcribes_normalizes_and_routes(capsys):
    config = Config()
    config.voice.record_seconds = 1.5
    router = FakeRouter()

    def record_audio(duration):
        assert duration == 1.5
        return b"audio"

    def transcribe(audio, model_name, device, compute_type):
        assert audio == b"audio"
        assert model_name == config.voice.model
        assert device == config.voice.device
        assert compute_type == config.voice.compute_type
        return "Betty airspeed"

    def normalize(text):
        assert text == "Betty airspeed"
        return "speed"

    pipeline = voice_main.SpeechCommandPipeline(
        (record_audio, transcribe, normalize),
        config,
        router,
    )

    result = voice_main._handle_voice_input(pipeline, config)

    assert result == "handled speed"
    assert router.commands == ["speed"]
    captured = capsys.readouterr()
    assert "[voice] Recording for 1.5s" in captured.out
    assert "[voice] Recognized: Betty airspeed" in captured.out
    assert "[voice] Normalized: speed" in captured.out


def test_speech_pipeline_speaks_when_requested(monkeypatch):
    config = Config()
    router = FakeRouter()
    spoken = []

    def fake_respond(text, tts):
        spoken.append((text, tts))

    monkeypatch.setattr(voice_main, "respond", fake_respond)
    pipeline = voice_main.SpeechCommandPipeline(
        (
            lambda duration: b"audio",
            lambda audio, model_name, device, compute_type: "status",
            lambda text: text,
        ),
        config,
        router,
        tts="tts",
    )

    result = pipeline.record_transcribe_route(3.0, prefix="wakeword", speak=True)

    assert result == "handled status"
    assert spoken == [("handled status", "tts")]


def test_callout_loop_runs_without_terminal_input(monkeypatch):
    stop_event = threading.Event()
    emitted = []

    class FakeRules:
        def check(self):
            return ["Missile warning."]

    def fake_respond(text, tts):
        emitted.append((text, tts))
        stop_event.set()

    monkeypatch.setattr(voice_main, "respond", fake_respond)

    thread = threading.Thread(
        target=voice_main._callout_loop,
        args=(FakeRules(), "tts", stop_event),
    )
    thread.start()
    thread.join(timeout=1.0)

    assert emitted == [("Missile warning.", "tts")]


def test_stt_model_cache_is_keyed_by_model_device_and_compute(monkeypatch):
    created = []

    class FakeWhisperModel:
        def __init__(self, model_name, **kwargs):
            created.append((model_name, kwargs))

    fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    speech_input._STT_MODELS.clear()

    first = speech_input._lazy_load_model("tiny.en", "cpu", "int8")
    second = speech_input._lazy_load_model("tiny.en", "cpu", "int8")
    third = speech_input._lazy_load_model("base.en", "cpu", "int8")
    fourth = speech_input._lazy_load_model("tiny.en", "cuda", "float16")

    assert first is second
    assert third is not first
    assert fourth is not first
    assert created == [
        ("tiny.en", {"device": "cpu", "compute_type": "int8"}),
        ("base.en", {"device": "cpu", "compute_type": "int8"}),
        ("tiny.en", {"device": "cuda", "compute_type": "float16"}),
    ]
