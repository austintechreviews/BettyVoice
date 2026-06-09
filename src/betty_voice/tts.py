"""TTS interface stub for BettyVoice."""

from abc import ABC, abstractmethod


class TTSBackend(ABC):
    @abstractmethod
    def speak(self, text: str) -> None:
        ...


class NullTTS(TTSBackend):
    def speak(self, text: str) -> None:
        pass


class PrintTTS(TTSBackend):
    def speak(self, text: str) -> None:
        print(f"[TTS] {text}")


def get_tts(enabled: bool = False) -> TTSBackend:
    if enabled:
        return PrintTTS()
    return NullTTS()
