"""Tests for betty_voice.tts."""

from betty_voice.config import TTSConfig
from betty_voice.tts import (
    NullTTS,
    PiperTTS,
    QueuedTTS,
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


class TestPiperTTS:
    def test_piper_failure_is_reported(self, monkeypatch, capsys):
        class Result:
            returncode = 2
            stderr = b"bad voice"

        tts = object.__new__(PiperTTS)
        tts._available = True
        tts._cfg = TTSConfig()
        tts._piper_path = "piper"
        tts._model_path = "model.onnx"
        tts._config_path = None
        tts._player = "afplay"

        monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())

        tts.speak("hello")

        captured = capsys.readouterr()
        assert "Piper failed with exit code 2" in captured.out
        assert "bad voice" in captured.out

    def test_piper_uses_length_scale(self, monkeypatch):
        class PiperResult:
            returncode = 0
            stderr = b""

        class PlayerResult:
            returncode = 0
            stderr = b""

        calls = []
        tts = object.__new__(PiperTTS)
        tts._available = True
        tts._cfg = TTSConfig(length_scale=0.85)
        tts._piper_path = "piper"
        tts._model_path = "model.onnx"
        tts._config_path = None
        tts._player = "afplay"

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return PiperResult() if cmd[0] == "piper" else PlayerResult()

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr("os.unlink", lambda path: None)

        tts.speak("hello")

        assert "--length-scale" in calls[0]
        assert calls[0][calls[0].index("--length-scale") + 1] == "0.85"


class TestQueuedTTS:
    def test_queued_tts_speaks_in_order(self):
        class FakeBackend:
            def __init__(self):
                self.spoken = []
                self.closed = False

            def speak(self, text):
                self.spoken.append(text)

            def close(self):
                self.closed = True

        backend = FakeBackend()
        tts = QueuedTTS(backend)
        tts.speak("one")
        tts.speak("two")
        tts.close()

        assert backend.spoken == ["one", "two"]
        assert backend.closed is True


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
