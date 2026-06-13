"""CLI for synthetic Betty wake-word dataset preparation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .wake_word_training import (
    augment_manifest,
    build_phrase_plan,
    synthesize_with_piper,
    write_livekit_config,
    write_manifest,
    write_phrase_plan,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic wake-word clips and manifests for Betty."
    )
    parser.add_argument("--phrase", default="betty", help="Wake phrase to train")
    parser.add_argument(
        "--output-dir",
        default="wakeword_training/betty",
        help="Output directory for generated data",
    )
    parser.add_argument(
        "--piper-voice",
        type=Path,
        help="Path to a Piper .onnx voice. If omitted, only plan/config files are written.",
    )
    parser.add_argument("--piper-exe", default="piper", help="Piper executable")
    parser.add_argument("--samples-per-phrase", type=int, default=8)
    parser.add_argument("--augmentations-per-clip", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    phrase_plan = build_phrase_plan(args.phrase)
    write_phrase_plan(output_dir / "phrases.json", phrase_plan)

    rows = []
    if args.piper_voice:
        rows = synthesize_with_piper(
            phrase_plan=phrase_plan,
            output_dir=output_dir / "clips",
            piper_model=args.piper_voice,
            piper_exe=args.piper_exe,
            samples_per_phrase=args.samples_per_phrase,
        )
        rows = augment_manifest(
            rows,
            output_dir=output_dir / "clips_augmented",
            augmentations_per_clip=args.augmentations_per_clip,
            seed=args.seed,
        )
    write_manifest(rows, output_dir / "manifest.csv")

    write_livekit_config(
        path=output_dir / "livekit_wakeword.yaml",
        model_name=args.phrase.replace(" ", "_"),
        target_phrases=phrase_plan["positive"],
        n_samples=max(10000, len(phrase_plan["positive"]) * args.samples_per_phrase),
    )

    print(f"Wrote wake-word training assets to {output_dir}")
    if not args.piper_voice:
        print("No --piper-voice supplied, so no WAV clips were synthesized.")
    print("Next: train/export an ONNX model, then run Betty with:")
    print(
        "  betty-voice --wake-word --wake-word-model "
        f"{output_dir / (args.phrase + '.onnx')}"
    )


if __name__ == "__main__":
    main()
