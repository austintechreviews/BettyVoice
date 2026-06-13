"""Tests for synthetic wake-word training helpers."""

import csv
import wave

from betty_voice.wake_word import _model_init_kwargs, _prediction_keys
from betty_voice.wake_word_training import (
    augment_manifest,
    build_phrase_plan,
    slugify,
    write_livekit_config,
    write_manifest,
    write_phrase_plan,
)


def test_slugify():
    assert slugify("Hey Betty!") == "hey_betty"


def test_build_phrase_plan_replaces_betty():
    plan = build_phrase_plan("computer")
    assert "computer" in plan["positive"]
    assert "hey computer" in plan["positive"]
    assert "speed" in plan["negative"]


def test_write_phrase_plan_and_manifest(tmp_path):
    plan_path = tmp_path / "phrases.json"
    manifest_path = tmp_path / "manifest.csv"
    plan = build_phrase_plan("betty", positives=["betty"], negatives=["speed"])

    write_phrase_plan(plan_path, plan)
    write_manifest(
        [{"path": "clips/betty.wav", "label": "positive", "phrase": "betty", "source": "piper"}],
        manifest_path,
    )

    assert '"positive"' in plan_path.read_text(encoding="utf-8")
    with manifest_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["phrase"] == "betty"


def test_augment_manifest_writes_gain_and_padding(tmp_path):
    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes((1000).to_bytes(2, "little", signed=True) * 160)

    rows = augment_manifest(
        [{"path": str(source), "label": "positive", "phrase": "betty", "source": "test"}],
        tmp_path / "aug",
        augmentations_per_clip=1,
        seed=1,
    )

    assert len(rows) == 2
    assert rows[1]["source"].startswith("augmented:")
    assert (tmp_path / "aug" / "positive").exists()


def test_write_livekit_config(tmp_path):
    path = tmp_path / "livekit.yaml"
    write_livekit_config(path, "betty", ["betty", "hey betty"], 10000)
    text = path.read_text(encoding="utf-8")
    assert "model_name: betty" in text
    assert '  - "hey betty"' in text
    assert "n_samples: 10000" in text


def test_openwakeword_custom_model_path_helpers():
    assert _model_init_kwargs("hey_jarvis") == {"wakeword_models": ["hey_jarvis"]}
    assert _model_init_kwargs("models/betty.onnx") == {
        "wakeword_models": ["models/betty.onnx"]
    }
    assert _prediction_keys("models/betty_wake.onnx") == [
        "models/betty_wake.onnx",
        "betty_wake",
        "betty wake",
        "betty_wake.onnx",
    ]
