"""Tests for context-aware performance solvers."""

from betty_voice.performance_solver import (
    identify_aircraft_id,
    solve_turn_recommendation,
)
from betty_voice.vtol_knowledge import load_reference


def test_identify_aircraft_from_question_or_telemetry():
    assert identify_aircraft_id("best turn speed for Tyro", None) == "t55"
    assert identify_aircraft_id("", {"aircraft": {"name": "FA-26B"}}) == "fa26b"


def test_solve_fa26b_turn_recommendation():
    rec = solve_turn_recommendation(
        "optimal speed for turning",
        {
            "aircraft": {"name": "FA-26B"},
            "ownship": {"indicated_airspeed_ms": 216.0},
            "systems": {"fuel_percent": 85.0},
            "weapons": {"selected_weapon": "AIM-120C", "selected_weapon_count": 4},
        },
        load_reference(),
    )

    assert rec.aircraft_name == "F/A-26B"
    assert 300 <= rec.target_speed_kt <= 380
    assert rec.current_speed_kt == 420
    assert rec.estimated_weight_kg is not None
    assert "flaps up or auto" in rec.flap_advice
