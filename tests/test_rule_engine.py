"""Tests for RuleEngine."""

import time
from betty_voice.state_store import StateStore
from betty_voice.rule_engine import RuleEngine


def _make_store(packet: dict) -> StateStore:
    store = StateStore(stale_seconds=1.0, offline_seconds=5.0)
    store.update(packet)
    return store


def test_telemetry_connected():
    store = StateStore()
    engine = RuleEngine(store)
    assert engine.check() == []

    store.update({"ownship": {"altitude_asl_m": 1000.0}})
    callouts = engine.check()
    assert any("Telemetry connected" in c for c in callouts)


def test_telemetry_disconnected():
    store = _make_store({"ownship": {"altitude_asl_m": 1000.0}})
    engine = RuleEngine(store)
    engine.check()

    time.sleep(1.5)
    callouts = engine.check()
    assert any("Telemetry disconnected" in c for c in callouts)


def test_missile_warning():
    store = _make_store({"warnings": {"missile_warning": True}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Missile warning" in c for c in callouts)


def test_missile_warning_cooldown():
    store = _make_store({"warnings": {"missile_warning": True}})
    engine = RuleEngine(store)
    engine.check()
    callouts = engine.check()
    assert not any("Missile warning" in c for c in callouts)


def test_rwr_spike():
    store = _make_store({"warnings": {"rwr_spike": True}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("RWR spike" in c for c in callouts)


def test_engine_failure():
    store = _make_store({"systems": {"engine_1_failed": True}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Engine one failure" in c for c in callouts)


def test_low_fuel():
    store = _make_store({"systems": {"fuel_percent": 30.0}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("thirty percent" in c for c in callouts)


def test_critical_fuel():
    store = _make_store({"systems": {"fuel_percent": 15.0}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("fifteen percent" in c for c in callouts)


def test_emergency_fuel():
    store = _make_store({"systems": {"fuel_percent": 5.0}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("five percent" in c for c in callouts)


def test_flares_depleted():
    store = _make_store({"weapons": {"flares": 0}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Flares depleted" in c for c in callouts)


def test_chaff_depleted():
    store = _make_store({"weapons": {"chaff": 0}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Chaff depleted" in c for c in callouts)


def test_flares_low():
    store = _make_store({"weapons": {"flares": 3}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Flares low" in c for c in callouts)


def test_chaff_low():
    store = _make_store({"weapons": {"chaff": 4}})
    engine = RuleEngine(store)
    callouts = engine.check()
    assert any("Chaff low" in c for c in callouts)


def test_no_callouts_when_offline():
    store = StateStore()
    engine = RuleEngine(store)
    callouts = engine.check()
    assert callouts == []


def test_reset():
    store = _make_store({"warnings": {"missile_warning": True}})
    engine = RuleEngine(store)
    engine.check()
    engine.reset()
    callouts = engine.check()
    assert any("Missile warning" in c for c in callouts)
