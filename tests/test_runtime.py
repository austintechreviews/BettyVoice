"""Tests for embeddable Betty runtime."""

from betty_voice.config import Config
from betty_voice.runtime import BettyRuntime


def test_runtime_start_stop_and_text_command(monkeypatch):
    logs = []
    config = Config()
    config.callouts.enabled = False
    config.llm.enabled = False

    class FakeReceiver:
        def __init__(self, *args, **kwargs):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    class FakeTTS:
        def __init__(self):
            self.closed = False

        def speak(self, text):
            pass

        def close(self):
            self.closed = True

    monkeypatch.setattr("betty_voice.runtime.TelemetryReceiver", FakeReceiver)
    monkeypatch.setattr("betty_voice.runtime.get_tts", lambda config: FakeTTS())
    monkeypatch.setattr("betty_voice.runtime._init_wake_word", lambda *args: None)
    monkeypatch.setattr("betty_voice.runtime._init_wake_phrase", lambda *args: None)

    runtime = BettyRuntime(config, log=logs.append)
    runtime.start()
    result = runtime.handle_text("speed")
    runtime.stop()

    assert result.startswith("Telemetry offline")
    assert any("Telemetry listening" in line for line in logs)
    assert any("Pilot typed: speed" in line for line in logs)
    assert any("Betty says:" in line for line in logs)
    assert any("Betty runtime stopped" in line for line in logs)


def test_runtime_logs_first_telemetry_packet():
    logs = []
    runtime = BettyRuntime(Config(), log=logs.append)

    runtime._on_telemetry_packet({"schema": "betty.telemetry.v1"})
    runtime._on_telemetry_packet({"schema": "betty.telemetry.v1"})

    assert logs.count("Telemetry connection established.") == 1
