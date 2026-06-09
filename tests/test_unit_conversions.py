"""Tests for unit conversions."""

from betty_voice.unit_conversions import (
    metres_to_feet,
    ms_to_knots,
    ms_to_fpm,
    format_feet,
    format_knots,
    format_heading,
)


def test_metres_to_feet():
    assert metres_to_feet(1.0) == 3.28084
    assert metres_to_feet(0.0) == 0.0


def test_ms_to_knots():
    assert ms_to_knots(1.0) == 1.94384
    assert ms_to_knots(0.0) == 0.0


def test_ms_to_fpm():
    assert ms_to_fpm(1.0) == 196.85


def test_format_feet():
    assert format_feet(3048.0) == "10000 feet"


def test_format_knots():
    assert format_knots(216.0) == "420 knots"


def test_format_heading():
    assert format_heading(270.0) == "270"
    assert format_heading(0.0) == "000"
    assert format_heading(359.5) == "360"
