"""Objective musical-quality scoring for composed tracks.

The score is deterministic: it reads only the composition's form, variation
plan and rendered MIDI note data, and never samples a random number.  Six
independent dimensions are measured, each clamped to 0..1:

* phrase grammar -- the lead lines' step counts, leap preparation/recovery and
  strong-beat chord tones;
* voice leading -- rank-to-rank movement between successive piano chord attacks;
* density balance -- sounding-part coverage, lead/support balance and whether
  the actual activity follows the dramatic intensity arc;
* rest placement -- cadence bars stay populated, support rests fall inside
  phrases, and the lead keeps some air;
* range shape -- phrase spans, the overall melodic span, and a climax apex;
* repetition -- hook recurrence balanced against progression/rhythm variety.

The weighted total is reported on a 0-100 scale.  ``--best-of`` in
``symphony.compose`` uses the unrounded total, with ties resolved by the lower
candidate index.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

from symphony.melody import (
    MelodyEvent,
    MelodyQuality,
    build_lead_line,
    melody_quality,
    plan_pitches,
)
from symphony.space import phrase_rest_bar
from symphony.styles import STYLES, get_style
from symphony.theory import MODES

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from symphony.compose import Composition
    from symphony.form import Form, SectionPlan
    from symphony.profile import Profile
    from symphony.styles import Style
    from symphony.variation import VariationPlan


COMPONENT_WEIGHTS: dict[str, float] = {
    "phrase_grammar": 0.32,
    "voice_leading": 0.20,
    "density_balance": 0.18,
    "rest_placement": 0.10,
    "range_shape": 0.10,
    "repetition": 0.10,
}

_INSTRUMENT_NAMES = {
    "piano": "Piano",
    "bass": "Bass",
    "drums": "Drum Kit",
    "violin": "Violin",
    "guitar": "Guitar",
}

_LEAD_PARTS = frozenset({"violin", "guitar", "piano"})


@dataclass(frozen=True)
class ScoreReport:
    """Measured quality dimensions plus their underlying raw statistics."""

    phrase_grammar: float
    voice_leading: float
    density_balance: float
    rest_placement: float
    range_shape: float
    repetition: float
    details: dict[str, float] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        return 100.0 * sum(
            weight * getattr(self, name)
            for name, weight in COMPONENT_WEIGHTS.items()
        )

    def to_dict(self) -> dict:
        return {
            "overall": round(self.overall, 2),
            "components": {
                name: round(getattr(self, name), 4)
                for name in COMPONENT_WEIGHTS
            },
            "weights": dict(COMPONENT_WEIGHTS),
            "details": {
                name: round(value, 4) for name, value in sorted(self.details.items())
            },
        }

    def format(self) -> str:
        lines = [f"Score: {self.overall:.2f} / 100"]
        for name, weight in COMPONENT_WEIGHTS.items():
            label = name.replace("_", " ")
            lines.append(
                f"  {label:16} {getattr(self, name):.3f}  (weight {weight:.2f})"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class _LeadObservation:
    section: "SectionPlan"
    part: str
    events: tuple[MelodyEvent, ...]
    pitches: tuple[int, ...]
    quality: MelodyQuality


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _band(value: float, low: float, high: float, softness: float) -> float:
    """1 inside [low, high], easing to 0 over *softness* outside the band."""

    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return _clamp(1.0 - distance / max(1e-9, softness))


def _bar_seconds(form: "Form") -> float:
    return form.meter_beats_per_bar * form.seconds_per_beat


def _instrument_map(composition: "Composition") -> dict[str, object]:
    return {instrument.name: instrument for instrument in composition.midi.instruments}


def _section_window(
    form: "Form", section: "SectionPlan"
) -> tuple[float, float]:
    bar = _bar_seconds(form)
    return section.start_bar * bar, section.end_bar * bar


def _note_starts(
    instrument: object,
    start: float,
    end: float,
) -> list[float]:
    return [
        note.start
        for note in instrument.notes
        if start <= note.start < end
    ]


def _lead_observations(composition: "Composition") -> tuple[_LeadObservation, ...]:
    form = composition.form
    plan = composition.variation_plan
    style = composition.style
    observations: list[_LeadObservation] = []
    for section in form.sections:
        for part in plan.arrangement_matrix.leads(section.name):
            if part not in _LEAD_PARTS:
                continue
            events = build_lead_line(form, section, plan, style, part)
            if not events:
                continue
            pitches = tuple(plan_pitches(form, section, events, part, style))
            quality = melody_quality(
                events,
                form,
                part,
                section=section,
                total_beats=section.bars * 4.0,
                style=style,
            )
            observations.append(
                _LeadObservation(
                    section=section,
                    part=part,
                    events=events,
                    pitches=pitches,
                    quality=quality,
                )
            )
    return tuple(observations)


def _phrase_grammar(
    observations: tuple[_LeadObservation, ...],
) -> tuple[float, dict[str, float]]:
    rankings = []
    details: dict[str, float] = {}
    fields = (
        ("step_ratio", 0.34),
        ("degree_step_ratio", 0.16),
        ("prepared_ratio", 0.18),
        ("leap_recovery", 0.18),
        ("strong_chord_ratio", 0.09),
    )
    for observation in observations:
        quality = observation.quality
        score = sum(
            weight * getattr(quality, name) for name, weight in fields
        )
        score += 0.05 * (1.0 if quality.clean else 0.0)
        rankings.append(score)
    for name, _weight in fields:
        details[f"phrase_{name}"] = _mean(
            [getattr(item.quality, name) for item in observations]
        )
    details["phrase_clean_ratio"] = _mean(
        [1.0 if item.quality.clean else 0.0 for item in observations]
    )
    details["phrase_rest_ratio"] = _mean(
        [item.quality.rest_ratio for item in observations]
    )
    return _mean(rankings), details


def _chord_clusters(
    notes: Sequence[object],
    tolerance: float = 0.09,
) -> list[tuple[float, list[int]]]:
    clusters: list[tuple[float, list[int]]] = []
    for note in sorted(notes, key=lambda item: (item.start, item.pitch)):
        if clusters and note.start - clusters[-1][0] <= tolerance:
            clusters[-1][1].append(note.pitch)
        else:
            clusters.append((note.start, [note.pitch]))
    result = []
    for start, pitches in clusters:
        distinct = sorted(set(pitches))
        if len(distinct) >= 2:
            result.append((start, distinct))
    return result


def _voice_leading(composition: "Composition") -> tuple[float, dict[str, float]]:
    piano = _instrument_map(composition).get("Piano")
    if piano is None:
        return 0.5, {"voice_movements": 0.0}
    chords = [pitches for _start, pitches in _chord_clusters(piano.notes)]
    movements: list[int] = []
    spacing: list[int] = []
    for chord in chords:
        spacing.extend(right - left for left, right in zip(chord, chord[1:]))
    for left, right in zip(chords, chords[1:]):
        pairs = min(len(left), len(right))
        movements.extend(
            abs(right[index] - left[index]) for index in range(pairs)
        )
    if not movements:
        return 0.5, {"voice_movements": 0.0}
    smooth = _mean(
        [
            1.0 if movement <= 2 else
            0.70 if movement <= 5 else
            0.35 if movement <= 9 else
            0.0
            for movement in movements
        ]
    )
    large_ratio = sum(1 for movement in movements if movement > 12) / len(movements)
    spacing_score = _mean(
        [1.0 if gap <= 12 else _clamp(1.0 - (gap - 12) / 8.0) for gap in spacing]
    )
    score = 0.70 * smooth + 0.15 * (1.0 - large_ratio) + 0.15 * spacing_score
    details = {
        "voice_chords": float(len(chords)),
        "voice_movements": float(len(movements)),
        "voice_mean_movement": _mean([float(value) for value in movements]),
        "voice_smooth_ratio": smooth,
        "voice_large_ratio": large_ratio,
        "voice_spacing": spacing_score,
    }
    return score, details


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left, right)
    )
    left_var = sum((a - left_mean) ** 2 for a in left)
    right_var = sum((b - right_mean) ** 2 for b in right)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator > 0.0 else 0.0


def _density_balance(composition: "Composition") -> tuple[float, dict[str, float]]:
    form = composition.form
    plan = composition.variation_plan
    instruments = _instrument_map(composition)
    coverage_values = []
    balance_values = []
    densities = []
    for section in form.sections:
        start, end = _section_window(form, section)
        active = plan.arrangement_matrix.active(section.name)
        counts = {
            part: len(_note_starts(instruments[_INSTRUMENT_NAMES[part]], start, end))
            for part in active
            if _INSTRUMENT_NAMES[part] in instruments
        }
        pitched = [part for part in active if part != "drums"]
        sounding = sum(1 for part in pitched if counts.get(part, 0) > 0)
        coverage_values.append(sounding / max(1, len(pitched)))
        leads = plan.arrangement_matrix.leads(section.name)
        lead = leads[0] if leads else ""
        if lead and lead != "piano":
            support = sum(
                counts.get(part, 0)
                for part in pitched
                if part != lead
            )
            total = counts.get(lead, 0) + support
            ratio = counts.get(lead, 0) / total if total else 0.0
            balance_values.append(_band(ratio, 0.05, 0.40, 0.15))
        densities.append(sum(counts.values()) / max(1, section.bars))
    coverage = _mean(coverage_values)
    balance = _mean(balance_values) if balance_values else 1.0
    intensities = [section.intensity for section in form.sections]
    correlation = _pearson(densities, intensities)
    arc = _clamp((correlation + 1.0) / 2.0)
    score = 0.45 * coverage + 0.30 * balance + 0.25 * arc
    details = {
        "density_coverage": coverage,
        "density_lead_balance": balance,
        "density_intensity_correlation": correlation,
    }
    return score, details


def _rest_placement(
    composition: "Composition",
    observations: tuple[_LeadObservation, ...],
) -> tuple[float, dict[str, float]]:
    form = composition.form
    plan = composition.variation_plan
    style = composition.style
    instruments = _instrument_map(composition)
    bar = _bar_seconds(form)
    cadence_values = []
    expected = 0
    silent = 0
    positions: set[int] = set()
    for section in form.sections:
        section_start, section_end = _section_window(form, section)
        final_start = section_end - bar
        active = [
            part
            for part in plan.arrangement_matrix.active(section.name)
            if part != "drums" and _INSTRUMENT_NAMES[part] in instruments
        ]
        present = 0
        for part in active:
            starts = _note_starts(
                instruments[_INSTRUMENT_NAMES[part]], final_start, section_end + 0.25
            )
            if starts:
                present += 1
        cadence_values.append(present / max(1, len(active)))
        for part in ("bass", "guitar", "drums"):
            if plan.role_for(section.name, part) != "support":
                continue
            instrument = instruments.get(_INSTRUMENT_NAMES[part])
            if instrument is None:
                continue
            for local_bar in range(section.bars):
                if not phrase_rest_bar(style, section, local_bar, part):
                    continue
                expected += 1
                rest_start = section_start + local_bar * bar
                starts = _note_starts(instrument, rest_start, rest_start + bar)
                if not starts:
                    silent += 1
                positions.add(local_bar % 4)
    hygiene = silent / expected if expected else 1.0
    diversity = _clamp(len(positions) / 2.0) if expected else 1.0
    # Lead air is measured from the phrase engine, not the final support rests.
    air = _mean(
        [_band(item.quality.rest_ratio, 0.08, 0.45, 0.25) for item in observations]
    )
    cadence = _mean(cadence_values)
    score = 0.35 * cadence + 0.30 * hygiene + 0.20 * diversity + 0.15 * air
    details = {
        "rest_cadence_ratio": cadence,
        "rest_hygiene": hygiene,
        "rest_expected_windows": float(expected),
        "rest_positions": float(len(positions)),
        "rest_lead_air": air,
    }
    return score, details


def _range_shape(
    observations: tuple[_LeadObservation, ...],
) -> tuple[float, dict[str, float]]:
    if not observations:
        return 0.0, {"range_section_fit": 0.0, "range_global_span": 0.0}
    section_spans = [
        max(item.pitches) - min(item.pitches)
        for item in observations
        if item.pitches
    ]
    section_fit = _mean([_band(span, 5, 22, 7) for span in section_spans])
    all_pitches = [pitch for item in observations for pitch in item.pitches]
    global_span = max(all_pitches) - min(all_pitches)
    global_fit = _band(global_span, 16, 38, 10)
    highest = max(
        observations,
        key=lambda item: max(item.pitches) if item.pitches else -1,
    )
    apex = 1.0 if highest.section.name == "climax" else 0.0
    score = 0.50 * section_fit + 0.30 * global_fit + 0.20 * apex
    details = {
        "range_section_fit": section_fit,
        "range_mean_section_span": _mean([float(span) for span in section_spans]),
        "range_global_span": float(global_span),
        "range_climax_apex": apex,
    }
    return score, details


def _repetition(
    composition: "Composition",
    observations: tuple[_LeadObservation, ...],
) -> tuple[float, dict[str, float]]:
    plan = composition.variation_plan
    hook_sections = {
        item.section.name
        for item in observations
        if any(event.is_hook for event in item.events)
    }
    progressions = {
        plan.progression_id_for(section.name) for section in composition.form.sections
    }
    rhythms = {
        plan.pattern_for(section.name) for section in composition.form.sections
    }
    adjacent = 0
    repeats = 0
    for item in observations:
        for left, right in zip(item.pitches, item.pitches[1:]):
            adjacent += 1
            if left == right:
                repeats += 1
    repeat_ratio = repeats / max(1, adjacent)
    hook = _clamp((len(hook_sections) - 2) / 2.0)
    progression_variety = _clamp((len(progressions) - 3) / 2.0)
    rhythm_variety = _clamp((len(rhythms) - 2) / 2.0)
    repeat_penalty = _clamp((repeat_ratio - 0.20) / 0.30)
    score = (
        0.40 * hook
        + 0.25 * progression_variety
        + 0.25 * rhythm_variety
        + 0.10 * (1.0 - repeat_penalty)
    )
    details = {
        "repetition_hook_sections": float(len(hook_sections)),
        "repetition_progressions": float(len(progressions)),
        "repetition_rhythms": float(len(rhythms)),
        "repetition_adjacent_pitch_ratio": repeat_ratio,
    }
    return score, details


def score_composition(composition: "Composition") -> ScoreReport:
    """Return the deterministic six-dimension score for one composition."""

    observations = _lead_observations(composition)
    phrase, phrase_details = _phrase_grammar(observations)
    voice, voice_details = _voice_leading(composition)
    density, density_details = _density_balance(composition)
    rests, rest_details = _rest_placement(composition, observations)
    span, range_details = _range_shape(observations)
    repetition, repetition_details = _repetition(composition, observations)
    details = {
        **phrase_details,
        **voice_details,
        **density_details,
        **rest_details,
        **range_details,
        **repetition_details,
    }
    return ScoreReport(
        phrase_grammar=_clamp(phrase),
        voice_leading=_clamp(voice),
        density_balance=_clamp(density),
        rest_placement=_clamp(rests),
        range_shape=_clamp(span),
        repetition=_clamp(repetition),
        details=details,
    )


def _build_for_cli(profile_path: str, style_name: str, seed: int) -> "Composition":
    # Imported lazily so ``symphony.compose`` can import this module at top level.
    from symphony.compose import build_composition
    from symphony.profile import load_profile

    profile = load_profile(profile_path)
    return build_composition(profile, get_style(style_name), seed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m symphony.score",
        description="Score a composed profile for objective musical quality.",
    )
    parser.add_argument("--profile", required=True, help="Path to a profile JSON file.")
    parser.add_argument(
        "--style",
        required=True,
        choices=sorted(STYLES),
        help="Musical style.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Variation index (default: 0).")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full score report as JSON.",
    )
    args = parser.parse_args(argv)
    try:
        composition = _build_for_cli(args.profile, args.style, args.seed)
        report = score_composition(composition)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            form = composition.form
            print(
                f"{composition.profile.name} / {composition.style.name} / "
                f"seed {composition.seed}: {form.key.label}, {form.tempo} BPM"
            )
            print(report.format())
            print("Details")
            for name, value in sorted(report.details.items()):
                print(f"  {name:34} {value:.4f}")
        return 0
    except (ValueError, OSError) as exc:
        print(f"symphony-score: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
