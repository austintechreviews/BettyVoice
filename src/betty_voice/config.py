"""Configuration for BettyVoice."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TelemetryConfig:
    host: str = "127.0.0.1"
    port: int = 47777
    stale_seconds: float = 1.0
    offline_seconds: float = 5.0


@dataclass
class CalloutConfig:
    enabled: bool = True
    missile_warning: bool = True
    engine_warning: bool = True
    low_countermeasures: bool = True
    telemetry_status: bool = True


@dataclass
class VoiceConfig:
    enabled: bool = False
    mode: str = "record_command"
    record_seconds: float = 3.0
    model: str = "tiny.en"
    device: str = "auto"
    compute_type: str = "auto"


@dataclass
class WakeWordConfig:
    enabled: bool = False
    engine: str = "openwakeword"
    model: str = "hey_jarvis"
    threshold: float = 0.5
    cooldown_seconds: float = 2.0
    command_record_seconds: float = 3.0


@dataclass
class WakePhraseConfig:
    enabled: bool = False
    mode: str = "whisper"
    phrase: str = "betty"
    chunk_seconds: float = 2.0
    command_record_seconds: float = 3.0
    threshold_mode: str = "text_contains"
    cooldown_seconds: float = 2.0
    ignore_while_processing: bool = True


@dataclass
class TTSConfig:
    enabled: bool = False
    engine: str = "piper"
    voice_model_path: Optional[str] = None


@dataclass
class Config:
    telemetry: TelemetryConfig = None
    callouts: CalloutConfig = None
    voice: VoiceConfig = None
    wake_word: WakeWordConfig = None
    wake_phrase: WakePhraseConfig = None
    tts: TTSConfig = None

    def __post_init__(self):
        if self.telemetry is None:
            self.telemetry = TelemetryConfig()
        if self.callouts is None:
            self.callouts = CalloutConfig()
        if self.voice is None:
            self.voice = VoiceConfig()
        if self.wake_word is None:
            self.wake_word = WakeWordConfig()
        if self.wake_phrase is None:
            self.wake_phrase = WakePhraseConfig()
        if self.tts is None:
            self.tts = TTSConfig()


DEFAULT_CONFIG = Config()
