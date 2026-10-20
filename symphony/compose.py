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
from symphony.instruments.piano import render_piano
from symphony.profile import Profile, ProfileError, load_profile
from symphony.render import RenderError, render_track
from symphony.styles import STYLES, Style, get_style


@dataclass(frozen=True)
class Composition:
    profile: Profile
    style: Style
    form: Form
    midi: pretty_midi.PrettyMIDI


def build_composition(profile: Profile, style: Style, seed: int) -> Composition:
    """Build one deterministic composition from a single seeded RNG."""

    rng = random.Random(seed)
    form = build_form(profile, style, rng)
    midi = pretty_midi.PrettyMIDI(initial_tempo=form.tempo, resolution=960)
    midi.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
    midi.instruments.append(render_piano(form, style, rng))
    return Composition(profile=profile, style=style, form=form, midi=midi)


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
        "--out",
        required=True,
        help="Output prefix, e.g. out/track -> out/track.mid/.wav/.mp3.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Write MIDI only (useful for fast iteration).",
    )
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
        style = get_style(args.style)
        composition = build_composition(profile, style, args.seed)
        out_prefix = _normalize_out_prefix(args.out)
        midi_path = write_midi(composition, out_prefix.with_suffix(".mid"))
        print(_summary(composition, midi_path))
        if args.no_render:
            return 0

        wav_path = out_prefix.with_suffix(".wav")
        mp3_path = out_prefix.with_suffix(".mp3")
        render_track(midi_path, wav_path, mp3_path, style=style)
        print(f"  wav: {wav_path}")
        print(f"  mp3: {mp3_path}")
        return 0
    except (ProfileError, RenderError, ValueError, OSError) as exc:
        print(f"symphony: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
