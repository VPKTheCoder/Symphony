"""Piano accompaniment.

Step-one instrument: the piano carries the complete harmonic sketch.  The same
part works with a wide, sustained cinematic treatment and a softer, swung
lo-fi treatment through style parameters rather than a second composer.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pretty_midi

from symphony.form import Form, SectionPlan
from symphony.styles import PianoPattern, Style
from symphony.variation import VariationPlan
from symphony.melody import render_hook_fragment
from symphony.theory import (
    Chord,
    build_chord,
    choose_bass,
    chord_tone_near,
    nearest_pitch_with_pc,
    voice_upper,
)

PROGRAM_ACOUSTIC_GRAND = 0


@dataclass(frozen=True)
class _Harmony:
    chord: Chord
    bass: int
    upper: tuple[int, ...]


def render_piano(
    form: Form,
    style: Style,
    rng: random.Random,
    plan: VariationPlan,
) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(
        program=PROGRAM_ACOUSTIC_GRAND,
        is_drum=False,
        name="Piano",
    )
    instrument.channel = 0
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=82, time=0.0),
            pretty_midi.ControlChange(number=10, value=74, time=0.0),
            pretty_midi.ControlChange(number=91, value=32, time=0.0),
        ]
    )

    previous_upper: tuple[int, ...] | None = None
    previous_bass: int | None = None
    voicing_style = next(
        item for item in style.voicing_styles if item.name == plan.voicing_style
    )

    for section in form.sections:
        if plan.role_for(section.name, "piano") == "out":
            continue
        current: _Harmony | None = None
        for local_bar in range(section.bars):
            if local_bar % section.bars_per_chord == 0:
                has_todo = local_bar == min(1, section.bars - 1) and any(
                    module.todo_count > 0 for module in section.modules
                )
                chord = _choose_chord(
                    form, section, local_bar, style, plan, sus4=has_todo
                )
                upper = voice_upper(
                    chord,
                    low=max(49, style.upper_floor + voicing_style.low_shift),
                    high=min(102, style.upper_ceiling + voicing_style.high_shift),
                    previous=previous_upper,
                    target_top=_top_target(form, section, local_bar, style, plan),
                    voices=style.upper_voices,
                    max_gap=voicing_style.max_gap,
                    rng=rng,
                )
                bass = choose_bass(
                    chord,
                    previous=previous_bass,
                    center=_bass_center(section),
                    rng=rng,
                )
                previous_upper = upper
                previous_bass = bass
                current = _Harmony(chord=chord, bass=bass, upper=upper)

            assert current is not None
            global_beat = (section.start_bar + local_bar) * form.beats_per_bar
            if local_bar % section.bars_per_chord == 0:
                held = min(section.bars_per_chord, section.bars - local_bar)
                _write_pedal(
                    instrument,
                    global_beat=global_beat,
                    beats_per_bar=form.beats_per_bar,
                    seconds_per_beat=form.seconds_per_beat,
                    style=style,
                    bars_held=held,
                )
            _play_bar(
                instrument,
                form=form,
                style=style,
                section=section,
                local_bar=local_bar,
                global_beat=global_beat,
                harmony=current,
                rng=rng,
                plan=plan,
            )

    # One in-scale tritone marks the section carrying the highest unsafe load.
    unsafe_sections = [
        section for section in form.sections
        if any(module.unsafe_count > 0 for module in section.modules)
    ]
    if unsafe_sections:
        section = max(
            unsafe_sections,
            key=lambda candidate: sum(module.unsafe_count for module in candidate.modules),
        )
        local_bar = min(section.bars - 1, section.bars // 2)
        beat = (section.start_bar + local_bar) * form.beats_per_bar + 2.0
        pcs = sorted({(form.key.tonic_pc + interval) % 12 for interval in form.key.intervals})
        tritones = [(left, right) for left in pcs for right in pcs if (right - left) % 12 == 6]
        if tritones:
            left, right = tritones[0]
            for pitch_class, target in ((left, 65), (right, 71)):
                pitch = min(
                    (value for value in range(60, 85) if value % 12 == pitch_class),
                    key=lambda value: abs(value - target),
                )
                _add_note(
                    instrument, pitch, beat, duration=0.8,
                    velocity=_velocity(style, section.intensity, 2.0, 2.0, rng),
                    form=form, style=style, rng=rng,
                )

    for section in form.sections:
        if plan.role_for(section.name, "piano") == "out":
            continue
        if section.name == "intro" and style.name != "contemplative" and section.bars >= 6:
            render_hook_fragment(
                instrument, form, section, plan, style,
                part="piano", bars=2, bar_offset=2, octave=0, velocity_scale=0.58,
            )
        elif section.name == "outro":
            render_hook_fragment(
                instrument, form, section, plan, style,
                part="piano", bars=2, bar_offset=0, octave=0, velocity_scale=0.70,
            )
    # The piano's high shimmer belongs to the climax.  Outside it, fold any
    # exceptionally high note down an octave so the climax stays the piece's
    # single highest point.
    _cap_non_climax_register(instrument, form)
    end_time = max(
        form.total_bars * form.beats_per_bar * form.seconds_per_beat,
        max((note.end for note in instrument.notes), default=0.0) + 0.4,
    )
    instrument.control_changes.append(
        pretty_midi.ControlChange(number=64, value=0, time=end_time + 0.2)
    )
    instrument.notes = _clean_same_pitch_notes(instrument.notes)
    instrument.control_changes.sort(key=lambda change: (change.time, change.number))
    return instrument


def _play_bar(
    instrument: pretty_midi.Instrument,
    *,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
    plan: VariationPlan,
) -> None:
    pattern = next(item for item in style.piano_patterns if item.name == plan.pattern_for(section.name))
    if style.comp_style == "ostinato":
        _play_ostinato_bar(
            instrument, form, style, section, local_bar, global_beat, harmony, rng,
            plan, pattern,
        )
        return
    if style.comp_style == "driving" and section.name in {
        "intro", "theme", "development", "climax"
    }:
        _play_driving_bar(
            instrument, form, style, section, local_bar, global_beat, harmony, rng,
            plan, pattern,
        )
        return
    if section.name == "intro":
        _play_intro(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
        if local_bar > 0 and local_bar % 2 == 1:
            for beat in pattern.intro[:1]:
                _add_chord(
                    instrument,
                    (harmony.upper[0], harmony.upper[-2], harmony.upper[-1]),
                    global_beat + beat,
                    duration=1.15,
                    base_velocity=_velocity(style, section.intensity, beat, -8.0, rng),
                    form=form, style=style, rng=rng, roll=True,
                )
    elif section.name == "theme":
        _play_varied_bar(
            instrument, form, style, section, local_bar, global_beat, harmony,
            rng, plan, pattern,
        )
    elif section.name == "development":
        _play_varied_bar(
            instrument, form, style, section, local_bar, global_beat, harmony,
            rng, plan, pattern,
        )
    elif section.name == "climax":
        _play_varied_bar(
            instrument, form, style, section, local_bar, global_beat, harmony,
            rng, plan, pattern,
        )
    elif section.name == "resolution":
        _play_resolution(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    else:
        _play_outro(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )


def _play_ostinato_bar(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
    plan: VariationPlan,
    pattern: PianoPattern,
) -> None:
    """A hypnotic repeating figure over slow harmony.

    The same four-note cell repeats for as long as the harmony holds.  Only its
    register, dynamics and a sparse high answer change, so the figure reads as a
    trance rather than a melody competing with the violin.
    """

    if section.name == "outro" and local_bar == section.bars - 1:
        _play_contemplative_final_bar(
            instrument, form, style, section, global_beat, harmony, rng,
        )
        return

    beats = {
        "intro": pattern.intro,
        "theme": pattern.theme,
        "development": pattern.development,
        "climax": pattern.climax,
        "resolution": pattern.theme,
        "outro": pattern.intro,
    }[section.name]
    if section.name in {"intro", "outro"}:
        # Frames stay sparse but always keep a quiet pulse on beats 1 and 3.
        beats = tuple(sorted(set(beats) | {0.0, 2.0}))
    ornament = plan.ornament_for(section.name)
    high_reply = (
        local_bar % 4 == 2 and ornament in {"high_reply", "late_answer"}
    )
    bass_slots = 1 if local_bar % section.bars_per_chord == 0 else 0
    budget = style.max_piano_attacks_per_bar - bass_slots - int(high_reply)
    beats = _limit_attacks(beats, max(1, budget))

    if local_bar % section.bars_per_chord == 0:
        hold = min(section.bars_per_chord, section.bars - local_bar)
        _add_note(
            instrument,
            harmony.bass,
            global_beat,
            duration=max(1.0, hold * 4.0 - 0.15),
            velocity=_velocity(style, section.intensity, 0.0, -9.0, rng),
            form=form,
            style=style,
            rng=rng,
        )

    upper = harmony.upper
    middle = upper[min(1, len(upper) - 1)]
    if (local_bar // 4) % 2:
        cell = (upper[0], upper[-2] if len(upper) > 2 else middle, upper[-1], middle)
    else:
        cell = (upper[0], middle, upper[-1], middle)
    growth = local_bar / max(1, section.bars - 1)
    for index, beat in enumerate(beats):
        pitch = cell[index % len(cell)]
        accent = 1.0 if abs(beat) < 1e-6 else -2.5
        if section.name == "climax":
            accent += 1.6
        velocity = _velocity(
            style, section.intensity, beat, accent + growth * 1.5, rng,
        )
        _add_note(
            instrument,
            pitch,
            global_beat + beat,
            duration=0.82 if section.name == "climax" else 0.95,
            velocity=velocity,
            form=form,
            style=style,
            rng=rng,
            top=pitch == upper[-1],
        )

    if high_reply:
        high = _high_chord_tone(harmony, style, rng, offset=6)
        if section.name != "climax":
            high = min(high, 80)
        _add_note(
            instrument,
            high,
            global_beat + 2.5,
            duration=1.7,
            velocity=_velocity(style, section.intensity, 2.5, -9.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )


def _play_contemplative_final_bar(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    """Let the last tonic ring well past the bar line."""

    duration = max(4.0, style.final_chord_beats)
    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=duration,
        velocity=_velocity(style, section.intensity, 0.0, -7.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    _add_chord(
        instrument,
        harmony.upper,
        global_beat,
        duration=duration,
        base_velocity=_velocity(style, section.intensity, 0.0, -2.0, rng),
        form=form,
        style=style,
        rng=rng,
        roll=True,
    )
    _add_note(
        instrument,
        min(_high_chord_tone(harmony, style, rng, offset=6), 80),
        global_beat + 1.25,
        duration=max(2.0, duration - 1.5),
        velocity=_velocity(style, section.intensity, 1.25, -10.0, rng),
        form=form,
        style=style,
        rng=rng,
        top=True,
    )


def _play_driving_bar(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
    plan: VariationPlan,
    pattern: PianoPattern,
) -> None:
    if section.name == "intro":
        _add_note(
            instrument, harmony.bass, global_beat, duration=3.8,
            velocity=_velocity(style, section.intensity, 0.0, 2.0, rng),
            form=form, style=style, rng=rng,
        )
        if local_bar >= 1:
            for beat in pattern.intro:
                _add_chord(
                    instrument,
                    (harmony.upper[0], harmony.upper[-2], harmony.upper[-1]),
                    global_beat + beat,
                    duration=0.55,
                    base_velocity=_velocity(style, section.intensity, beat, -3.0, rng),
                    form=form, style=style, rng=rng, roll=True,
                )
        return

    if section.name == "theme":
        beats = pattern.theme
    elif section.name == "development":
        beats = pattern.development
    else:
        beats = pattern.climax
    beats = _limit_attacks(beats, max(1, style.max_piano_attacks_per_bar - 1))

    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=1.0 if section.name != "climax" else 1.4,
        velocity=_velocity(style, section.intensity, 0.0, 4.0, rng),
        form=form, style=style, rng=rng,
    )
    for index, beat in enumerate(beats):
        if section.name == "development" or pattern.texture == "broken":
            pitches = (harmony.upper[(index + local_bar) % len(harmony.upper)],)
        elif pattern.texture == "high":
            pitches = harmony.upper[-2:]
        elif pattern.texture == "stabs" or index % 2 == 0 or section.name == "climax":
            pitches = (harmony.upper[0], harmony.upper[2], harmony.upper[-1])
        else:
            pitches = harmony.upper[-2:]
        velocity = _velocity(
            style, section.intensity, beat,
            5.0 if section.name == "climax" and beat in (0.0, 2.0) else 0.0,
            rng,
        )
        duration = 0.62 if section.name != "climax" else 0.82
        _add_chord(
            instrument, pitches, global_beat + beat, duration=duration,
            base_velocity=velocity, form=form, style=style, rng=rng,
            roll=section.name == "climax",
        )
        if section.name == "climax" and style.climax_octaves:
            for pitch in pitches:
                if pitch + 12 <= 108:
                    _add_note(
                        instrument, pitch + 12, global_beat + beat,
                        duration=duration - 0.1,
                        velocity=max(18, velocity - 10),
                        form=form, style=style, rng=rng, top=True,
                    )


def _play_varied_bar(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
    plan: VariationPlan,
    pattern: PianoPattern,
) -> None:
    if section.name == "climax":
        beats = pattern.climax
    elif section.name == "development":
        beats = pattern.development
    else:
        beats = pattern.theme

    ornament = plan.ornament_for(section.name)
    fill_beats = (
        {
            "high_reply": (3.0,),
            "pickup": (3.0, 3.5),
            "late_answer": (2.75, 3.5),
            "turn": (3.0, 3.5),
            "rising_fill": (2.5, 3.0, 3.5),
            "octave_answer": (3.0, 3.5),
        }.get(ornament, ())
        if ornament != "none" and local_bar % 2 == 1
        else ()
    )
    beats = _limit_attacks(
        beats,
        max(1, style.max_piano_attacks_per_bar - 1 - len(fill_beats)),
    )

    bass_duration = 2.4 if section.name == "theme" else 3.2
    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=bass_duration,
        velocity=_velocity(style, section.intensity, 0.0, -2.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    if style.comp_style == "swung_comp":
        chord_duration = 0.86
    elif section.name == "climax":
        chord_duration = 1.35
    else:
        chord_duration = 1.05

    for index, beat in enumerate(beats):
        if pattern.texture == "broken" or section.name == "development":
            pitches = (harmony.upper[(index + local_bar) % len(harmony.upper)],)
        elif pattern.texture == "high":
            pitches = harmony.upper[-2:]
        elif pattern.texture == "stabs":
            pitches = (harmony.upper[0], harmony.upper[-1])
        else:
            pitches = harmony.upper
        accent = 1.5 if section.name == "climax" and beat % 2.0 == 0 else 0.0
        velocity = _velocity(style, section.intensity, beat, accent, rng)
        _add_chord(
            instrument,
            pitches,
            global_beat + beat,
            duration=chord_duration,
            base_velocity=velocity,
            form=form,
            style=style,
            rng=rng,
            roll=True,
        )

    if fill_beats:
        for index, beat in enumerate(fill_beats):
            pitch = harmony.upper[-1 - (index % min(2, len(harmony.upper)))]
            _add_note(
                instrument,
                pitch,
                global_beat + beat,
                duration=0.34,
                velocity=_velocity(style, section.intensity, beat, -4.0, rng),
                form=form,
                style=style,
                rng=rng,
                top=True,
            )


def _play_intro(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    if form.health < 0.70 and local_bar == 1:
        # Messier profiles need a clearer pickup into the opening phrase. The
        # healthy cinematic profile keeps its original sparse introduction.
        _add_chord(
            instrument,
            (harmony.upper[0], harmony.upper[-2], harmony.upper[-1]),
            global_beat + 0.5,
            duration=2.7,
            base_velocity=_velocity(style, section.intensity, 0.5, 1.0, rng),
            form=form,
            style=style,
            rng=rng,
            roll=True,
        )
    slot = local_bar % section.bars_per_chord == 0
    if slot:
        _add_note(
            instrument,
            harmony.bass,
            global_beat,
            duration=6.6,
            velocity=_velocity(style, section.intensity, 0.0, -6.0, rng),
            form=form,
            style=style,
            rng=rng,
        )
        if local_bar >= 2:
            subset = (harmony.upper[0], harmony.upper[2], harmony.upper[-1])
            _add_chord(
                instrument,
                subset,
                global_beat + 1.5,
                duration=3.6,
                base_velocity=_velocity(
                    style, section.intensity, 1.5, -2.0, rng
                ),
                form=form,
                style=style,
                rng=rng,
                roll=True,
            )
        if local_bar == 0:
            _add_note(
                instrument,
                _high_chord_tone(harmony, style, rng, offset=4),
                global_beat + 2.5,
                duration=2.1,
                velocity=_velocity(style, section.intensity, 2.5, -5.0, rng),
                form=form,
                style=style,
                rng=rng,
                top=True,
            )
        return

    if local_bar >= section.bars - 2:
        # Keep the last introductory bar connected to the theme. The previous
        # sparse version left a multi-beat gap at this section boundary.
        if local_bar == section.bars - 1:
            _add_chord(
                instrument,
                (harmony.upper[0], harmony.upper[-2], harmony.upper[-1]),
                global_beat + 1.0,
                duration=2.8,
                base_velocity=_velocity(style, section.intensity, 1.0, -7.0, rng),
                form=form,
                style=style,
                rng=rng,
                roll=True,
            )
        return
    high = _high_chord_tone(harmony, style, rng, offset=5)
    _add_note(
        instrument,
        high,
        global_beat + 2.0,
        duration=1.8,
        velocity=_velocity(style, section.intensity, 2.0, -7.0, rng),
        form=form,
        style=style,
        rng=rng,
        top=True,
    )


def _play_theme(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    swung = style.comp_style == "swung_comp"
    breath = local_bar % 4 == 3
    chord_beat = 1.5 if swung else 0.5

    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=2.2,
        velocity=_velocity(style, section.intensity, 0.0, -5.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    if not breath:
        _add_note(
            instrument,
            _fifth_pitch(harmony),
            global_beat + 2.0,
            duration=1.55,
            velocity=_velocity(style, section.intensity, 2.0, -7.0, rng),
            form=form,
            style=style,
            rng=rng,
        )

    _add_chord(
        instrument,
        harmony.upper,
        global_beat + chord_beat,
        duration=2.1 if not swung else 1.15,
        base_velocity=_velocity(style, section.intensity, chord_beat, 0.0, rng),
        form=form,
        style=style,
        rng=rng,
        roll=True,
    )

    if breath:
        return

    if swung:
        second_beat = 3.5
        second_notes = harmony.upper[1:]
        second_duration = 1.0
    else:
        second_beat = 2.5
        second_notes = harmony.upper[-2:]
        second_duration = 1.15
    _add_chord(
        instrument,
        second_notes,
        global_beat + second_beat,
        duration=second_duration,
        base_velocity=_velocity(
            style, section.intensity, second_beat, -3.0, rng
        ),
        form=form,
        style=style,
        rng=rng,
        roll=False,
    )
    if swung and local_bar % 2 == 0:
        # A light offbeat answer adds a little more pocket without crowding the
        # relaxed swung comp.
        _add_chord(
            instrument,
            harmony.upper[-2:],
            global_beat + 2.5,
            duration=0.65,
            base_velocity=_velocity(style, section.intensity, 2.5, -9.0, rng),
            form=form,
            style=style,
            rng=rng,
            roll=False,
        )
    if local_bar % 2 == 1:
        _add_note(
            instrument,
            _high_chord_tone(harmony, style, rng, offset=5),
            global_beat + 3.5,
            duration=0.75,
            velocity=_velocity(style, section.intensity, 3.5, -4.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )


def _play_development(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    swung = style.comp_style == "swung_comp"
    phrase_end = local_bar % 4 == 3

    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=3.7,
        velocity=_velocity(style, section.intensity, 0.0, -4.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    _add_note(
        instrument,
        _fifth_pitch(harmony),
        global_beat + 2.5,
        duration=1.25,
        velocity=_velocity(style, section.intensity, 2.5, -8.0, rng),
        form=form,
        style=style,
        rng=rng,
    )

    if phrase_end:
        _add_chord(
            instrument,
            harmony.upper,
            global_beat + (2.0 if not swung else 2.5),
            duration=1.7,
            base_velocity=_velocity(
                style, section.intensity, 2.0, -2.0, rng
            ),
            form=form,
            style=style,
            rng=rng,
            roll=True,
        )
        _add_note(
            instrument,
            harmony.upper[-1],
            global_beat + 3.0,
            duration=0.8,
            velocity=_velocity(style, section.intensity, 3.0, -2.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )
        return

    positions = (
        (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
        if swung
        else (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
    )
    run = list(harmony.upper) + list(reversed(harmony.upper[:-1]))
    if local_bar % 2:
        run.reverse()
    top_pitch = max(run)
    for index, beat in enumerate(positions):
        pitch = run[index % len(run)]
        _add_note(
            instrument,
            pitch,
            global_beat + beat,
            duration=0.42,
            velocity=_velocity(
                style,
                section.intensity,
                beat,
                -2.0 + (2.0 if pitch == top_pitch else 0.0),
                rng,
            ),
            form=form,
            style=style,
            rng=rng,
            top=pitch == top_pitch,
        )


def _play_climax(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    swung = style.comp_style == "swung_comp"
    second_beat = 2.5 if swung else 2.0
    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=1.9,
        velocity=_velocity(style, section.intensity, 0.0, -2.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    if style.upper_ceiling >= 84 and harmony.bass + 12 <= 60:
        _add_note(
            instrument,
            harmony.bass + 12,
            global_beat,
            duration=1.65,
            velocity=_velocity(style, section.intensity, 0.0, -8.0, rng),
            form=form,
            style=style,
            rng=rng,
        )

    _add_chord(
        instrument,
        harmony.upper,
        global_beat,
        duration=1.85,
        base_velocity=_velocity(style, section.intensity, 0.0, 1.0, rng),
        form=form,
        style=style,
        rng=rng,
        roll=True,
    )
    if (
        style.upper_ceiling >= 84
        and harmony.upper[-1] + 12 <= 96
        and local_bar % 2 == 0
    ):
        _add_note(
            instrument,
            harmony.upper[-1] + 12,
            global_beat + 0.04,
            duration=1.55,
            velocity=_velocity(style, section.intensity, 0.0, -9.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )

    second_notes = (
        harmony.upper
        if local_bar % 4 == 2
        else (harmony.upper[0], harmony.upper[2], harmony.upper[-1])
    )
    _add_chord(
        instrument,
        second_notes,
        global_beat + second_beat,
        duration=1.5,
        base_velocity=_velocity(
            style, section.intensity, second_beat, 0.0, rng
        ),
        form=form,
        style=style,
        rng=rng,
        roll=True,
    )
    _add_note(
        instrument,
        _fifth_pitch(harmony),
        global_beat + second_beat,
        duration=1.3,
        velocity=_velocity(
            style, section.intensity, second_beat, -11.0, rng
        ),
        form=form,
        style=style,
        rng=rng,
    )


def _play_resolution(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    swung = style.comp_style == "swung_comp"
    breath = local_bar % 4 == 3
    final_bar = local_bar == section.bars - 1

    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=3.8 if final_bar else 2.9,
        velocity=_velocity(style, section.intensity, 0.0, -7.0, rng),
        form=form,
        style=style,
        rng=rng,
    )
    _add_chord(
        instrument,
        harmony.upper,
        global_beat + (1.5 if swung else 0.5),
        duration=3.2 if final_bar else (1.3 if swung else 2.1),
        base_velocity=_velocity(style, section.intensity, 0.5, -2.0, rng),
        form=form,
        style=style,
        rng=rng,
        roll=True,
    )
    if final_bar:
        _add_note(
            instrument,
            _high_chord_tone(harmony, style, rng, offset=5),
            global_beat + 2.4,
            duration=1.0,
            velocity=_velocity(style, section.intensity, 2.4, -7.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )
        return
    if not breath:
        _add_note(
            instrument,
            _high_chord_tone(harmony, style, rng, offset=5),
            global_beat + 2.5,
            duration=1.0,
            velocity=_velocity(style, section.intensity, 2.5, -6.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )


def _play_outro(
    instrument: pretty_midi.Instrument,
    form: Form,
    style: Style,
    section: SectionPlan,
    local_bar: int,
    global_beat: float,
    harmony: _Harmony,
    rng: random.Random,
) -> None:
    final_bar = local_bar == section.bars - 1
    if final_bar:
        _add_note(
            instrument,
            harmony.bass,
            global_beat,
            duration=4.0,
            velocity=_velocity(style, section.intensity, 0.0, -7.0, rng),
            form=form,
            style=style,
            rng=rng,
        )
        _add_chord(
            instrument,
            harmony.upper,
            global_beat,
            duration=4.0,
            base_velocity=_velocity(style, section.intensity, 0.0, -1.0, rng),
            form=form,
            style=style,
            rng=rng,
            roll=True,
        )
        _add_note(
            instrument,
            _high_chord_tone(harmony, style, rng, offset=7),
            global_beat + 1.5,
            duration=2.3,
            velocity=_velocity(style, section.intensity, 1.5, -8.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )
        return

    slot = local_bar % section.bars_per_chord == 0
    if slot:
        _add_note(
            instrument,
            harmony.bass,
            global_beat,
            duration=6.4,
            velocity=_velocity(style, section.intensity, 0.0, -7.0, rng),
            form=form,
            style=style,
            rng=rng,
        )
        final_approach = local_bar >= section.bars - 2
        _add_chord(
            instrument,
            harmony.upper,
            global_beat + 1.5,
            duration=3.2 if final_approach else 3.5,
            base_velocity=_velocity(
                style, section.intensity, 1.5, -7.0 if final_approach else -3.0, rng
            ),
            form=form,
            style=style,
            rng=rng,
            roll=True,
        )
        return

    if local_bar < section.bars - 1:
        _add_note(
            instrument,
            _high_chord_tone(harmony, style, rng, offset=5),
            global_beat + 2.2,
            duration=1.7,
            velocity=_velocity(style, section.intensity, 2.2, -9.0, rng),
            form=form,
            style=style,
            rng=rng,
            top=True,
        )


def _choose_chord(
    form: Form,
    section: SectionPlan,
    local_bar: int,
    style: Style,
    plan: VariationPlan,
    *,
    sus4: bool = False,
) -> Chord:
    degree = section.degrees[local_bar]
    color = plan.chord_color_for(section.name)
    seventh = color in {"seventh", "ninth", "eleventh"}
    ninth = color == "ninth"
    eleventh = color == "eleventh" and "eleventh" in style.chord_colors
    if section.name in ("outro", "resolution") and local_bar >= section.bars - 2:
        ninth = ninth or color == "seventh"
    if (
        section.name in ("outro", "resolution")
        and local_bar >= section.bars - 2
        and any(module.todo_count > 0 for module in section.modules)
    ):
        # TODO-heavy repositories hang on a suspension before the final tonic.
        sus4 = True
    return build_chord(
        form.key,
        degree,
        seventh=seventh,
        ninth=ninth,
        add9=False,
        eleventh=eleventh,
        sus4=sus4,
    )


def _top_target(
    form: Form,
    section: SectionPlan,
    local_bar: int,
    style: Style,
    plan: VariationPlan,
) -> float:
    role_target = {
        "intro": 65.0,
        "theme": 72.0,
        "development": 76.0,
        "climax": 82.0,
        "resolution": 71.0,
        "outro": 66.0,
    }[section.name]
    register_shift = (style.upper_ceiling - 84.0) * 0.28
    phrase_arch = (0.0, 0.8, 1.5, 0.5)[local_bar % 4]
    target = (
        role_target + register_shift + plan.register_shift
        + phrase_arch * (0.7 + section.intensity)
    )
    if section.name in ("resolution", "outro"):
        target -= local_bar / max(1, section.bars) * 2.0
    return max(55.0, min(style.upper_ceiling - 1.0, target))


def _bass_center(section: SectionPlan) -> int:
    return round(53.5 - section.intensity * 1.5)


def _high_chord_tone(
    harmony: _Harmony,
    style: Style,
    rng: random.Random,
    *,
    offset: int,
) -> int:
    target = min(style.upper_ceiling, harmony.upper[-1] + offset)
    pitch = chord_tone_near(
        harmony.chord,
        target=target,
        low=harmony.upper[0],
        high=style.upper_ceiling,
        rng=rng,
        avoid=harmony.upper[-1],
    )
    if pitch == harmony.upper[-1]:
        return nearest_pitch_with_pc(
            harmony.upper[-1] % 12,
            target + 2,
            harmony.upper[0],
            style.upper_ceiling,
        )
    return pitch


def _fifth_pitch(harmony: _Harmony) -> int:
    candidate = harmony.bass + 7
    if candidate % 12 in harmony.chord.pitch_classes:
        return candidate
    return harmony.bass + 6


def _limit_attacks(beats: tuple[float, ...], cap: int) -> tuple[float, ...]:
    """Thin a comping pattern without losing its first and last attack."""

    cap = max(1, int(cap))
    if len(beats) <= cap:
        return beats
    if cap == 1:
        return (beats[0],)
    indices: list[int] = []
    for index in range(cap):
        position = round(index * (len(beats) - 1) / (cap - 1))
        if position not in indices:
            indices.append(position)
    return tuple(beats[position] for position in indices)


def _velocity(
    style: Style,
    intensity: float,
    beat: float,
    accent: float,
    rng: random.Random,
) -> int:
    shaped = intensity ** style.velocity_curve
    base = style.velocity_floor + (style.velocity_ceiling - style.velocity_floor) * shaped
    local_beat = beat % 4.0
    if abs(local_beat) < 1e-6 or abs(local_beat - 4.0) < 1e-6:
        base += 3.0
    elif abs(local_beat - 2.0) < 1e-6:
        base += 1.0
    base += accent
    base += rng.uniform(-3.8, 3.8)
    return int(max(18, min(style.velocity_ceiling + 9, round(base))))


def _add_note(
    instrument: pretty_midi.Instrument,
    pitch: int,
    beat: float,
    *,
    duration: float,
    velocity: int,
    form: Form,
    style: Style,
    rng: random.Random,
    top: bool = False,
    roll_seconds: float = 0.0,
) -> None:
    if not 21 <= pitch <= 108:
        return
    jitter_ms = rng.uniform(*style.humanize_ms) / 1000.0
    beat = _apply_swing(beat, style)
    start = (
        beat * form.seconds_per_beat
        + rng.uniform(-jitter_ms, jitter_ms)
        + roll_seconds
    )
    if start < 0.0:
        start = 0.0
    end = start + duration * form.seconds_per_beat
    end += rng.uniform(-jitter_ms * 0.35, jitter_ms * 0.35)
    if end <= start + 0.06:
        end = start + 0.06
    if top:
        velocity = min(style.velocity_ceiling + 10, velocity + 2)
    instrument.notes.append(
        pretty_midi.Note(
            velocity=int(max(18, min(112, velocity))),
            pitch=int(pitch),
            start=float(start),
            end=float(end),
        )
    )


def _add_chord(
    instrument: pretty_midi.Instrument,
    pitches: tuple[int, ...],
    beat: float,
    *,
    duration: float,
    base_velocity: int,
    form: Form,
    style: Style,
    rng: random.Random,
    roll: bool,
) -> None:
    unique = sorted(set(pitches))
    max_roll = style.chord_roll_ms[1] / 1000.0 if roll else 0.0
    for index, pitch in enumerate(unique):
        roll_seconds = 0.0
        if roll and index:
            roll_seconds = index * rng.uniform(0.0, max_roll)
        is_top = index == len(unique) - 1
        velocity = base_velocity + rng.randint(-3, 3) + (3 if is_top else 0)
        _add_note(
            instrument,
            pitch,
            beat,
            duration=duration,
            velocity=velocity,
            form=form,
            style=style,
            rng=rng,
            top=is_top,
            roll_seconds=roll_seconds,
        )


def _write_pedal(
    instrument: pretty_midi.Instrument,
    *,
    global_beat: float,
    beats_per_bar: int,
    seconds_per_beat: float,
    style: Style,
    bars_held: int = 1,
) -> None:
    """Pedal each harmony, with a short lift so changes never blur together."""

    changes = max(1, style.pedal_changes_per_bar)
    total = beats_per_bar * max(1, bars_held)
    span = total / changes
    for index in range(changes):
        start_beat = global_beat + index * span
        end_beat = start_beat + span
        instrument.control_changes.append(
            pretty_midi.ControlChange(
                number=64,
                value=127,
                time=max(0.0, start_beat * seconds_per_beat + 0.01),
            )
        )
        instrument.control_changes.append(
            pretty_midi.ControlChange(
                number=64,
                value=0,
                time=max(0.0, end_beat * seconds_per_beat - 0.07),
            )
        )


def _cap_non_climax_register(instrument: pretty_midi.Instrument, form: Form) -> None:
    """Fold rare high piano notes below the climax apex."""

    climax = next(section for section in form.sections if section.name == "climax")
    bar_seconds = form.beats_per_bar * form.seconds_per_beat
    start = climax.start_bar * bar_seconds
    end = climax.end_bar * bar_seconds
    for note in instrument.notes:
        if start <= note.start < end:
            continue
        while note.pitch > 84:
            note.pitch -= 12


def _apply_swing(beat: float, style: Style) -> float:
    if style.swing_ratio <= 0.5:
        return beat
    fraction = beat - math.floor(beat)
    if abs(fraction - 0.5) < 1e-6:
        return beat + (style.swing_ratio - 0.5)
    return beat


def _clean_same_pitch_notes(notes: list[pretty_midi.Note]) -> list[pretty_midi.Note]:
    """Merge accidental duplicate attacks and prevent same-pitch overlap."""

    cleaned: list[pretty_midi.Note] = []
    last_by_pitch: dict[int, pretty_midi.Note] = {}
    for note in sorted(notes, key=lambda item: (item.start, item.pitch, item.end)):
        previous = last_by_pitch.get(note.pitch)
        if previous is None:
            cleaned.append(note)
            last_by_pitch[note.pitch] = note
            continue

        gap = note.start - previous.start
        if gap < 0.09:
            # The same pitch was emitted by two layers at almost the same
            # instant (often a bass fifth doubling a chord tone).  Treat it as
            # one attack instead of a flam.
            previous.end = max(previous.end, note.end)
            previous.velocity = max(previous.velocity, note.velocity)
            continue

        if previous.end > note.start - 0.02:
            previous.end = max(previous.start + 0.03, note.start - 0.02)
        cleaned.append(note)
        last_by_pitch[note.pitch] = note

    cleaned.sort(key=lambda note: (note.start, note.pitch, note.end))
    return cleaned
