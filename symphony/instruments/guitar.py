"""Guitar: phrase-grammar lead, soft fingerstyle support, and anthem drive."""

from __future__ import annotations

import random

import pretty_midi

from symphony.form import Form
from symphony.profile import Profile
from symphony.styles import Style
from symphony.theory import MODES, build_chord
from symphony.variation import VariationPlan
from symphony.melody import render_lead_notes
from symphony.instruments.repo_hook import add_repo_hook

GUITAR_MIN, GUITAR_MAX = 40, 76  # E2–E5


def render_guitar(
    form: Form,
    profile: Profile,
    style: Style,
    rng: random.Random,
    plan: VariationPlan,
) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(program=plan.guitar_program, name="Guitar")
    instrument.channel = 4
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=76 if style.name == "lofi" else 88, time=0.0),
            pretty_midi.ControlChange(number=10, value=52, time=0.0),
            pretty_midi.ControlChange(number=91, value=int(getattr(style, "guitar_send", 0.28) * 127), time=0.0),
        ]
    )
    for section in form.sections:
        role = plan.role_for(section.name, "guitar")
        if role == "out":
            continue
        if role == "lead":
            render_lead_notes(instrument, form, section, plan, style, "guitar")
        elif style.comp_style == "driving":
            _write_anthem_rhythm(instrument, form, section, style, plan, rng)
        elif style.comp_style == "ostinato":
            _write_fingerstyle(instrument, form, section, style, plan, rng)
        elif style.name == "lofi":
            _write_lofi(instrument, form, section, style, plan, rng)
        else:
            _write_cinematic(instrument, form, section, style, plan, rng)
    for section in form.sections:
        add_repo_hook(instrument, form, section, plan, "guitar")
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    return instrument


def _write_anthem_rhythm(instrument, form, section, style, plan, rng) -> None:
    for bar in range(section.bars):
        chord = build_chord(form.key, section.degrees[bar])
        root = _pitch(chord.root_pc, 48)
        fifth_pc = chord.pitch_classes[2] if len(chord.pitch_classes) > 2 else chord.root_pc
        fifth = _pitch(fifth_pc, 55)
        bar_beat = (section.start_bar + bar) * 4
        accents = (
            (0.0, 1.0, 2.0, 3.0)
            if section.name == "theme"
            else (0.0, 0.5, 1.5, 2.0, 2.5, 3.5)
        )
        for index, beat in enumerate(accents):
            velocity = 53 + int(section.intensity * 34) + rng.randint(-3, 4)
            duration = 0.45 if beat % 1 else 0.78
            _add_strum(
                instrument, (root, fifth), bar_beat + beat, duration,
                velocity, form, spread=0.010, decay=4,
            )


def _write_cinematic(instrument, form, section, style, plan, rng) -> None:
    """Sparse, rolled arpeggios: space first, colour second."""

    if section.name == "climax" and section.intensity > 0.9:
        beats = (0.0, 2.0, 3.5)
    else:
        beats = (0.0, 3.0)
    for bar in range(section.bars):
        if section.name == "resolution" and bar % 2:
            continue
        chord = build_chord(
            form.key,
            section.degrees[bar],
            seventh=False,
            add9=bool(bar % 3 == 1),
        )
        notes = [
            _pitch(pc, 52 + index * 4)
            for index, pc in enumerate(chord.pitch_classes[:4])
        ]
        bar_beat = (section.start_bar + bar) * 4
        for index, beat in enumerate(beats):
            if (bar + index) % 4 == 3:
                continue  # micro-variation: not every repeat is identical
            velocity = 30 + int(section.intensity * 28) + rng.randint(-2, 3)
            _add_strum(
                instrument,
                tuple(notes[: 2 + (index % 2)]),
                bar_beat + beat,
                duration=1.65 if section.name == "climax" else 1.30,
                velocity=velocity,
                form=form,
                spread=0.014,
                decay=3,
            )


def _write_lofi(instrument, form, section, style, plan, rng) -> None:
    for bar in range(section.bars):
        chord = build_chord(
            form.key,
            section.degrees[bar],
            seventh=True,
            ninth=plan.chord_color_for(section.name) in {"ninth", "eleventh"},
        )
        notes = [_pitch(pc, 52 + index * 3) for index, pc in enumerate(chord.pitch_classes[:4])]
        bar_beat = (section.start_bar + bar) * 4
        for beat in (0.5, 2.5):
            velocity = 28 + int(section.intensity * 25) + rng.randint(-3, 3)
            _add_strum(
                instrument, tuple(notes[:3]), bar_beat + beat, 1.0,
                velocity, form, spread=0.011, decay=2,
            )


def _write_fingerstyle(instrument, form, section, style, plan, rng) -> None:
    """Soft broken chords for contemplative development and resolution."""

    if section.name == "development":
        beats = (0.0, 1.5, 2.5)
    elif section.name == "resolution":
        beats = (0.0, 2.5)
    else:
        beats = (0.0, 2.0)
    for bar in range(section.bars):
        chord = build_chord(form.key, section.degrees[bar], add9=bar % 4 == 2)
        notes = sorted(
            _pitch(pc, 52 + index * 3)
            for index, pc in enumerate(chord.pitch_classes[:4])
        )
        bar_beat = (section.start_bar + bar) * 4
        for index, beat in enumerate(beats):
            if (bar + index) % 5 == 4:
                continue
            pitch = notes[(bar + index) % len(notes)]
            velocity = 26 + int(section.intensity * 18) + rng.randint(-2, 2)
            _add_strum(
                instrument, (pitch,), bar_beat + beat, 1.35,
                velocity, form, spread=0.0, decay=0,
            )


def _add_strum(
    instrument,
    pitches: tuple[int, ...],
    beat: float,
    duration: float,
    velocity: int,
    form: Form,
    *,
    spread: float,
    decay: int,
) -> None:
    start = max(0.0, beat * form.seconds_per_beat)
    for index, pitch in enumerate(sorted(set(pitches))):
        note_start = start + index * spread
        note_velocity = max(1, min(118, velocity - index * decay))
        instrument.notes.append(
            pretty_midi.Note(
                velocity=note_velocity,
                pitch=pitch,
                start=note_start,
                end=note_start + max(0.07, duration * form.seconds_per_beat),
            )
        )


def _scale_pitch(form: Form, degree: int, target: float) -> int:
    octave, scale_degree = divmod(degree, 7)
    pc = (form.key.tonic_pc + MODES[form.key.mode][scale_degree]) % 12
    return _pitch(pc, target + octave * 12)


def _pitch(pitch_class: int, target: float) -> int:
    return min(
        (pitch for pitch in range(GUITAR_MIN, GUITAR_MAX + 1) if pitch % 12 == pitch_class % 12),
        key=lambda pitch: abs(pitch - target),
    )


def _add(instrument, pitch, beat, duration, velocity, form) -> None:
    start = max(0.0, beat * form.seconds_per_beat)
    end = start + max(0.07, duration * form.seconds_per_beat)
    instrument.notes.append(pretty_midi.Note(max(1, min(118, velocity)), pitch, start, end))
