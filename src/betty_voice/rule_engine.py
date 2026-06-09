"""RuleEngine - detects changes and generates passive callouts."""

import time
from typing import List

from .state_store import StateStore


class RuleEngine:
    def __init__(self, state_store: StateStore):
        self._state = state_store
        self._was_online = False
        self._cooldowns: dict[str, float] = {}
        self._announce_flags: dict[str, bool] = {}

    def _can_announce(self, key: str, cooldown: float) -> bool:
        now = time.monotonic()
        last = self._cooldowns.get(key, 0.0)
        if now - last >= cooldown:
            self._cooldowns[key] = now
            return True
        return False

    def check(self) -> List[str]:
        callouts: List[str] = []

        is_online = self._state.is_online()
        if is_online and not self._was_online:
            if self._can_announce("telemetry_connected", 10.0):
                callouts.append("Telemetry connected.")
        elif not is_online and self._was_online:
            if self._can_announce("telemetry_disconnected", 10.0):
                callouts.append("Telemetry disconnected.")
        self._was_online = is_online

        if not is_online:
            return callouts

        warnings = self._state.get("warnings") or {}

        if warnings.get("missile_warning") and self._can_announce("missile", 5.0):
            callouts.append("Missile warning.")

        if warnings.get("engine_warning") and self._can_announce("engine_warning", 15.0):
            callouts.append("Engine warning.")

        systems = self._state.get("systems") or {}
        if systems.get("engine_1_failed") and self._can_announce("engine_1_failed", 15.0):
            callouts.append("Engine one failure.")
        if systems.get("engine_2_failed") and self._can_announce("engine_2_failed", 15.0):
            callouts.append("Engine two failure.")

        weapons = self._state.get("weapons") or {}
        chaff = weapons.get("chaff", -1)
        flares = weapons.get("flares", -1)
        if flares == 0 and self._can_announce("flares_depleted", 30.0):
            callouts.append("Flares depleted.")
        elif 0 < flares <= 5 and self._can_announce("flares_low", 30.0):
            callouts.append("Flares low.")
        if chaff == 0 and self._can_announce("chaff_depleted", 30.0):
            callouts.append("Chaff depleted.")
        elif 0 < chaff <= 5 and self._can_announce("chaff_low", 30.0):
            callouts.append("Chaff low.")

        return callouts

    def reset(self) -> None:
        self._was_online = False
        self._cooldowns.clear()
        self._announce_flags.clear()
