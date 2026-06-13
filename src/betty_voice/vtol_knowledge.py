"""Deterministic VTOL VR knowledge lookup for Betty."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from .performance_solver import solve_turn_recommendation


def load_reference() -> dict[str, Any]:
    ref = resources.files("betty_voice.data").joinpath("vtol_reference.json")
    return json.loads(ref.read_text(encoding="utf-8"))


class VTOLKnowledgeBase:
    def __init__(self, data: dict[str, Any] | None = None):
        self._data = data or load_reference()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def answer(self, question: str, telemetry: dict[str, Any] | None = None) -> str | None:
        q = _clean(question)
        if not q:
            return None

        if _mentions(q, "turn", "turning", "rate fight", "dogfight", "corner speed"):
            if _mentions(q, "speed", "optimal", "best", "flap", "flaps", "rate"):
                return solve_turn_recommendation(
                    question,
                    telemetry=telemetry,
                    reference=self._data,
                ).to_speech()

        if _mentions(q, "loadout", "load out", "recommend", "recommended"):
            if _mentions(q, "a2a", "air to air", "cap", "fighter sweep"):
                aircraft = self._find_aircraft(q) or self._find_aircraft("fa26b")
                return self._recommend_loadout(aircraft["id"], mission="a2a")

        if _mentions(q, "performance", "graph", "curve", "solver"):
            aircraft = self._find_aircraft(q)
            if aircraft:
                return self._aircraft_performance(aircraft)
            return self._list_performance_graphs()

        if _mentions(q, "weapon", "missile", "aim", "agm", "gbu", "bomb"):
            weapon = self._find_weapon(q)
            if weapon:
                return self._weapon_summary(weapon)

        if _mentions(q, "aircraft", "plane", "jet", "helo", "helicopter"):
            aircraft = self._find_aircraft(q)
            if aircraft:
                return self._aircraft_summary(aircraft)

        if _mentions(q, "tutorial", "manual", "learn", "training", "teach", "brief"):
            lesson = self._lesson(q)
            if lesson:
                return lesson
            return self._tutorials()

        if _mentions(q, "notch", "evade", "evasion", "chaff", "missile defense"):
            return self._tactic("radar_missile_defense")

        return None

    def _find_aircraft(self, q: str) -> dict[str, Any] | None:
        for aircraft in self._data["aircraft"]:
            terms = [aircraft["name"], aircraft["id"], *aircraft.get("aliases", [])]
            if any(_clean(term) in q for term in terms):
                return aircraft
        return None

    def _find_weapon(self, q: str) -> dict[str, Any] | None:
        for weapon in self._data["weapons"]:
            terms = [weapon["name"], weapon["id"], *weapon.get("aliases", [])]
            if any(_clean(term) in q for term in terms):
                return weapon
        return None

    def _recommend_loadout(self, aircraft_id: str, mission: str) -> str:
        matches = [
            rec for rec in self._data["loadout_recommendations"]
            if rec["aircraft_id"] == aircraft_id and mission in rec["mission"]
        ]
        if not matches:
            return "No loadout recommendation is available for that aircraft and mission."

        rec = matches[0]
        stores = "; ".join(
            f"{item['count']} {item['weapon']} for {item['purpose']}"
            for item in rec["stores"]
        )
        tradeoffs = " ".join(rec["tradeoffs"])
        return f"{rec['name']}: {stores}. {tradeoffs}"

    def _aircraft_summary(self, aircraft: dict[str, Any]) -> str:
        vtol = "VTOL capable" if aircraft.get("vtol") else "not VTOL capable"
        hardpoints = aircraft.get("hardpoints")
        hardpoint_text = ""
        if hardpoints:
            hardpoint_text = (
                f" Hardpoints: {hardpoints.get('weapons')} weapon and "
                f"{hardpoints.get('utility')} utility."
            )
        return (
            f"{aircraft['name']}: {', '.join(aircraft['role'])}. "
            f"Gross weight {aircraft.get('gross_weight_kg', 'unknown')} kg, "
            f"length {aircraft.get('length_m', 'unknown')} m, {vtol}."
            f"{hardpoint_text} {' '.join(aircraft.get('notes', []))}"
        )

    def _weapon_summary(self, weapon: dict[str, Any]) -> str:
        weight = weapon.get("munition_weight_kg")
        weight_text = f", {weight} kg" if weight is not None else ""
        return (
            f"{weapon['name']}: {weapon['domain'].upper()}, "
            f"{weapon['guidance']}, {weapon['range_band']} range{weight_text}."
        )

    def _aircraft_performance(self, aircraft: dict[str, Any]) -> str:
        graphs = [
            graph for graph in self._data["performance_graphs"]
            if graph.get("aircraft_id") == aircraft["id"]
        ]
        if not graphs:
            return f"No solver graph is available for {aircraft['name']} yet."
        graph = graphs[0]
        series = "; ".join(
            f"{s['name']} points {s['points']}" for s in graph["series"]
        )
        return (
            f"{graph['title']}. X axis: {graph['x_axis']['meaning']}. "
            f"{series}. {graph['solver_note']}"
        )

    def _list_performance_graphs(self) -> str:
        names = ", ".join(graph["id"] for graph in self._data["performance_graphs"])
        return f"Available solver-readable graphs: {names}."

    def _tutorials(self) -> str:
        topics = ", ".join(
            lesson["topic"] for lesson in self._data.get("lessons", [])
        )
        return (
            "I can brief these training topics directly: "
            f"{topics}. Ask for one, for example 'teach me missile evasion'."
        )

    def _tactic(self, tactic_id: str) -> str | None:
        for tactic in self._data["tactics"]:
            if tactic["id"] == tactic_id:
                return tactic["summary"]
        return None

    def _lesson(self, q: str) -> str | None:
        for lesson in self._data.get("lessons", []):
            terms = [lesson["topic"], *lesson.get("aliases", [])]
            if any(_clean(term) in q for term in terms):
                steps = " ".join(
                    f"{idx + 1}. {step}" for idx, step in enumerate(lesson["steps"])
                )
                return f"{lesson['title']}: {lesson['summary']} {steps}"
        return None


def _mentions(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _clean(text: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    )
