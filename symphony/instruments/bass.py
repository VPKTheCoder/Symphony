"""Scale-safe bass part driven by the shared VariationPlan."""

from __future__ import annotations

import random

import pretty_midi

from symphony.form import Form
from symphony.styles import BassPattern, Style
from symphony.theory import MODES, build_chord
from symphony.variation import VariationPlan

PROGRAM_ACOUSTIC_BASS = 32
BASS_MIN, BASS_MAX = 24, 48  # C1–C3


def render_bass(
    form: Form, style: Style, profile_metrics, rng: random.Random, plan: VariationPlan
) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(program=PROGRAM_ACOUSTIC_BASS, name="Bass")
    instrument.channel = 1
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=100, time=0.0),
            pretty_midi.ControlChange(number=10, value=64, time=0.0),
            pretty_midi.ControlChange(number=91, value=18, time=0.0),
        ]
    )
    pattern = next(item for item in style.bass_patterns if item.name == plan.bass_pattern)
    scale_pcs = {(form.key.tonic_pc + degree) % 12 for degree in MODES[form.key.mode]}
    dependencies = [module.depended_by_count for module in profile_metrics.modules]
    dependent_load = sum(dependencies) / max(1, len(dependencies))
    deep = dependent_load >= 1.0

    for section in form.sections:
        if plan.role_for(section.name, "bass") == "out":
            continue
        beats = pattern.lead_beats if plan.role_for(section.name, "bass") == "lead" else pattern.support_beats
        for local_bar in range(section.bars):
            todo_rest = (
                local_bar == min(1, section.bars - 1)
                and any(module.todo_count > 0 for module in section.modules)
            )
            chord = build_chord(form.key, section.degrees[local_bar])
            root_pc = chord.root_pc % 12
            target = (29 if deep else 35) + (section.intensity > 0.8) * 2
            root = min(
                (pitch for pitch in range(BASS_MIN, BASS_MAX + 1) if pitch % 12 == root_pc),
                key=lambda pitch: abs(pitch - target),
            )
            next_root_pc = build_chord(
                form.key, section.degrees[(local_bar + 1) % section.bars]
            ).root_pc % 12
            bar_start = (section.start_bar + local_bar) * form.beats_per_bar
            for index, beat in enumerate(beats):
                if todo_rest and beat < 1.0:
                    continue
                absolute_beat = bar_start + beat
                pitch = root
                if index and pattern.passing_tone:
                    # A curated diatonic approach tone, placed between chord
                    # roots and never outside the selected mode.
                    direction = 1 if (next_root_pc - root_pc) % 12 < 6 else -1
                    candidates = [
                        value for value in range(BASS_MIN, BASS_MAX + 1)
                        if value % 12 in scale_pcs
                        and (value - root) * direction > 0
                        and abs(value - root) <= 5
                    ]
                    if candidates:
                        pitch = min(candidates, key=lambda value: abs(value - root - direction * 2))
                duration = pattern.duration
                if deep and index == 0:
                    duration = max(duration, 3.4)
                if section.name in {"intro", "outro"}:
                    duration = max(duration, 2.8)
                velocity = int(58 + section.intensity * 36 + rng.randint(-3, 3))
                start = max(0.0, absolute_beat * form.seconds_per_beat)
                end = min(
                    start + duration * form.seconds_per_beat,
                    (bar_start + 4.0) * form.seconds_per_beat - 0.015,
                )
                if end > start:
                    instrument.notes.append(
                        pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
                    )
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    return instrument
