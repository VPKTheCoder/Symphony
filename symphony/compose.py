"""Command-line composer: profile + style + seed -> MIDI, WAV and MP3."""

from __future__ import annotations

import argparse
import random
import sys
import subprocess
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
from symphony.analyze import analyze_repository, format_explanation, format_summary, resolve_repository, write_profile
from symphony.render import RenderError, render_track
from symphony.styles import STYLES, Style, get_style
from symphony.variation import VariationPlan, sample_variation_plan
from symphony.timeline import build_timeline, format_listening_guide, write_timeline
from symphony.identity import profile_fingerprint, variation_seed
from symphony.theory import MODES

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
        base_seed = variation_seed(profile, style.name, seed)
        effective_seed = base_seed if attempt == 0 else base_seed + attempt * 1_000_003
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
    if plan.signature_id == "sprawl":
        climax = next(section for section in form.sections if section.name == "climax")
        bar_seconds = form.seconds_per_beat * 4.0
        start_time = climax.start_bar * bar_seconds
        end_time = climax.end_bar * bar_seconds
        lanes = {"Piano": (49, 108), "Bass": (24, 48), "Violin": (55, 103), "Guitar": (40, 76)}
        for instrument in midi.instruments:
            if instrument.is_drum:
                continue
            low, high = lanes[instrument.name]
            for note in instrument.notes:
                if start_time <= note.start < end_time:
                    shifted = note.pitch + 2
                    if shifted > high:
                        shifted -= 12
                    if shifted < low:
                        shifted += 12
                    note.pitch = shifted
    _quantize_generated_notes(midi, form, plan)
    _apply_meter(midi, plan.meter, form.tempo)
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


def _apply_meter(midi: pretty_midi.PrettyMIDI, meter: tuple[int, int], tempo: int) -> None:
    """Warp each generated four-beat bar into its selected curated meter."""

    numerator, denominator = meter
    target_beats = numerator * 4.0 / denominator
    ratio = target_beats / 4.0
    seconds_per_beat = 60.0 / tempo

    def warp(seconds: float) -> float:
        beat = max(0.0, seconds / seconds_per_beat)
        bar = int(beat // 4.0)
        within = beat - bar * 4.0
        return (bar * target_beats + within * ratio) * seconds_per_beat

    if meter != (4, 4):
        for instrument in midi.instruments:
            for note in instrument.notes:
                note.start = warp(note.start)
                note.end = max(note.start + 0.01, warp(note.end))
            for event in (*instrument.control_changes, *instrument.pitch_bends):
                event.time = warp(event.time)
    midi.time_signature_changes = [
        pretty_midi.TimeSignature(numerator, denominator, 0.0)
    ]


def _quantize_generated_notes(midi: pretty_midi.PrettyMIDI, form: Form, plan: VariationPlan) -> None:
    """Keep every generated pitched note in the active section's curated scale."""
    base_scale = {(form.key.tonic_pc + interval) % 12 for interval in MODES[form.key.mode]}
    lanes = {"Piano": (49, 108), "Bass": (24, 48), "Violin": (55, 103), "Guitar": (40, 76)}
    bar_seconds = form.seconds_per_beat * 4.0
    climax = next(section for section in form.sections if section.name == "climax")
    climax_start = climax.start_bar * bar_seconds
    climax_end = climax.end_bar * bar_seconds
    for instrument in midi.instruments:
        if instrument.is_drum:
            continue
        low, high = lanes[instrument.name]
        for note in instrument.notes:
            scale = base_scale
            if plan.signature_id == "sprawl" and climax_start <= note.start < climax_end:
                scale = {(pitch + 2) % 12 for pitch in base_scale}
            if note.pitch % 12 not in scale:
                note.pitch = min(
                    (candidate for candidate in range(low, high + 1) if candidate % 12 in scale),
                    key=lambda candidate: (abs(candidate - note.pitch), candidate),
                )


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
        f"  plan (variation index {composition.seed}, resample {composition.variation_attempt}): "
        f"{composition.variation_plan.summary()}\n"
        f"  repo fingerprint: {profile_fingerprint(composition.profile)}\n"
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
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--profile", help="Path to a profile JSON file.")
    source_group.add_argument("--repo", help="Analyze a local Rust repo path or Git URL before composing.")
    parser.add_argument(
        "--style",
        required=True,
        choices=sorted(STYLES),
        help="Musical style.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Variation index (default: 0); the base seed is derived from repository identity.")
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
    parser.add_argument("--entry", help="Analyzer entry module (defaults to main, then lib).")
    parser.add_argument("--lcov", help="LCOV report for real coverage instead of the test proxy.")
    parser.add_argument("--explain", action="store_true", help="Explain each module metric's musical mapping.")
    args = parser.parse_args(argv)

    try:
        out_prefix = _normalize_out_prefix(args.out)
        analyzed_profile = None
        if args.repo:
            repository = resolve_repository(args.repo)
            analyzed_profile = analyze_repository(
                repository,
                name=out_prefix.name,
                entry=args.entry,
                lcov=args.lcov,
            )
            profile_path = write_profile(
                analyzed_profile,
                out_prefix.with_name(out_prefix.name + ".profile.json"),
            )
            print(format_summary(analyzed_profile))
            print(f"  profile: {profile_path}")
            profile = load_profile(profile_path)
        else:
            if args.entry or args.lcov:
                raise ValueError("--entry and --lcov are only used with --repo.")
            profile = load_profile(args.profile)
        style = get_style(args.style)
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
            timeline = build_timeline(composition)
            timeline_path = write_timeline(composition, prefix)
            print(f"  timeline: {timeline_path}")
            if args.explain:
                if analyzed_profile is None:
                    analyzed_profile = {
                        "name": profile.name,
                        "global": {
                            "total_loc": profile.global_metrics.total_loc,
                            "unsafe_ratio": profile.global_metrics.unsafe_ratio,
                            "test_coverage": profile.global_metrics.test_coverage,
                            "avg_complexity": profile.global_metrics.avg_complexity,
                        },
                        "coverage_source": profile.coverage_source or "profile",
                        "modules": [
                            {
                                "name": module.name,
                                "loc": module.loc,
                                "complexity": module.complexity,
                                "unsafe_count": module.unsafe_count,
                                "depends_on": list(module.depends_on),
                                "todo_count": module.todo_count,
                                "test_coverage": module.test_coverage,
                                "depended_by_count": module.depended_by_count,
                            }
                            for module in profile.modules
                        ],
                    }
                print(format_explanation(analyzed_profile))
            if args.no_render:
                print(format_listening_guide(timeline))
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
            print(format_listening_guide(timeline))
        return 0
    except (ProfileError, RenderError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"symphony: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
