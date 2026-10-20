"""Command-line composer: profile + style + seed -> MIDI, WAV and MP3."""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pretty_midi

from symphony.form import Form, build_form
from symphony.instruments.bass import render_bass
from symphony.instruments.drums import render_drums
from symphony.instruments.guitar import render_guitar
from symphony.instruments.piano import render_piano
from symphony.instruments.violin import render_violin
from symphony.profile import Profile, ProfileError, load_profile
from symphony.render import RenderError, render_track
from symphony.styles import STYLES, Style, get_style
from symphony.variation import VariationPlan, sample_variation_plan

MAX_INSTRUMENTS = 5


@dataclass(frozen=True)
class Composition:
    profile: Profile
    style: Style
    form: Form
    variation_plan: VariationPlan
    seed: int
    variation_attempt: int
    midi: pretty_midi.PrettyMIDI


def build_composition(
    profile: Profile,
    style: Style,
    seed: int,
    *,
    avoid_fingerprints: Sequence[tuple[str, ...]] = (),
    minimum_variation_distance: int = 4,
) -> Composition:
    """Build a deterministic composition and sample its plan exactly once."""

    plan: VariationPlan | None = None
    rng: random.Random | None = None
    attempt = 0
    for attempt in range(128):
        # Retries are deterministic and only occur when a caller supplies the
        # already accepted fingerprints for a variation batch.
        effective_seed = seed if attempt == 0 else seed + attempt * 1_000_003
        candidate_rng = random.Random(effective_seed)
        candidate = sample_variation_plan(profile, style, candidate_rng)
        fingerprint = candidate.fingerprint()
        too_similar = any(
            sum(left != right for left, right in zip(fingerprint, other))
            < minimum_variation_distance
            for other in avoid_fingerprints
        )
        if not too_similar:
            plan, rng = candidate, candidate_rng
            break
    if plan is None or rng is None:
        raise ValueError(
            "Could not sample a sufficiently distinct plan after 128 attempts."
        )

    form = build_form(profile, style, plan)
    midi = pretty_midi.PrettyMIDI(initial_tempo=form.tempo, resolution=960)
    midi.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
    midi.instruments.append(render_piano(form, style, rng, plan))
    midi.instruments.append(render_bass(form, style, profile, rng, plan))
    midi.instruments.append(render_drums(form, style, profile, rng, plan))
    midi.instruments.append(render_violin(form, profile, style, rng, plan))
    midi.instruments.append(render_guitar(form, profile, style, rng, plan))
    if len(midi.instruments) > MAX_INSTRUMENTS:
        raise ValueError(f"Composition exceeds the {MAX_INSTRUMENTS}-instrument limit.")
    return Composition(
        profile=profile,
        style=style,
        form=form,
        variation_plan=plan,
        seed=seed,
        variation_attempt=attempt,
        midi=midi,
    )


def write_midi(composition: Composition, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    composition.midi.write(str(path))
    return path


def _format_duration(seconds: float) -> str:
    total = int(round(seconds))
    minutes, rest = divmod(total, 60)
    return f"{minutes}:{rest:02d}"


def _summary(composition: Composition, midi_path: Path) -> str:
    form = composition.form
    section_bits = " | ".join(
        f"{section.name} {section.bars}" for section in form.sections
    )
    map_bits = []
    for section in form.sections:
        if section.modules:
            names = ", ".join(module.name for module in section.modules)
            map_bits.append(f"{section.name}: {names}")
    return (
        f"{composition.profile.name} / {composition.style.name}\n"
        f"  key {form.key.label}  |  {form.tempo} BPM  |  "
        f"{_format_duration(form.estimated_seconds)}  |  {form.total_bars} bars\n"
        f"  form: {section_bits}\n"
        f"  call path: {'; '.join(map_bits)}\n"
        f"  plan (seed {composition.seed}, resample {composition.variation_attempt}): "
        f"{composition.variation_plan.summary()}\n"
        f"  midi: {midi_path}"
    )


def _normalize_out_prefix(value: str) -> Path:
    path = Path(value)
    if path.suffix.lower() in {".mid", ".midi", ".wav", ".mp3"}:
        path = path.with_suffix("")
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m symphony.compose",
        description="Turn a codebase profile into an instrumental track.",
    )
    parser.add_argument("--profile", required=True, help="Path to a profile JSON file.")
    parser.add_argument(
        "--style",
        required=True,
        choices=sorted(STYLES),
        help="Musical style.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed.")
    parser.add_argument(
        "--variations",
        type=int,
        default=1,
        help="Generate a distinct batch with consecutive seeds (default: 1).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output prefix, e.g. out/track -> out/track.mid/.wav/.mp3.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Write MIDI only (useful for fast iteration).",
    )
    parser.add_argument(
        "--stems", action="store_true",
        help="Also render each instrument to its own WAV file.",
    )
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
        style = get_style(args.style)
        out_prefix = _normalize_out_prefix(args.out)
        if args.variations < 1:
            raise ValueError("--variations must be at least 1.")
        accepted_fingerprints: list[tuple[str, ...]] = []
        for index in range(args.variations):
            seed = args.seed + index
            composition = build_composition(
                profile,
                style,
                seed,
                avoid_fingerprints=accepted_fingerprints,
            )
            accepted_fingerprints.append(composition.variation_plan.fingerprint())
            prefix = (
                out_prefix
                if args.variations == 1
                else out_prefix.with_name(f"{out_prefix.name}_v{index + 1}")
            )
            midi_path = write_midi(composition, prefix.with_suffix(".mid"))
            print(_summary(composition, midi_path))
            if args.no_render:
                continue

            wav_path = prefix.with_suffix(".wav")
            mp3_path = prefix.with_suffix(".mp3")
            render_result = render_track(
                midi_path, wav_path, mp3_path, style=style, stems=args.stems
            )
            print(f"  wav: {wav_path}")
            print(f"  mp3: {mp3_path}")
            if args.stems:
                print("  stems: " + ", ".join(str(path) for path in render_result.stem_paths))
        return 0
    except (ProfileError, RenderError, ValueError, OSError) as exc:
        print(f"symphony: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
