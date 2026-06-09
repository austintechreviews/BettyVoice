"""Tests for betty_voice.tts."""

from betty_voice.config import TTSConfig
from betty_voice.tts import (
    NullTTS,
    _shorten_for_speech,
    get_tts,
    respond,
)


class TestNullTTS:
    def test_speak_does_nothing(self):
        tts = NullTTS()
        tts.speak("hello")  # should not raise


class TestShortenForSpeech:
    def test_help_text(self):
        assert _shorten_for_speech("Commands:\n  help  Show this help") == "Help printed."

    def test_short_response(self):
        assert _shorten_for_speech("Speed four hundred knots.") == "Speed four hundred knots."

    def test_help_prefix(self):
        assert _shorten_for_speech("Commands:") == "Help printed."


class TestGetTTS:
    def test_default_returns_null(self):
        assert isinstance(get_tts(), NullTTS)

    def test_disabled_returns_null(self):
        cfg = TTSConfig(enabled=False)
        assert isinstance(get_tts(cfg), NullTTS)

    def test_enabled_no_model_returns_null(self):
        cfg = TTSConfig(enabled=True, voice_model_path="/nonexistent/model.onnx")
        tts = get_tts(cfg)
        assert isinstance(tts, NullTTS)

    def test_enabled_no_piper_path(self):
        cfg = TTSConfig(enabled=True)
        tts = get_tts(cfg)
        assert isinstance(tts, NullTTS)


class TestRespond:
    def test_prints_to_stdout(self, capsys):
        respond("hello world")
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello world"

    def test_does_not_speak_with_null_tts(self, capsys):
        tts = NullTTS()
        respond("hello", tts)
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello"

    def test_long_text_shortened(self):
        class FakeTTS:
            def __init__(self):
                self.spoken = []
            def speak(self, text):
                self.spoken.append(text)

        tts = FakeTTS()
        long_text = "Commands:\n  help     Show this help message\n  status   Show aircraft status"
        respond(long_text, tts)
        assert tts.spoken == ["Help printed."]

    def test_short_text_not_shortened(self):
        class FakeTTS:
            def __init__(self):
                self.spoken = []
            def speak(self, text):
                self.spoken.append(text)

        tts = FakeTTS()
        respond("Altitude ten thousand feet.", tts)
        assert tts.spoken == ["Altitude ten thousand feet."]
