"""StateStore - holds latest telemetry packet and connection status."""

import time
from typing import Any, Optional


class StateStore:
    def __init__(self, stale_seconds: float = 1.0, offline_seconds: float = 5.0):
        self._stale_seconds = stale_seconds
        self._offline_seconds = offline_seconds
        self._packet: Optional[dict] = None
        self._receive_time: Optional[float] = None
        self._prev_packet: Optional[dict] = None

    def update(self, packet: dict) -> None:
        self._prev_packet = self._packet
        self._packet = packet
        self._receive_time = time.monotonic()

    @property
    def packet(self) -> Optional[dict]:
        return self._packet

    @property
    def prev_packet(self) -> Optional[dict]:
        return self._prev_packet

    @property
    def receive_time(self) -> Optional[float]:
        return self._receive_time

    def _age(self) -> Optional[float]:
        if self._receive_time is None:
            return None
        return time.monotonic() - self._receive_time

    def is_online(self) -> bool:
        age = self._age()
        return age is not None and age < self._stale_seconds

    def is_stale(self) -> bool:
        age = self._age()
        if age is None:
            return False
        return self._stale_seconds <= age < self._offline_seconds

    def is_offline(self) -> bool:
        age = self._age()
        if age is None:
            return True
        return age >= self._offline_seconds

    def get(self, *keys: str, default: Any = None) -> Any:
        if self._packet is None:
            return default
        val = self._packet
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
            if val is None:
                return default
        return val

    def get_status_label(self) -> str:
        if self.is_online():
            return "online"
        elif self.is_stale():
            return "stale"
        else:
            return "offline"
