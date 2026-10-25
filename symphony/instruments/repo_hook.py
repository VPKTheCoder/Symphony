"""Repository signature gestures layered on top of the phrase-grammar hook.

The main hook is no longer overlaid on every instrument: the melody engine owns
it.  This module only adds the one audible, repository-specific gesture that the
timeline names, plus the pedal-point signature.  The gestures stay short and
quiet so they read as colour rather than a second, unrelated tune.
"""

from __future__ import annotations

import pretty_midi

from symphony.form import Form, SectionPlan
from symphony.theory import build_chord
from symphony.variation import VariationPlan


def add_repo_hook(
    instrument: pretty_midi.Instrument,
    form: Form,
    section: SectionPlan,
    plan: VariationPlan,
    part: str,
) -> None:
    """Backwards-compatible entry point for the signature gesture."""

    add_signature_gesture(instrument, form, section, plan, part)


def add_signature_gesture(
    instrument: pretty_midi.Instrument,
    form: Form,
    section: SectionPlan,
    plan: VariationPlan,
    part: str,
) -> None:
    if part == "bass" and plan.signature_id == "hub":
        _pedal(instrument, form, section)
    elif part == "violin" and plan.signature_id == "unsafe":
        _unsafe_tremolo(instrument, form, section)
    elif part in {"violin", "guitar"} and plan.signature_id == "iterator":
        _iterator_run(instrument, form, section)
    elif part == "drums" and plan.signature_id == "complexity":
        _complexity_pulse(instrument, form, section)
    elif part == "violin" and plan.signature_id == "clean" and section.name == "resolution":
        _resolved_glow(instrument, form, section)


def _pedal(instrument: pretty_midi.Instrument, form: Form, section: SectionPlan) -> None:
    if section.name in {"intro", "outro"}:
        return
    tonic = form.key.tonic_pc
    pitch = min(
        (candidate for candidate in range(24, 49) if candidate % 12 == tonic),
        key=lambda candidate: abs(candidate - 31),
    )
    for bar in range(0, section.bars, 2):
        beat = (section.start_bar + bar) * 4.0
        start = beat * form.seconds_per_beat
        end = min(
            (beat + min(7.8, (section.bars - bar) * 4.0 - 0.2)) * form.seconds_per_beat,
            form.estimated_seconds,
        )
        instrument.notes.append(
            pretty_midi.Note(50, pitch, start, max(start + 0.05, end))
        )


def _unsafe_tremolo(instrument: pretty_midi.Instrument, form: Form, section: SectionPlan) -> None:
    if not section.modules:
        return
    unsafe = sum(module.unsafe_count for module in section.modules)
    if unsafe <= 0:
        return
    # Only the section carrying the most unsafe weight gets the gesture.
    candidates = [
        candidate for candidate in form.sections
        if sum(module.unsafe_count for module in candidate.modules) > 0
    ]
    if not candidates:
        return
    hottest = max(candidates, key=lambda candidate: sum(module.unsafe_count for module in candidate.modules))
    if section.name != hottest.name:
        return
    scale_pcs = sorted({(form.key.tonic_pc + interval) % 12 for interval in form.key.intervals})
    pair = next(
        ((left, right) for left in scale_pcs for right in scale_pcs if (right - left) % 12 == 6),
        None,
    )
    if pair is None:
        return
    local_bar = min(section.bars - 1, section.bars // 2)
    beat = (section.start_bar + local_bar) * 4.0 + 2.0
    for index in range(6):
        pitch_class = pair[index % 2]
        pitch = min(
            (pitch for pitch in range(55, 104) if pitch % 12 == pitch_class),
            key=lambda value: abs(value - 71),
        )
        start = (beat + index * 0.25) * form.seconds_per_beat
        instrument.notes.append(
            pretty_midi.Note(58 - (index % 2) * 4, pitch, start, start + 0.18 * form.seconds_per_beat)
        )


def _iterator_run(instrument: pretty_midi.Instrument, form: Form, section: SectionPlan) -> None:
    if section.name not in {"development", "climax"} or not section.modules:
        return
    # One flowing scalar run per section, derived from the mode rather than the
    # old shared hook so it sounds like an ornament on the phrase.
    low, high = (55, 103) if instrument.name == "Violin" else (40, 76)
    start_beat = (section.start_bar + max(0, section.bars // 2)) * 4.0 + 2.0
    scale = form.key.intervals
    for index in range(6):
        degree = index + 2
        octave, step = divmod(degree, 7)
        pc = (form.key.tonic_pc + scale[step]) % 12
        pitch = min(
            (candidate for candidate in range(low, high + 1) if candidate % 12 == pc),
            key=lambda value: abs(value - (64 + index * 2)),
        )
        start = (start_beat + index * 0.25) * form.seconds_per_beat
        instrument.notes.append(
            pretty_midi.Note(56, pitch, start, start + 0.19 * form.seconds_per_beat)
        )


def _complexity_pulse(instrument: pretty_midi.Instrument, form: Form, section: SectionPlan) -> None:
    if section.name != "climax":
        return
    for bar in range(section.bars):
        bar_start = (section.start_bar + bar) * 4.0
        for index in range(4):
            start = (bar_start + 0.5 + index) * form.seconds_per_beat
            instrument.notes.append(
                pretty_midi.Note(38 + index * 2, 42, start, start + 0.09 * form.seconds_per_beat)
            )


def _resolved_glow(instrument: pretty_midi.Instrument, form: Form, section: SectionPlan) -> None:
    # A quiet tonic glow under the cadence, deliberately below the climax apex.
    tonic = form.key.tonic_pc
    pitch = min(
        (candidate for candidate in range(60, 85) if candidate % 12 == tonic),
        key=lambda candidate: abs(candidate - 76),
    )
    beat = (section.start_bar + max(0, section.bars - 2)) * 4.0
    start = beat * form.seconds_per_beat
    instrument.notes.append(
        pretty_midi.Note(52, pitch, start, start + 3.2 * form.seconds_per_beat)
    )
