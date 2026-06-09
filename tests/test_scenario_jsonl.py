"""Tests for scenario JSONL file validity."""

import json
import glob


def _scenario_files():
    return glob.glob("scenarios/*.jsonl")


def test_all_scenarios_valid_json():
    files = _scenario_files()
    assert len(files) > 0, "No scenario files found"
    for path in files:
        with open(path) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise AssertionError(f"{path}:{i}: invalid JSON - {e}")
                assert isinstance(obj, dict), f"{path}:{i}: not a JSON object"
                assert "schema" in obj, f"{path}:{i}: missing 'schema'"
                assert "ownship" in obj, f"{path}:{i}: missing 'ownship'"
                assert "systems" in obj, f"{path}:{i}: missing 'systems'"


def test_scenario_required_fields():
    files = _scenario_files()
    for path in files:
        with open(path) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                assert "altitude_asl_m" in obj.get("ownship", {}), f"{path}:{i}: missing ownship.altitude_asl_m"
                assert "heading_deg" in obj.get("ownship", {}), f"{path}:{i}: missing ownship.heading_deg"
                assert "fuel_percent" in obj.get("systems", {}), f"{path}:{i}: missing systems.fuel_percent"


def test_each_scenario_has_at_least_one_packet():
    files = _scenario_files()
    for path in files:
        count = sum(1 for line in open(path) if line.strip())
        assert count >= 1, f"{path}: must have at least one packet"
