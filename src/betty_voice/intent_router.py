"""IntentRouter - maps typed/voice commands to cockpit-assistant responses."""

from . import number_words as nw
from .state_store import StateStore
from . import unit_conversions as uc


class IntentRouter:
    def __init__(self, state_store: StateStore):
        self._state = state_store

    def handle(self, command: str) -> str:
        cmd = command.strip().lower()
        if not cmd:
            return ""

        if cmd in ("quit", "exit", "q"):
            return "__QUIT__"
        if cmd == "help":
            return self._help()
        if cmd == "status":
            return self._status()
        if cmd == "altitude":
            return self._altitude()
        if cmd in ("speed", "airspeed"):
            return self._speed()
        if cmd == "heading":
            return self._heading()
        if cmd == "engines":
            return self._engines()
        if cmd == "apu":
            return self._apu()
        if cmd == "gear":
            return self._gear()
        if cmd == "weapon":
            return self._weapon()
        if cmd in ("countermeasures", "cm", "cms"):
            return self._countermeasures()
        if cmd == "fuel":
            return self._fuel()
        if cmd in ("warnings", "warning"):
            return self._warnings()
        return f"Unknown command: {cmd}. Type help."

    def _offline(self) -> bool:
        return self._state.is_offline()

    def _altitude(self) -> str:
        if self._offline():
            return "Telemetry offline."
        alt = self._state.get("ownship", "altitude_asl_m") or 0.0
        rad = self._state.get("ownship", "radar_altitude_m") or 0.0
        return f"Altitude {uc.format_feet(alt)}. Radar altitude {uc.format_feet(rad)}."

    def _speed(self) -> str:
        if self._offline():
            return "Telemetry offline."
        ias = self._state.get("ownship", "indicated_airspeed_ms") or 0.0
        return f"Speed {uc.format_knots(ias)}."

    def _heading(self) -> str:
        if self._offline():
            return "Telemetry offline."
        hdg = self._state.get("ownship", "heading_deg") or 0.0
        return f"Heading {uc.format_heading(hdg)}."

    def _engines(self) -> str:
        if self._offline():
            return "Telemetry offline."
        s = self._state.get("systems") or {}
        e1 = "online" if s.get("engine_1_enabled") else "offline"
        e2 = "online" if s.get("engine_2_enabled") else "offline"
        return f"Engine one {e1}, engine two {e2}."

    def _apu(self) -> str:
        if self._offline():
            return "Telemetry offline."
        s = self._state.get("systems") or {}
        status = "on" if s.get("apu_enabled") else "off"
        return f"APU {status}."

    def _gear(self) -> str:
        if self._offline():
            return "Telemetry offline."
        gear = self._state.get("systems", "gear_state") or "unknown"
        display = {"extended": "down", "retracted": "up", "extending": "extending", "retracting": "retracting"}
        return f"Gear {display.get(gear, gear)}."

    def _weapon(self) -> str:
        if self._offline():
            return "Telemetry offline."
        w = self._state.get("weapons") or {}
        name = w.get("selected_weapon", "none")
        if name == "none" or not name:
            arm = "on" if w.get("master_arm") else "off"
            return f"No weapon selected. Master arm {arm}."
        count = w.get("selected_weapon_count", 0)
        arm = "on" if w.get("master_arm") else "off"
        return f"Selected {name}, {nw.number_to_words(count)} remaining. Master arm {arm}."

    def _countermeasures(self) -> str:
        if self._offline():
            return "Telemetry offline."
        w = self._state.get("weapons") or {}
        flares = w.get("flares", 0)
        chaff = w.get("chaff", 0)
        return f"Flares {nw.number_to_words(flares)}, chaff {nw.number_to_words(chaff)}."

    def _fuel(self) -> str:
        if self._offline():
            return "Telemetry offline."
        fuel = self._state.get("systems", "fuel_percent")
        if fuel is not None:
            return f"Fuel {uc.format_percent(fuel)}."
        return "Fuel data not available."

    def _warnings(self) -> str:
        if self._offline():
            return "Telemetry offline."
        warnings = self._state.get("warnings") or {}
        active = []
        if warnings.get("missile_warning"):
            active.append("missile")
        if warnings.get("rwr_spike"):
            active.append("RWR spike")
        if warnings.get("engine_warning"):
            active.append("engine")
        if warnings.get("fuel_warning"):
            active.append("low fuel")
        if not active:
            return "No warnings."
        return "Warning: " + ", ".join(active) + "."

    def _status(self) -> str:
        if self._offline():
            return "Telemetry offline."
        parts = [
            self._altitude(),
            self._speed(),
            self._engines(),
            self._gear(),
        ]
        w = self._state.get("weapons") or {}
        arm = "on" if w.get("master_arm") else "off"
        parts.append(f"Master arm {arm}.")
        fuel = self._state.get("systems", "fuel_percent")
        if fuel is not None:
            parts.append(f"Fuel {uc.format_percent(fuel)}.")
        return " ".join(parts)

    def _help(self) -> str:
        return (
            "Commands: altitude, speed, heading, engines, apu, gear, "
            "weapon, countermeasures, fuel, warnings, status, help, quit."
        )
