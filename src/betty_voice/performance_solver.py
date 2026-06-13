"""Context-aware VTOL VR performance heuristics.

These solvers are intentionally conservative. They provide useful game-helper
recommendations from telemetry and local reference data, but they are not a
substitute for in-game flight cues or a measured aerodynamic model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import unit_conversions as uc


@dataclass(frozen=True)
class TurnRecommendation:
    aircraft_name: str
    current_speed_kt: int | None
    estimated_weight_kg: int | None
    target_speed_kt: int
    speed_band_kt: tuple[int, int]
    flap_advice: str
    technique: str
    caveat: str

    def to_speech(self) -> str:
        current = (
            f" Current speed is about {self.current_speed_kt} knots."
            if self.current_speed_kt is not None
            else ""
        )
        weight = (
            f" Estimated weight {self.estimated_weight_kg} kilograms."
            if self.estimated_weight_kg is not None
            else " Weight estimate unavailable."
        )
        low, high = self.speed_band_kt
        return (
            f"{self.aircraft_name} turn solver: aim for about "
            f"{self.target_speed_kt} knots, usable band {low} to {high} knots."
            f"{current} {weight} {self.flap_advice} {self.technique} {self.caveat}"
        )


TURN_PROFILES: dict[str, dict[str, Any]] = {
    "fa26b": {
        "name": "F/A-26B",
        "base_turn_kt": 330,
        "band_kt": 35,
        "min_kt": 260,
        "max_kt": 390,
        "flaps": (
            "For sustained rate, keep flaps up or auto. If slow and nose authority "
            "matters more than energy, use one notch briefly below roughly 250 knots, "
            "then retract as you accelerate."
        ),
        "technique": (
            "Unload slightly to regain energy, then pull to the lift-limit without "
            "living in high AoA buffet."
        ),
    },
    "f45a": {
        "name": "F-45A",
        "base_turn_kt": 300,
        "band_kt": 30,
        "min_kt": 240,
        "max_kt": 360,
        "flaps": "Leave flight control scheduling alone; avoid dragging external stores if you need turn performance.",
        "technique": "Use the F-45's sensors and nose authority, but do not trade all energy for one snapshot.",
    },
    "t55": {
        "name": "T-55",
        "base_turn_kt": 285,
        "band_kt": 30,
        "min_kt": 230,
        "max_kt": 340,
        "flaps": "Keep flaps up for rate; use landing flaps only for approach-speed handling.",
        "technique": "Keep the trainer light and smooth; it rewards energy discipline more than brute force.",
    },
    "av42c": {
        "name": "AV-42C",
        "base_turn_kt": 210,
        "band_kt": 25,
        "min_kt": 160,
        "max_kt": 260,
        "flaps": "Use wingborne flight for turning performance; vectoring is for low-speed control, not sustained rate.",
        "technique": "Avoid pulling the tilt-jet into a mush; trade altitude and vectoring only when deliberately slowing.",
    },
    "ah94": {
        "name": "AH-94",
        "base_turn_kt": 90,
        "band_kt": 20,
        "min_kt": 40,
        "max_kt": 130,
        "flaps": "No flap recommendation; manage rotor energy and attitude instead.",
        "technique": "For a fast repositioning turn, bank smoothly and preserve rotor authority; for hover fighting, pivot instead of chasing fixed-wing rate.",
    },
    "ef24g": {
        "name": "EF-24G",
        "base_turn_kt": 320,
        "band_kt": 35,
        "min_kt": 250,
        "max_kt": 380,
        "flaps": "Keep wings and flaps configured for energy unless you intentionally need low-speed nose authority.",
        "technique": "It is an EW aircraft first; preserve speed and separation rather than committing to a slow-rate fight.",
    },
}


ALIASES = {
    "fa 26b": "fa26b",
    "fa26b": "fa26b",
    "f a 26b": "fa26b",
    "wasp": "fa26b",
    "f45a": "f45a",
    "f 45a": "f45a",
    "ghost": "f45a",
    "t55": "t55",
    "t 55": "t55",
    "tyro": "t55",
    "av42c": "av42c",
    "av 42c": "av42c",
    "kestrel": "av42c",
    "ah94": "ah94",
    "ah 94": "ah94",
    "ef24g": "ef24g",
    "ef 24g": "ef24g",
}


def solve_turn_recommendation(
    question: str,
    telemetry: dict[str, Any] | None,
    reference: dict[str, Any],
) -> TurnRecommendation:
    aircraft_id = identify_aircraft_id(question, telemetry) or "fa26b"
    profile = TURN_PROFILES.get(aircraft_id, TURN_PROFILES["fa26b"])
    aircraft_ref = _find_aircraft(reference, aircraft_id)
    fuel = _get(telemetry, "systems", "fuel_percent")
    current_speed = _get(telemetry, "ownship", "indicated_airspeed_ms")
    selected_count = _get(telemetry, "weapons", "selected_weapon_count") or 0
    selected_weapon = _get(telemetry, "weapons", "selected_weapon")

    weight_ratio = _estimate_weight_ratio(fuel, selected_count)
    stores_penalty = min(18, max(0, int(selected_count) * 2))
    fuel_penalty = round((weight_ratio - 0.82) * 80)
    target = profile["base_turn_kt"] + stores_penalty + fuel_penalty
    target = max(profile["min_kt"], min(profile["max_kt"], target))
    band = (target - profile["band_kt"], target + profile["band_kt"])

    current_kt = round(uc.ms_to_knots(current_speed)) if current_speed is not None else None
    estimated_weight = _estimate_weight_kg(aircraft_ref, fuel, selected_count, selected_weapon, reference)
    caveat = (
        "This is a heuristic from aircraft type, fuel, and visible selected stores; "
        "use AoA, buffet, G, and energy state to fine tune."
    )

    return TurnRecommendation(
        aircraft_name=profile["name"],
        current_speed_kt=current_kt,
        estimated_weight_kg=estimated_weight,
        target_speed_kt=target,
        speed_band_kt=band,
        flap_advice=profile["flaps"],
        technique=profile["technique"],
        caveat=caveat,
    )


def identify_aircraft_id(question: str, telemetry: dict[str, Any] | None) -> str | None:
    text = _clean(question)
    for alias, aircraft_id in ALIASES.items():
        if alias in text:
            return aircraft_id

    name = _get(telemetry, "aircraft", "name")
    if name:
        cleaned = _clean(str(name))
        for alias, aircraft_id in ALIASES.items():
            if alias in cleaned:
                return aircraft_id
    return None


def _estimate_weight_ratio(fuel_percent: float | None, selected_count: int) -> float:
    fuel_fraction = 0.55 if fuel_percent is None else max(0.0, min(1.0, fuel_percent / 100.0))
    stores_fraction = min(0.08, max(0, selected_count) * 0.006)
    return 0.72 + fuel_fraction * 0.24 + stores_fraction


def _estimate_weight_kg(
    aircraft: dict[str, Any] | None,
    fuel_percent: float | None,
    selected_count: int,
    selected_weapon: str | None,
    reference: dict[str, Any],
) -> int | None:
    if not aircraft or not aircraft.get("gross_weight_kg"):
        return None
    gross = float(aircraft["gross_weight_kg"])
    estimated = gross * _estimate_weight_ratio(fuel_percent, selected_count)
    weapon = _find_weapon_by_name(reference, selected_weapon)
    if weapon and weapon.get("munition_weight_kg"):
        estimated += max(0, selected_count) * float(weapon["munition_weight_kg"])
    return round(estimated)


def _find_aircraft(reference: dict[str, Any], aircraft_id: str) -> dict[str, Any] | None:
    for aircraft in reference.get("aircraft", []):
        if aircraft.get("id") == aircraft_id:
            return aircraft
    return None


def _find_weapon_by_name(reference: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    cleaned = _clean(name)
    for weapon in reference.get("weapons", []):
        terms = [weapon["name"], weapon["id"], *weapon.get("aliases", [])]
        if any(_clean(term) == cleaned for term in terms):
            return weapon
    return None


def _get(data: dict[str, Any] | None, *keys: str) -> Any:
    val: Any = data
    for key in keys:
        if not isinstance(val, dict):
            return None
        val = val.get(key)
    return val


def _clean(text: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    )
