"""Tests for VTOL VR knowledge routing."""

from betty_voice.vtol_knowledge import VTOLKnowledgeBase


def test_recommends_fa26b_a2a_loadout():
    kb = VTOLKnowledgeBase()
    answer = kb.answer("recommend A2A loadout for FA-26B")
    assert "Balanced F/A-26B A2A CAP" in answer
    assert "AIM-120" in answer
    assert "AIRS-T" in answer


def test_aircraft_performance_graph_is_solver_readable():
    kb = VTOLKnowledgeBase()
    answer = kb.answer("show FA-26B performance graph for solver")
    assert "points" in answer
    assert "Linear interpolation" in answer
    assert "drag" in answer


def test_weapon_summary():
    kb = VTOLKnowledgeBase()
    answer = kb.answer("what is AIM-120C")
    assert "AIM-120C" in answer
    assert "active radar homing" in answer


def test_tutorial_sources():
    kb = VTOLKnowledgeBase()
    answer = kb.answer("where are tutorials")
    assert "I can brief" in answer
    assert "missile evasion" in answer


def test_lesson_rephrases_tutorial_content():
    kb = VTOLKnowledgeBase()
    answer = kb.answer("teach me missile evasion")
    assert "Radar missile evasion brief" in answer
    assert "3 or 9 o'clock" in answer


def test_turn_solver_uses_telemetry_context():
    kb = VTOLKnowledgeBase()
    telemetry = {
        "aircraft": {"name": "FA-26B"},
        "ownship": {"indicated_airspeed_ms": 216.0},
        "systems": {"fuel_percent": 85.0},
        "weapons": {"selected_weapon": "AIM-120C", "selected_weapon_count": 4},
    }
    answer = kb.answer("optimal speed for turning", telemetry=telemetry)
    assert "F/A-26B turn solver" in answer
    assert "Current speed is about" in answer
    assert "flaps up or auto" in answer
    assert "Estimated weight" in answer
