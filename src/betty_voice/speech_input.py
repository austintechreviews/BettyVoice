"""Optional voice input for BettyVoice - record, transcribe, normalize."""

from __future__ import annotations

import re

PHRASE_MAP: dict[str, str] = {
    "what's my speed": "speed",
    "what is my speed": "speed",
    "how fast am i going": "speed",
    "how fast": "speed",
    "speed": "speed",
    "airspeed": "speed",
    "what's my airspeed": "speed",
    "what is my airspeed": "speed",
    "altitude": "altitude",
    "what's my altitude": "altitude",
    "what is my altitude": "altitude",
    "how high am i": "altitude",
    "how high": "altitude",
    "heading": "heading",
    "what heading": "heading",
    "what's my heading": "heading",
    "what is my heading": "heading",
    "fuel": "fuel",
    "how much fuel": "fuel",
    "what's my fuel": "fuel",
    "what is my fuel": "fuel",
    "fuel remaining": "fuel",
    "state fuel": "fuel",
    "bingo fuel": "fuel",
    "engines": "engines",
    "engine status": "engines",
    "engine": "engines",
    "apu": "apu",
    "auxiliary power": "apu",
    "gear": "gear",
    "landing gear": "gear",
    "gear status": "gear",
    "weapon": "weapon",
    "what weapon": "weapon",
    "what's my weapon": "weapon",
    "what is my weapon": "weapon",
    "what am i carrying": "weapon",
    "weapons": "weapon",
    "stores": "weapon",
    "what stores": "weapon",
    "master arm": "weapon",
    "countermeasures": "countermeasures",
    "counter measures": "countermeasures",
    "flares": "countermeasures",
    "chaff": "countermeasures",
    "warnings": "warnings",
    "warning": "warnings",
    "any warnings": "warnings",
    "are there any warnings": "warnings",
    "any threats": "warnings",
    "threats": "warnings",
    "status": "status",
    "system status": "status",
    "say status": "status",
    "how are we doing": "status",
    "what's my status": "status",
    "what is my status": "status",
}

_WAKE_WORDS = {"betty"}

_STT_MODELS: dict[tuple[str, str, str], object] = {}


def _lazy_load_model(model_name: str, device: str, compute_type: str):
    key = (model_name, device, compute_type)
    if key in _STT_MODELS:
        return _STT_MODELS[key]
    from faster_whisper import WhisperModel

    kw: dict = {}
    if device != "auto":
        kw["device"] = device
    if compute_type != "auto":
        kw["compute_type"] = compute_type
    model = WhisperModel(model_name, **kw)
    _STT_MODELS[key] = model
    return model


def _check_deps() -> None:
    missing = []
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        missing.append("sounddevice")
    try:
        import soundfile  # noqa: F401
    except ImportError:
        missing.append("soundfile")
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper")
    if missing:
        deps = " ".join(missing)
        raise ImportError(
            f"Missing voice dependencies: {deps}. "
            f"Install with: pip install \"betty-voice[voice]\""
        )


def record_audio(duration: float, samplerate: int = 16000) -> bytes:
    import numpy as np
    import sounddevice as sd

    audio: np.ndarray = sd.rec(
        int(duration * samplerate), samplerate=samplerate, channels=1, dtype="float32"
    )
    sd.wait()
    return audio.tobytes()


def transcribe(
    audio_bytes: bytes,
    model_name: str = "tiny.en",
    device: str = "auto",
    compute_type: str = "auto",
    samplerate: int = 16000,
) -> str:
    import numpy as np

    model = _lazy_load_model(model_name, device, compute_type)
    audio_array: np.ndarray = np.frombuffer(audio_bytes, dtype="float32").reshape(-1)
    segments, _ = model.transcribe(audio_array, beam_size=1, language="en")
    text = " ".join(seg.text for seg in segments)
    return text.strip()


def strip_wake_word(text: str) -> str:
    lower = text.lower().strip()
    for ww in _WAKE_WORDS:
        if lower.startswith(ww):
            remainder = lower[len(ww) :].strip()
            if remainder:
                return remainder
    return text


def normalize(text: str) -> str:
    text = strip_wake_word(text)
    lower = text.lower().strip()
    lower = re.sub(r"[^a-z0-9\s']", "", lower)
    lower = re.sub(r"\s+", " ", lower).strip()
    if lower in PHRASE_MAP:
        return PHRASE_MAP[lower]
    return lower


# --- Wake phrase helpers (used by wake_phrase.py) ---

_WAKE_PHRASE_PREFIXES = [
    "hey betty",
    "okay betty",
    "ok betty",
    "hey bettie",
    "okay bettie",
    "betty",
    "bettie",
]

_PHRASE_VARIANTS = {"betty", "bettie", "betti"}


def contains_wake_phrase(text: str, phrase: str = "betty") -> bool:
    """Check whether *text* contains the wake *phrase* (case-insensitive).

    Handles common Whisper transcription variants and possessives
    (e.g. ``"betty's"`` matches ``"betty"``) without matching arbitrary
    substrings such as ``"alphabetty"``.
    """
    lower = re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()
    words = lower.split()
    phrase_lower = phrase.lower()

    if any(_wake_word_matches(word, phrase_lower) for word in words):
        return True

    for variant in _PHRASE_VARIANTS:
        if any(_wake_word_matches(word, variant) for word in words):
            return True

    return False


def strip_wake_phrases(text: str) -> str:
    """Strip a leading wake-phrase prefix from *text*.

    Handles ``"betty speed"``, ``"hey betty speed"``, ``"okay betty speed"``
    and similar variants.  Returns the remainder (preserving original
    casing and punctuation) or the original text if no prefix matches.
    """
    cleaned = _clean_for_match(text)
    for prefix in _WAKE_PHRASE_PREFIXES:
        if cleaned.startswith(prefix):
            # Map the cleaned prefix length back to the original text
            # by counting non-punctuation characters
            idx = _map_prefix_end(text, prefix)
            return text[idx:].strip()
    return text


def _clean_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()


def _wake_word_matches(word: str, phrase: str) -> bool:
    return word == phrase or word == f"{phrase}s"


def _map_prefix_end(original: str, prefix: str) -> int:
    """Return the index in *original* after the *prefix* has been consumed,
    skipping punctuation characters."""
    lower = original.lower()
    matched = 0
    for i, ch in enumerate(lower):
        if matched >= len(prefix):
            return i
        if ch.isalnum() or ch.isspace():
            matched += 1
    return len(original)
