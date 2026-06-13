"""Synthetic wake-word dataset helpers for Betty.

This module deliberately avoids importing heavyweight ML libraries. It prepares
positive/negative synthetic audio and config files that can be fed to a real
wake-word trainer such as openWakeWord's notebooks or livekit-wakeword.
"""

from __future__ import annotations

import csv
import json
import random
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path


DEFAULT_POSITIVE_PHRASES = [
    "betty",
    "hey betty",
    "okay betty",
    "betty speed",
    "betty status",
    "betty altitude",
]

DEFAULT_NEGATIVE_PHRASES = [
    "speed",
    "status",
    "altitude",
    "heading",
    "fuel state",
    "gear down",
    "master arm",
    "missile warning",
    "radio check",
    "tower request takeoff",
    "fox three",
    "rifle",
    "pickle",
]


@dataclass(frozen=True)
class SyntheticWakeWordConfig:
    phrase: str = "betty"
    samples_per_phrase: int = 8
    augmentations_per_clip: int = 2
    seed: int = 7
    sample_rate: int = 16000


def slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in text)
    return "_".join(part for part in slug.split("_") if part)


def build_phrase_plan(
    phrase: str,
    positives: list[str] | None = None,
    negatives: list[str] | None = None,
) -> dict[str, list[str]]:
    positive_phrases = positives or [
        p.replace("betty", phrase) for p in DEFAULT_POSITIVE_PHRASES
    ]
    negative_phrases = negatives or DEFAULT_NEGATIVE_PHRASES
    return {
        "positive": list(dict.fromkeys(positive_phrases)),
        "negative": list(dict.fromkeys(negative_phrases)),
    }


def write_phrase_plan(path: Path, phrase_plan: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(phrase_plan, indent=2) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "phrase", "source"])
        writer.writeheader()
        writer.writerows(rows)


def synthesize_with_piper(
    phrase_plan: dict[str, list[str]],
    output_dir: Path,
    piper_model: Path,
    piper_exe: str = "piper",
    samples_per_phrase: int = 8,
) -> list[dict[str, str]]:
    piper_path = shutil.which(piper_exe) or piper_exe
    if not Path(piper_path).exists() and shutil.which(piper_path) is None:
        raise FileNotFoundError(f"Piper executable not found: {piper_exe}")
    if not piper_model.exists():
        raise FileNotFoundError(f"Piper model not found: {piper_model}")

    rows: list[dict[str, str]] = []
    for label, phrases in phrase_plan.items():
        label_dir = output_dir / label
        label_dir.mkdir(parents=True, exist_ok=True)
        for phrase in phrases:
            for idx in range(samples_per_phrase):
                wav_path = label_dir / f"{slugify(phrase)}_{idx:04d}.wav"
                _run_piper(piper_path, piper_model, phrase, wav_path)
                rows.append(
                    {
                        "path": str(wav_path),
                        "label": label,
                        "phrase": phrase,
                        "source": "piper",
                    }
                )
    return rows


def augment_manifest(
    manifest_rows: list[dict[str, str]],
    output_dir: Path,
    augmentations_per_clip: int = 2,
    seed: int = 7,
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows = list(manifest_rows)
    for row in manifest_rows:
        source = Path(row["path"])
        if source.suffix.lower() != ".wav" or not source.exists():
            continue
        for idx in range(augmentations_per_clip):
            gain = rng.uniform(0.72, 1.18)
            pad_ms = rng.randint(0, 280)
            dest = output_dir / row["label"] / f"{source.stem}_aug{idx:02d}.wav"
            dest.parent.mkdir(parents=True, exist_ok=True)
            augment_wav(source, dest, gain=gain, pad_ms=pad_ms)
            rows.append(
                {
                    "path": str(dest),
                    "label": row["label"],
                    "phrase": row["phrase"],
                    "source": f"augmented:g={gain:.2f},pad={pad_ms}",
                }
            )
    return rows


def augment_wav(source: Path, dest: Path, gain: float, pad_ms: int) -> None:
    with wave.open(str(source), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(wav.getnframes())

    if params.sampwidth != 2:
        raise ValueError("Only 16-bit PCM WAV files can be augmented")

    samples = bytearray(frames)
    for i in range(0, len(samples), 2):
        sample = int.from_bytes(samples[i : i + 2], "little", signed=True)
        scaled = max(-32768, min(32767, int(sample * gain)))
        samples[i : i + 2] = scaled.to_bytes(2, "little", signed=True)

    silence_frames = int(params.framerate * (pad_ms / 1000.0))
    silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth

    with wave.open(str(dest), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(silence + bytes(samples) + silence)


def write_livekit_config(
    path: Path,
    model_name: str,
    target_phrases: list[str],
    n_samples: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    phrases = "\n".join(f'  - "{phrase}"' for phrase in target_phrases)
    path.write_text(
        "\n".join(
            [
                f"model_name: {model_name}",
                "target_phrases:",
                phrases,
                f"n_samples: {n_samples}",
                "model:",
                "  model_type: conv_attention",
                "  model_size: small",
                "steps: 50000",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _run_piper(piper_path: str, model_path: Path, text: str, output_path: Path) -> None:
    cmd = [
        piper_path,
        "--model",
        str(model_path),
        "--output-file",
        str(output_path),
    ]
    config_path = model_path.with_suffix(".json")
    if config_path.exists():
        cmd += ["--config", str(config_path)]

    result = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Piper failed for {text!r}: {detail}")
