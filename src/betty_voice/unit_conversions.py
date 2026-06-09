"""Unit conversions for BettyVoice."""

from . import number_words as nw


def metres_to_feet(metres: float) -> float:
    return metres * 3.28084


def ms_to_knots(ms: float) -> float:
    return ms * 1.94384


def ms_to_fpm(ms: float) -> float:
    return ms * 196.85


def format_feet(metres: float) -> str:
    feet = round(metres_to_feet(metres))
    return f"{nw.number_to_words(feet)} feet"


def format_knots(ms: float) -> str:
    knots = round(ms_to_knots(ms))
    return f"{nw.number_to_words(knots)} knots"


def format_fpm(ms: float) -> str:
    fpm = ms_to_fpm(ms)
    return f"{fpm:.0f} feet per minute"


def format_heading(deg: float) -> str:
    heading = round(deg % 360)
    return nw.number_to_words_digits(heading)


def format_percent(value: float) -> str:
    return f"{nw.number_to_words(round(value))} percent"
