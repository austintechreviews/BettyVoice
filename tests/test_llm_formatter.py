"""Tests for local LLM formatting safeguards."""

import json

from betty_voice.config import Config, LLMConfig
from betty_voice.llm_formatter import LocalLLMFormatter


def test_llm_config_defaults_to_local_model_enabled():
    config = Config()
    assert config.llm.enabled is True
    assert config.llm.base_url == "http://localhost:1234/v1"
    assert config.llm.model == "qwen3.5-0.8b-optiq"


def test_cli_can_disable_default_llm(monkeypatch):
    from betty_voice.main import _build_config

    monkeypatch.setattr("sys.argv", ["betty-voice", "--no-llm"])
    config, _ = _build_config()
    assert config.llm.enabled is False


def test_cli_keeps_llm_enabled_by_default(monkeypatch):
    from betty_voice.main import _build_config

    monkeypatch.setattr("sys.argv", ["betty-voice"])
    config, _ = _build_config()
    assert config.llm.enabled is True
    assert config.llm.model == "qwen3.5-0.8b-optiq"


def test_formatter_returns_deterministic_answer_when_disabled():
    fmt = LocalLLMFormatter(LLMConfig(enabled=False))
    assert fmt.format_answer("q", "answer") == "answer"


def test_formatter_uses_local_model(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Use six AIM-120s."}}]}
            ).encode("utf-8")

    def fake_urlopen(req, timeout):
        assert timeout == 8.0
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "qwen3.5-0.8b-optiq"
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    fmt = LocalLLMFormatter(LLMConfig(enabled=True))

    assert fmt.format_answer("loadout", "Use 6 AIM-120s.") == "Use six AIM-120s."


def test_formatter_rejects_new_numbers(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Use 12 AIM-120s."}}]}
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: FakeResponse())
    fmt = LocalLLMFormatter(LLMConfig(enabled=True))

    assert fmt.format_answer("loadout", "Use 6 AIM-120s.") == "Use 6 AIM-120s."


def test_formatter_preserves_turn_solver_details(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "Aim for 348 knots."}}]}
            ).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: FakeResponse())
    source = (
        "F/A-26B turn solver: aim for about 348 knots. Estimated weight "
        "25000 kilograms. For sustained rate, keep flaps up or auto."
    )
    fmt = LocalLLMFormatter(LLMConfig(enabled=True))

    assert fmt.format_answer("turn speed", source) == source
