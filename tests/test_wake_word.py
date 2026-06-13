"""Tests for wake-word configuration and dependency handling."""

import importlib
from betty_voice.config import Config, WakeWordConfig


DEFAULT_BETTY_WAKE_MODEL = "wakeword_training/livekit_output/betty/betty.onnx"


def test_wake_word_config_defaults():
    config = Config()
    assert config.wake_word is not None
    assert config.wake_word.enabled is False
    assert config.wake_word.engine == "openwakeword"
    assert config.wake_word.model == DEFAULT_BETTY_WAKE_MODEL
    assert config.wake_word.threshold == 0.8
    assert config.wake_word.cooldown_seconds == 2.0
    assert config.wake_word.command_record_seconds == 3.0


def test_wake_word_config_custom():
    cfg = WakeWordConfig(
        enabled=True,
        engine="openwakeword",
        model="hey_jarvis",
        threshold=0.7,
        cooldown_seconds=3.0,
        command_record_seconds=4.0,
    )
    assert cfg.enabled is True
    assert cfg.threshold == 0.7
    assert cfg.cooldown_seconds == 3.0
    assert cfg.command_record_seconds == 4.0


def test_wake_word_can_be_disabled():
    config = Config()
    assert config.wake_word.enabled is False
    config.wake_word.enabled = True
    assert config.wake_word.enabled is True


def test_wake_word_dependency_check_import_error():
    """Verify the wake_word module raises ImportError when deps are missing.

    We simulate this by checking that the module's _check_deps method
    would fail if openwakeword is not installed.
    """
    try:
        import openwakeword  # noqa: F401
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
        wakeword_deps_installed = True
    except ImportError:
        wakeword_deps_installed = False

    if not wakeword_deps_installed:
        try:
            from betty_voice.wake_word import WakeWordListener
            listener = WakeWordListener()
            listener._check_deps()
            assert False, "Expected ImportError was not raised"
        except ImportError:
            pass
    else:
        from betty_voice.wake_word import WakeWordListener
        listener = WakeWordListener()
        listener._check_deps()


def test_phrase_normalization_routes_wake_word_commands():
    from betty_voice.speech_input import normalize

    assert normalize("speed") == "speed"
    assert normalize("what's my speed") == "speed"
    assert normalize("altitude") == "altitude"
    assert normalize("heading") == "heading"
    assert normalize("status") == "status"
    assert normalize("weapon") == "weapon"
    assert normalize("countermeasures") == "countermeasures"


def test_intent_router_works_without_wake_word():
    from betty_voice.state_store import StateStore
    from betty_voice.intent_router import IntentRouter

    store = StateStore()
    store.update({"ownship": {"altitude_asl_m": 3048.0}})
    router = IntentRouter(store)
    result = router.handle("altitude")
    assert "feet" in result


def test_wake_word_default_not_enabled_in_voice_mode():
    config = Config()
    config.voice.enabled = True
    assert config.wake_word.enabled is False


def test_wake_word_config_independent_of_voice():
    config = Config()
    config.voice.enabled = True
    config.wake_word.enabled = True
    assert config.voice.enabled is True
    assert config.wake_word.enabled is True
