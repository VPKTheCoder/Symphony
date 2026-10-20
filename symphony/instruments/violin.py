"""Module leitmotifs for the violin lead."""

from __future__ import annotations

import math
import random

import pretty_midi

from symphony.form import Form
from symphony.profile import Profile
from symphony.styles import Style
from symphony.theory import MODES, build_chord
from symphony.variation import VariationPlan
from symphony.instruments.motifs import developed_degree, module_bar_spans, module_motif

VIOLIN_MIN = 55  # G3
VIOLIN_MAX = 103


def render_violin(
    form: Form,
    profile: Profile,
    style: Style,
    rng: random.Random,
    plan: VariationPlan,
) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(program=style.violin_program, name="Violin")
    instrument.channel = 3
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=92, time=0.0),
            pretty_midi.ControlChange(number=10, value=76, time=0.0),
            pretty_midi.ControlChange(number=91, value=42, time=0.0),
        ]
    )
    module_lookup = profile.modules_by_name
    for section in form.sections:
        role = plan.role_for(section.name, "violin")
        if role == "out":
            continue
        if role == "support":
            _write_support(instrument, form, section, rng, style)
            continue
        for module, first_bar, end_bar in module_bar_spans(section):
            motif = module_motif(module.name)
            phrase_number = 0
            for phrase_start in range(first_bar, end_bar, 2):
                phrase_bars = min(2, end_bar - phrase_start)
                phrase_base = (section.start_bar + phrase_start) * form.beats_per_bar
                phrase_limit = phrase_bars * form.beats_per_bar
                current_module = module_lookup[module.name]
                for event_index, event in enumerate(motif):
                    if event.beat >= phrase_limit:
                        continue
                    degree = developed_degree(
                        event.degree, plan.motif_treatment or "repeat", phrase_number
                    )
                    if degree is None:
                        continue
                    beat_in_section = phrase_start * 4 + event.beat
                    bar = min(section.bars - 1, int(beat_in_section // 4))
                    chord = build_chord(form.key, section.degrees[bar])
                    target = _target_register(section.name, section.intensity, current_module.complexity, degree)
                    if event.beat % 4 in (0.0, 2.0):
                        pitch = _chord_pitch(chord.pitch_classes, target)
                    else:
                        pitch = _scale_pitch(form, degree, target)
                    absolute_beat = phrase_base + event.beat
                    if current_module.todo_count and event.beat >= 7.0 and phrase_number % 2 == 1:
                        continue
                    duration = min(event.duration, phrase_limit - event.beat - 0.05)
                    if duration <= 0.06:
                        continue
                    velocity = _velocity(style, section.intensity, event.beat, rng)
                    if current_module.unsafe_count > 0 and event_index == len(motif) // 2:
                        _tremolo(
                            instrument, pitch, absolute_beat, duration,
                            velocity, form,
                        )
                    else:
                        _add_note(instrument, pitch, absolute_beat, duration, velocity, form, style, rng)
                if (plan.motif_treatment == "extend" and phrase_number % 2 == 1
                        and phrase_limit >= 4):
                    last = motif[-1]
                    pitch = _scale_pitch(form, last.degree + 1, 79 + section.intensity * 8)
                    _add_note(
                        instrument, pitch, phrase_base + phrase_limit - 0.48,
                        0.38, _velocity(style, section.intensity, 3.5, rng),
                        form, style, rng,
                    )
                phrase_number += 1
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    return instrument


def _write_support(
    instrument: pretty_midi.Instrument,
    form: Form,
    section,
    rng: random.Random,
    style: Style,
) -> None:
    for bar in range(0, section.bars, 2):
        chord = build_chord(form.key, section.degrees[bar])
        pitch = _chord_pitch(chord.pitch_classes, 64 + section.intensity * 10)
        beat = (section.start_bar + bar) * 4.0 + 1.0
        _add_note(
            instrument, pitch, beat, min(2.3, (section.bars - bar) * 4 - 1.1),
            max(30, _velocity(style, section.intensity, 1.0, rng) - 18),
            form, style, rng,
        )


def _scale_pitch(form: Form, degree: int, target: float) -> int:
    intervals = MODES[form.key.mode]
    octave, scale_degree = divmod(degree, 7)
    pc = (form.key.tonic_pc + intervals[scale_degree]) % 12
    target = min(VIOLIN_MAX, max(VIOLIN_MIN, target + octave * 12))
    return min(
        (pitch for pitch in range(VIOLIN_MIN, VIOLIN_MAX + 1) if pitch % 12 == pc),
        key=lambda pitch: abs(pitch - target),
    )


def _chord_pitch(pitch_classes: tuple[int, ...], target: float) -> int:
    pcs = set(pitch_classes)
    return min(
        (pitch for pitch in range(VIOLIN_MIN, VIOLIN_MAX + 1) if pitch % 12 in pcs),
        key=lambda pitch: abs(pitch - target),
    )


def _target_register(section: str, intensity: float, complexity: float, degree: int) -> float:
    base = {"theme": 69, "development": 73, "climax": 82, "resolution": 71}.get(section, 67)
    return max(VIOLIN_MIN, min(96, base + intensity * 3 + complexity * 5 + degree * 1.3))


def _velocity(style: Style, intensity: float, beat: float, rng: random.Random) -> int:
    base = style.velocity_floor + (style.velocity_ceiling - style.velocity_floor) * intensity ** style.velocity_curve
    accent = 9 if beat % 4 == 0 else 3 if beat % 2 == 0 else -2
    return max(26, min(116, int(base + accent + rng.randint(-3, 3))))


def _add_note(
    instrument: pretty_midi.Instrument,
    pitch: int,
    beat: float,
    duration: float,
    velocity: int,
    form: Form,
    style: Style,
    rng: random.Random,
) -> None:
    jitter = rng.uniform(-0.008, 0.008) if style.name == "anthem" else rng.uniform(-0.014, 0.014)
    start = max(0.0, beat * form.seconds_per_beat + jitter)
    end = start + max(0.08, duration * form.seconds_per_beat)
    instrument.notes.append(pretty_midi.Note(velocity, pitch, start, end))


def _tremolo(
    instrument: pretty_midi.Instrument,
    pitch: int,
    beat: float,
    duration: float,
    velocity: int,
    form: Form,
) -> None:
    count = 5
    step = duration / count
    for index in range(count):
        start = (beat + index * step) * form.seconds_per_beat
        end = start + max(0.05, step * form.seconds_per_beat * 0.84)
        instrument.notes.append(
            pretty_midi.Note(max(1, velocity - (index % 2) * 5), pitch, start, end)
        )
