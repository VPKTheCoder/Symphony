"""Style-specific guitar comping and lead answers."""

from __future__ import annotations

import random

import pretty_midi

from symphony.form import Form
from symphony.profile import Profile
from symphony.styles import Style
from symphony.theory import MODES, build_chord
from symphony.variation import VariationPlan
from symphony.instruments.motifs import developed_degree, module_bar_spans, module_motif

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
            pretty_midi.ControlChange(number=91, value=36 if style.name != "lofi" else 24, time=0.0),
        ]
    )
    for section in form.sections:
        role = plan.role_for(section.name, "guitar")
        if role == "out":
            continue
        if role == "lead":
            _write_lead(instrument, form, section, style, rng, plan)
        elif style.name == "cinematic":
            if section.name not in {"development", "climax", "resolution"}:
                continue
            _write_cinematic(instrument, form, section, style, plan, rng)
        elif style.name == "lofi":
            _write_lofi(instrument, form, section, style, plan, rng)
        else:
            _write_anthem_rhythm(instrument, form, section, style, plan, rng)
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    return instrument


def _write_anthem_rhythm(instrument, form, section, style, plan, rng) -> None:
    for bar in range(section.bars):
        chord = build_chord(form.key, section.degrees[bar])
        root = _pitch(chord.root_pc, 48)
        fifth_pc = chord.pitch_classes[2] if len(chord.pitch_classes) > 2 else chord.root_pc
        fifth = _pitch(fifth_pc, 55)
        bar_beat = (section.start_bar + bar) * 4
        accents = (0.0, 1.0, 2.0, 3.0) if section.name == "theme" else (0.0, 0.5, 1.5, 2.0, 2.5, 3.5)
        for index, beat in enumerate(accents):
            velocity = 53 + int(section.intensity * 34) + rng.randint(-3, 4)
            # Short enough for the intended muted pulse, long enough for an
            # electric-guitar note to ring between attacks.
            duration = 0.45 if beat % 1 else 0.78
            _add(instrument, root, bar_beat + beat, duration, velocity, form)
            _add(instrument, fifth, bar_beat + beat, duration, velocity - 5, form)


def _write_cinematic(instrument, form, section, style, plan, rng) -> None:
    offsets = (0.0, 1.0, 2.0, 3.0)
    for bar in range(section.bars):
        chord = build_chord(form.key, section.degrees[bar])
        notes = [_pitch(pc, 53 + index * 4) for index, pc in enumerate(chord.pitch_classes[:4])]
        bar_beat = (section.start_bar + bar) * 4
        swell = section.name == "climax"
        for index, beat in enumerate(offsets):
            if section.name == "resolution" and bar % 2:
                continue
            velocity = 34 + int(section.intensity * 30) + (index * 4 if swell else 0)
            duration = 1.75 if swell else 1.35
            _add(instrument, notes[index % len(notes)], bar_beat + beat, duration, velocity, form)


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
            for pitch in notes[:3]:
                _add(instrument, pitch, bar_beat + beat, 1.0, velocity, form)


def _write_lead(instrument, form, section, style, rng, plan) -> None:
    spans = module_bar_spans(section)
    if not spans:
        # In a rare short-profile case, use the section's stable harmony cells.
        spans = ()
    for module, first_bar, end_bar in spans:
        motif = module_motif(module.name)
        phrase_number = 0
        for phrase_start in range(first_bar, end_bar, 2):
            phrase_bars = min(2, end_bar - phrase_start)
            phrase_base = (section.start_bar + phrase_start) * 4
            phrase_limit = phrase_bars * 4
            for event in motif:
                if event.beat >= phrase_limit:
                    continue
                degree = developed_degree(
                    event.degree, plan.motif_treatment or "repeat", phrase_number
                )
                if degree is None:
                    continue
                bar = min(section.bars - 1, phrase_start + int(event.beat // 4))
                chord = build_chord(form.key, section.degrees[bar])
                target = 59 + section.intensity * 8 + module.complexity * 4 + degree
                if event.beat % 4 in (0.0, 2.0):
                    pitch = _pitch(min(chord.pitch_classes, key=lambda pc: abs(_pitch(pc, target) - target)), target)
                else:
                    pitch = _scale_pitch(form, degree, target)
                if module.todo_count and event.beat >= 7.0 and phrase_number % 2:
                    continue
                velocity = 65 + int(section.intensity * 34) + rng.randint(-3, 4)
                next_beat = next(
                    (candidate.beat for candidate in motif if candidate.beat > event.beat),
                    phrase_limit,
                )
                ringing = max(event.duration, min(1.5, (next_beat - event.beat) * 0.91))
                _add(instrument, pitch, phrase_base + event.beat, min(ringing, phrase_limit - event.beat - 0.04), velocity, form)
            if (plan.motif_treatment == "extend" and phrase_number % 2 == 1
                    and phrase_limit >= 4):
                pitch = _scale_pitch(form, motif[-1].degree + 1, 69 + section.intensity * 6)
                _add(instrument, pitch, phrase_base + phrase_limit - 0.48, 0.38, 72, form)
            phrase_number += 1


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
