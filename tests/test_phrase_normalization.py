"""Tests for voice phrase normalization."""

from betty_voice.speech_input import normalize, strip_wake_word


def test_strip_wake_word():
    assert strip_wake_word("betty speed") == "speed"
    assert strip_wake_word("Betty what's my speed") == "what's my speed"
    assert strip_wake_word("hello there") == "hello there"


def test_normalize_speed():
    assert normalize("speed") == "speed"
    assert normalize("what's my speed") == "speed"
    assert normalize("how fast am i going") == "speed"
    assert normalize("how fast") == "speed"


def test_normalize_altitude():
    assert normalize("altitude") == "altitude"
    assert normalize("what's my altitude") == "altitude"
    assert normalize("how high am i") == "altitude"
    assert normalize("how high") == "altitude"


def test_normalize_heading():
    assert normalize("heading") == "heading"
    assert normalize("what heading") == "heading"
    assert normalize("what's my heading") == "heading"


def test_normalize_fuel():
    assert normalize("fuel") == "fuel"
    assert normalize("how much fuel") == "fuel"
    assert normalize("what's my fuel") == "fuel"
    assert normalize("bingo fuel") == "fuel"


def test_normalize_engines():
    assert normalize("engines") == "engines"
    assert normalize("engine status") == "engines"
    assert normalize("engine") == "engines"


def test_normalize_weapon():
    assert normalize("weapon") == "weapon"
    assert normalize("what weapon") == "weapon"
    assert normalize("what am i carrying") == "weapon"


def test_normalize_countermeasures():
    assert normalize("countermeasures") == "countermeasures"
    assert normalize("flares") == "countermeasures"
    assert normalize("chaff") == "countermeasures"


def test_normalize_warnings():
    assert normalize("warnings") == "warnings"
    assert normalize("any warnings") == "warnings"


def test_normalize_gear():
    assert normalize("gear") == "gear"
    assert normalize("landing gear") == "gear"


def test_normalize_apu():
    assert normalize("apu") == "apu"
    assert normalize("auxiliary power") == "apu"


def test_normalize_status():
    assert normalize("status") == "status"
    assert normalize("system status") == "status"
    assert normalize("how are we doing") == "status"
    assert normalize("what's my status") == "status"


def test_normalize_with_wake_word():
    assert normalize("betty speed") == "speed"
    assert normalize("Betty how fast am i going") == "speed"


def test_normalize_unrecognized():
    assert normalize("hello world") == "hello world"
