"""Optional voice input for BettyVoice - record, transcribe, normalize."""

from __future__ import annotations

import re
from typing import Optional

PHRASE_MAP: dict[str, str] = {
    "what's my speed": "speed",
    "what is my speed": "speed",
    "speed": "speed",
    "altitude": "altitude",
    "what's my altitude": "altitude",
    "what is my altitude": "altitude",
    "heading": "heading",
    "fuel": "fuel",
    "how much fuel": "fuel",
    "engines": "engines",
    "apu": "apu",
    "gear": "gear",
    "weapon": "weapon",
    "what weapon": "weapon",
    "what's my weapon": "weapon",
    "what is my weapon": "weapon",
    "countermeasures": "countermeasures",
    "counter measures": "countermeasures",
    "status": "status",
}

_WAKE_WORDS = {"betty", "betty"}

_STT_MODEL: Optional[object] = None


def _lazy_load_model(model_name: str, device: str, compute_type: str):
    global _STT_MODEL
    if _STT_MODEL is not None:
        return _STT_MODEL
    from faster_whisper import WhisperModel

    kw: dict = {}
    if device != "auto":
        kw["device"] = device
    if compute_type != "auto":
        kw["compute_type"] = compute_type
    _STT_MODEL = WhisperModel(model_name, **kw)
    return _STT_MODEL


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
