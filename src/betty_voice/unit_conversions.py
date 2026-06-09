"""Unit conversions for BettyVoice."""


def metres_to_feet(metres: float) -> float:
    return metres * 3.28084


def ms_to_knots(ms: float) -> float:
    return ms * 1.94384


def ms_to_fpm(ms: float) -> float:
    return ms * 196.85


def format_feet(metres: float) -> str:
    feet = metres_to_feet(metres)
    return f"{feet:.0f} feet"


def format_knots(ms: float) -> str:
    knots = ms_to_knots(ms)
    return f"{knots:.0f} knots"


def format_fpm(ms: float) -> str:
    fpm = ms_to_fpm(ms)
    return f"{fpm:.0f} feet per minute"


def format_heading(deg: float) -> str:
    heading = deg % 360
    return f"{heading:03.0f}"


def format_percent(value: float) -> str:
    return f"{value:.0f} percent"
