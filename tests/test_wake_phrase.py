"""Tests for wake phrase detection, stripping, and configuration."""

from betty_voice.speech_input import contains_wake_phrase, strip_wake_phrases, normalize
from betty_voice.config import Config, WakePhraseConfig


# --- contains_wake_phrase ---

def test_contains_exact_phrase():
    assert contains_wake_phrase("betty", "betty")
    assert contains_wake_phrase("Betty", "betty")
    assert contains_wake_phrase("hey betty", "betty")


def test_contains_phrase_in_sentence():
    assert contains_wake_phrase("i said betty speed", "betty")
    assert contains_wake_phrase("hello betty how are you", "betty")


def test_contains_phrase_substring():
    assert contains_wake_phrase("betty's speed", "betty")
    assert contains_wake_phrase("hey betty's", "betty")


def test_contains_variants():
    assert contains_wake_phrase("bettie", "betty")
    assert contains_wake_phrase("betti", "betty")
    assert contains_wake_phrase("hey bettie speed", "betty")


def test_does_not_contain_phrase():
    assert not contains_wake_phrase("hello world", "betty")
    assert not contains_wake_phrase("speed altitude heading", "betty")
    assert not contains_wake_phrase("", "betty")


def test_contains_punctuation():
    assert contains_wake_phrase("Betty, what's my speed", "betty")
    assert contains_wake_phrase("hello! betty! speed!", "betty")


# --- strip_wake_phrases ---

def test_strip_betty_prefix():
    assert strip_wake_phrases("betty speed") == "speed"
    assert strip_wake_phrases("Betty speed") == "speed"


def test_strip_hey_betty():
    assert strip_wake_phrases("hey betty speed") == "speed"
    assert strip_wake_phrases("hey betty what's my speed") == "what's my speed"


def test_strip_okay_betty():
    assert strip_wake_phrases("okay betty speed") == "speed"
    assert strip_wake_phrases("ok betty speed") == "speed"


def test_strip_bettie():
    assert strip_wake_phrases("hey bettie speed") == "speed"


def test_strip_no_prefix():
    assert strip_wake_phrases("speed") == "speed"
    assert strip_wake_phrases("what's my altitude") == "what's my altitude"


def test_strip_prefix_only():
    assert strip_wake_phrases("betty") == ""


# --- normalize after strip ---

def test_normalize_betty_speed():
    assert normalize("betty speed") == "speed"


def test_normalize_hey_betty_altitude():
    text = strip_wake_phrases("hey betty what's my altitude")
    assert normalize(text) == "altitude"


def test_normalize_okay_betty_fuel():
    text = strip_wake_phrases("okay betty how much fuel")
    assert normalize(text) == "fuel"


# --- config ---

def test_wake_phrase_config_defaults():
    config = Config()
    assert config.wake_phrase is not None
    assert config.wake_phrase.enabled is False
    assert config.wake_phrase.mode == "whisper"
    assert config.wake_phrase.phrase == "betty"
    assert config.wake_phrase.chunk_seconds == 2.0
    assert config.wake_phrase.command_record_seconds == 3.0
    assert config.wake_phrase.cooldown_seconds == 2.0


def test_wake_phrase_config_custom():
    cfg = WakePhraseConfig(
        enabled=True,
        phrase="computer",
        chunk_seconds=1.5,
        command_record_seconds=4.0,
        cooldown_seconds=1.0,
    )
    assert cfg.enabled is True
    assert cfg.phrase == "computer"
    assert cfg.chunk_seconds == 1.5
    assert cfg.command_record_seconds == 4.0
    assert cfg.cooldown_seconds == 1.0


def test_wake_phrase_independent_of_wake_word():
    config = Config()
    config.wake_word.enabled = True
    config.wake_phrase.enabled = True
    assert config.wake_word.enabled is True
    assert config.wake_phrase.enabled is True


def test_wake_phrase_disabled_by_default():
    config = Config()
    assert config.wake_phrase.enabled is False
    config.wake_phrase.enabled = True
    assert config.wake_phrase.enabled is True
