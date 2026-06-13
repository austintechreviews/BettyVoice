"""Tests for UDP telemetry receiving."""

import json

from betty_voice.state_store import StateStore
from betty_voice.telemetry_receiver import TelemetryReceiver


def test_receiver_accepts_packets_from_configured_source():
    store = StateStore()
    seen = []
    receiver = TelemetryReceiver(
        store,
        source_host="127.0.0.1",
        on_packet=seen.append,
    )
    receiver._accept_packet(
        json.dumps({"schema": "betty.telemetry.v1"}).encode(),
        ("127.0.0.1", 50000),
    )

    assert store.packet == {"schema": "betty.telemetry.v1"}
    assert seen == [{"schema": "betty.telemetry.v1"}]


def test_receiver_ignores_packets_from_other_sources():
    store = StateStore()
    receiver = TelemetryReceiver(
        store,
        source_host="192.168.1.115",
    )
    receiver._accept_packet(
        json.dumps({"schema": "betty.telemetry.v1"}).encode(),
        ("127.0.0.1", 50000),
    )

    assert store.packet is None
