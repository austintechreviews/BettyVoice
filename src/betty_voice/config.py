"""Configuration for BettyVoice."""

from dataclasses import dataclass


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
class Config:
    telemetry: TelemetryConfig = None
    callouts: CalloutConfig = None

    def __post_init__(self):
        if self.telemetry is None:
            self.telemetry = TelemetryConfig()
        if self.callouts is None:
            self.callouts = CalloutConfig()


DEFAULT_CONFIG = Config()
