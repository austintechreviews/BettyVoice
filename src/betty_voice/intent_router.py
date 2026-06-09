"""IntentRouter - maps typed commands to responses."""

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
        return f"Gear {gear}."

    def _weapon(self) -> str:
        if self._offline():
            return "Telemetry offline."
        w = self._state.get("weapons") or {}
        name = w.get("selected_weapon", "unknown")
        count = w.get("selected_weapon_count", -1)
        arm = "on" if w.get("master_arm") else "off"
        count_str = f"{count} remaining" if count >= 0 else ""
        parts = [f"Selected {name}."]
        if count_str:
            parts.append(f"{count_str}.")
        parts.append(f"Master arm {arm}.")
        return " ".join(parts)

    def _countermeasures(self) -> str:
        if self._offline():
            return "Telemetry offline."
        w = self._state.get("weapons") or {}
        flares = w.get("flares", -1)
        chaff = w.get("chaff", -1)
        return f"Flares {flares}. Chaff {chaff}."

    def _fuel(self) -> str:
        if self._offline():
            return "Telemetry offline."
        fuel = self._state.get("systems", "fuel_percent")
        if fuel is not None:
            return f"Fuel {uc.format_percent(fuel)}."
        return "Fuel data not available."

    def _status(self) -> str:
        if self._offline():
            return "Telemetry offline."
        parts = []
        parts.append(self._altitude())
        parts.append(self._speed())
        parts.append(self._engines())
        gear = self._state.get("systems", "gear_state") or "unknown"
        parts.append(f"Gear {gear}.")
        w = self._state.get("weapons") or {}
        arm = "on" if w.get("master_arm") else "off"
        parts.append(f"Master arm {arm}.")
        name = w.get("selected_weapon", "unknown")
        count = w.get("selected_weapon_count", -1)
        if count >= 0:
            parts.append(f"Selected {name}, {count} remaining.")
        else:
            parts.append(f"Selected {name}.")
        return " ".join(parts)

    def _help(self) -> str:
        return (
            "Commands: altitude, speed, heading, engines, apu, gear, "
            "weapon, countermeasures, fuel, status, help, quit."
        )
