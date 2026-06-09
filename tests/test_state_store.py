"""Tests for StateStore."""

import time
from betty_voice.state_store import StateStore


def test_offline_initially():
    store = StateStore()
    assert store.is_offline()
    assert not store.is_online()
    assert not store.is_stale()


def test_online_after_update():
    store = StateStore(stale_seconds=1.0, offline_seconds=5.0)
    store.update({"ownship": {"altitude_asl_m": 3048.0}})
    assert store.is_online()
    assert not store.is_stale()
    assert not store.is_offline()


def test_stale_detection():
    store = StateStore(stale_seconds=0.1, offline_seconds=1.0)
    store.update({"ownship": {"altitude_asl_m": 3048.0}})
    assert store.is_online()
    time.sleep(0.15)
    assert store.is_stale()
    assert not store.is_online()


def test_offline_detection():
    store = StateStore(stale_seconds=0.1, offline_seconds=0.3)
    store.update({"ownship": {"altitude_asl_m": 3048.0}})
    time.sleep(0.4)
    assert store.is_offline()
    assert not store.is_online()
    assert not store.is_stale()


def test_get_nested():
    store = StateStore()
    store.update({"ownship": {"altitude_asl_m": 3048.0}})
    assert store.get("ownship", "altitude_asl_m") == 3048.0
    assert store.get("ownship", "missing", default=0.0) == 0.0
    assert store.get("missing", "key") is None


def test_prev_packet():
    store = StateStore()
    store.update({"v": 1})
    assert store.prev_packet is None
    store.update({"v": 2})
    assert store.prev_packet == {"v": 1}
