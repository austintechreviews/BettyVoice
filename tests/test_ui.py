"""Tests for Betty browser UI config plumbing."""

from betty_voice.config import Config
from betty_voice.ui import _config_to_payload, _payload_to_config


def test_ui_payload_round_trips_core_settings():
    payload = _config_to_payload(Config())
    payload.update(
        {
            "telemetry_source_host": "192.168.1.115",
            "telemetry_bind_host": "0.0.0.0",
            "telemetry_port": 47778,
            "voice_enabled": True,
            "wake_word_enabled": True,
            "tts_enabled": True,
            "tts_voice": "/tmp/voice.onnx",
            "tts_speed": 0.85,
            "llm_enabled": False,
        }
    )

    config = _payload_to_config(payload)

    assert config.telemetry.port == 47778
    assert config.telemetry.host == "0.0.0.0"
    assert config.telemetry.source_host == "192.168.1.115"
    assert config.voice.enabled is True
    assert config.wake_word.enabled is True
    assert config.tts.enabled is True
    assert config.tts.voice_model_path == "/tmp/voice.onnx"
    assert config.tts.length_scale == 0.85
    assert config.llm.enabled is False


def test_ui_accepts_old_telemetry_host_as_source_filter():
    payload = _config_to_payload(Config())
    payload.pop("telemetry_source_host")
    payload["telemetry_host"] = "192.168.1.115"

    config = _payload_to_config(payload)

    assert config.telemetry.host == "0.0.0.0"
    assert config.telemetry.source_host == "192.168.1.115"
