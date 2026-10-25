"""Violin: phrase-grammar lead and warm sustained support."""

from __future__ import annotations

import random

import pretty_midi

from symphony.form import Form
from symphony.profile import Profile
from symphony.styles import Style
from symphony.theory import build_chord, nearest_pitch_with_pc
from symphony.variation import VariationPlan
from symphony.melody import render_lead_notes
from symphony.instruments.repo_hook import add_repo_hook

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
            pretty_midi.ControlChange(number=7, value=118, time=0.0),
            pretty_midi.ControlChange(number=10, value=76, time=0.0),
            pretty_midi.ControlChange(number=91, value=int(getattr(style, "strings_send", 0.33) * 127), time=0.0),
        ]
    )
    previous_pitch: int | None = None
    for section in form.sections:
        role = plan.role_for(section.name, "violin")
        if role == "out":
            continue
        first_new = len(instrument.notes)
        if role == "lead":
            previous_pitch = render_lead_notes(
                instrument, form, section, plan, style, "violin",
                previous_pitch=previous_pitch,
            )
        else:
            _write_support(instrument, form, section, rng, style)
        _add_expression(instrument, form, section, style, first_new)
    for section in form.sections:
        add_repo_hook(instrument, form, section, plan, "violin")
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    _trim_same_pitch(instrument.notes)
    instrument.control_changes.sort(key=lambda change: (change.time, change.number))
    return instrument


def _write_support(
    instrument: pretty_midi.Instrument,
    form: Form,
    section,
    rng: random.Random,
    style: Style,
) -> None:
    hold = max(1, section.bars_per_chord)
    for local_bar in range(0, section.bars, hold):
        chord = build_chord(form.key, section.degrees[local_bar])
        target = 63 + section.intensity * 9
        pitch = nearest_pitch_with_pc(
            min(chord.pitch_classes, key=lambda pc: abs(
                nearest_pitch_with_pc(pc, target, VIOLIN_MIN, VIOLIN_MAX) - target
            )),
            target,
            VIOLIN_MIN,
            VIOLIN_MAX,
        )
        beat = (section.start_bar + local_bar) * 4.0
        duration = min(hold * 4.0 - 0.25, (section.bars - local_bar) * 4.0 - 0.25)
        start = beat * form.seconds_per_beat
        velocity = max(28, int(style.velocity_floor + section.intensity * 24))
        instrument.notes.append(
            pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=start,
                end=start + max(0.4, duration * form.seconds_per_beat),
            )
        )


def _add_expression(
    instrument: pretty_midi.Instrument,
    form: Form,
    section,
    style: Style,
    first_new: int,
) -> None:
    if not getattr(style, "expression_swells", True):
        return
    for note in instrument.notes[first_new:]:
        length = note.end - note.start
        if length < 0.30:
            continue
        peak = note.start + length * 0.58
        instrument.control_changes.extend(
            [
                pretty_midi.ControlChange(number=11, value=92, time=note.start),
                pretty_midi.ControlChange(number=11, value=112, time=peak),
                pretty_midi.ControlChange(number=11, value=94, time=max(note.start, note.end - 0.05)),
                pretty_midi.ControlChange(number=1, value=6, time=note.start),
                pretty_midi.ControlChange(number=1, value=38, time=peak),
                pretty_midi.ControlChange(number=1, value=20, time=max(note.start, note.end - 0.05)),
            ]
        )


def _trim_same_pitch(notes: list[pretty_midi.Note]) -> None:
    last_by_pitch: dict[int, pretty_midi.Note] = {}
    for note in notes:
        previous = last_by_pitch.get(note.pitch)
        if previous is not None and previous.end > note.start - 0.02:
            previous.end = max(previous.start + 0.03, note.start - 0.02)
        last_by_pitch[note.pitch] = note
