"""Tests for IntentRouter."""

from betty_voice.state_store import StateStore
from betty_voice.intent_router import IntentRouter


def make_online_store():
    store = StateStore(stale_seconds=1.0, offline_seconds=5.0)
    store.update(
        {
            "ownship": {
                "altitude_asl_m": 3048.0,
                "radar_altitude_m": 914.4,
                "indicated_airspeed_ms": 216.0,
                "heading_deg": 270.0,
            },
            "systems": {
                "gear_state": "retracted",
                "engine_1_enabled": True,
                "engine_2_enabled": True,
                "apu_enabled": False,
            },
            "weapons": {
                "master_arm": True,
                "selected_weapon": "AIM-120C",
                "selected_weapon_count": 2,
                "chaff": 20,
                "flares": 12,
            },
        }
    )
    return store


def test_altitude():
    router = IntentRouter(make_online_store())
    result = router.handle("altitude")
    assert "10000 feet" in result
    assert "Radar altitude" in result


def test_speed():
    router = IntentRouter(make_online_store())
    result = router.handle("speed")
    assert "420 knots" in result


def test_heading():
    router = IntentRouter(make_online_store())
    result = router.handle("heading")
    assert "270" in result


def test_engines():
    router = IntentRouter(make_online_store())
    result = router.handle("engines")
    assert "online" in result


def test_gear():
    router = IntentRouter(make_online_store())
    result = router.handle("gear")
    assert "retracted" in result


def test_weapon():
    router = IntentRouter(make_online_store())
    result = router.handle("weapon")
    assert "AIM-120C" in result
    assert "2 remaining" in result
    assert "Master arm on" in result


def test_countermeasures():
    router = IntentRouter(make_online_store())
    result = router.handle("countermeasures")
    assert "Flares 12" in result
    assert "Chaff 20" in result


def test_help():
    router = IntentRouter(make_online_store())
    result = router.handle("help")
    assert "Commands" in result


def test_quit():
    router = IntentRouter(make_online_store())
    assert router.handle("quit") == "__QUIT__"


def test_unknown():
    router = IntentRouter(make_online_store())
    result = router.handle("blah")
    assert "Unknown" in result


def test_offline():
    store = StateStore()
    router = IntentRouter(store)
    assert router.handle("altitude") == "Telemetry offline."
    assert router.handle("speed") == "Telemetry offline."
    assert router.handle("status") == "Telemetry offline."
