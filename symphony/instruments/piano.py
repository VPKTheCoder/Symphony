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
from symphony.styles import Style
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


def render_piano(form: Form, style: Style, rng: random.Random) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(
        program=PROGRAM_ACOUSTIC_GRAND,
        is_drum=False,
        name="Piano",
    )
    instrument.channel = 0
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=100, time=0.0),
            pretty_midi.ControlChange(number=10, value=64, time=0.0),
        ]
    )

    previous_upper: tuple[int, ...] | None = None
    previous_bass: int | None = None

    for section in form.sections:
        current: _Harmony | None = None
        for local_bar in range(section.bars):
            if local_bar % section.bars_per_chord == 0:
                chord = _choose_chord(form, section, local_bar, style, rng)
                upper = voice_upper(
                    chord,
                    low=style.upper_floor,
                    high=style.upper_ceiling,
                    previous=previous_upper,
                    target_top=_top_target(form, section, local_bar, style),
                    voices=style.upper_voices,
                    max_gap=style.upper_gap,
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
            _write_pedal(
                instrument,
                global_beat=global_beat,
                beats_per_bar=form.beats_per_bar,
                seconds_per_beat=form.seconds_per_beat,
                style=style,
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
            )

    end_time = form.total_bars * form.beats_per_bar * form.seconds_per_beat
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
) -> None:
    if style.comp_style == "driving" and section.name in {
        "intro", "theme", "development", "climax"
    }:
        _play_driving_bar(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
        return
    if section.name == "intro":
        _play_intro(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    elif section.name == "theme":
        _play_theme(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    elif section.name == "development":
        _play_development(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    elif section.name == "climax":
        _play_climax(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    elif section.name == "resolution":
        _play_resolution(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
        )
    else:
        _play_outro(
            instrument, form, style, section, local_bar, global_beat, harmony, rng
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
) -> None:
    if section.name == "intro":
        _add_note(
            instrument, harmony.bass, global_beat, duration=3.8,
            velocity=_velocity(style, section.intensity, 0.0, 2.0, rng),
            form=form, style=style, rng=rng,
        )
        if local_bar >= 1:
            for beat in (0.5, 2.5):
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
        beats = (0.0, 0.75, 1.5, 2.0, 2.75, 3.5)
    elif section.name == "development":
        beats = (0.0, 0.5, 1.5, 2.0, 2.5, 3.0, 3.5)
    else:
        beats = (0.0, 1.0, 1.5, 2.0, 3.0, 3.5)

    _add_note(
        instrument,
        harmony.bass,
        global_beat,
        duration=1.0 if section.name != "climax" else 1.4,
        velocity=_velocity(style, section.intensity, 0.0, 4.0, rng),
        form=form, style=style, rng=rng,
    )
    for index, beat in enumerate(beats):
        if section.name == "development":
            pitches = (harmony.upper[(index + local_bar) % len(harmony.upper)],)
        elif index % 2 == 0 or section.name == "climax":
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
        if local_bar < section.bars - 2:
            _add_chord(
                instrument,
                harmony.upper,
                global_beat + 1.5,
                duration=3.5,
                base_velocity=_velocity(
                    style, section.intensity, 1.5, -3.0, rng
                ),
                form=form,
                style=style,
                rng=rng,
                roll=True,
            )
        return

    if local_bar < section.bars - 3:
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
    rng: random.Random,
) -> Chord:
    degree = section.degrees[local_bar]
    intensity = section.intensity
    seventh_probability = style.seventh_probability * (0.78 + 0.40 * intensity)
    ninth_probability = style.ninth_probability * (0.78 + 0.40 * intensity)
    eleventh = (
        style.eleventh_probability > 0.0
        and rng.random() < style.eleventh_probability
    )
    seventh = rng.random() < seventh_probability
    ninth = rng.random() < ninth_probability
    add9 = (not ninth) and rng.random() < 0.14
    if section.name in ("outro", "resolution") and local_bar >= section.bars - 2:
        add9 = not ninth and rng.random() < 0.48
    return build_chord(
        form.key,
        degree,
        seventh=seventh,
        ninth=ninth,
        add9=add9,
        eleventh=eleventh,
    )


def _top_target(
    form: Form,
    section: SectionPlan,
    local_bar: int,
    style: Style,
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
    target = role_target + register_shift + phrase_arch * (0.7 + section.intensity)
    if section.name in ("resolution", "outro"):
        target -= local_bar / max(1, section.bars) * 2.0
    return max(55.0, min(style.upper_ceiling - 1.0, target))


def _bass_center(section: SectionPlan) -> int:
    return round(40.5 - section.intensity * 1.5)


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
) -> None:
    changes = max(1, style.pedal_changes_per_bar)
    span = beats_per_bar / changes
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
                time=max(0.0, end_beat * seconds_per_beat - 0.06),
            )
        )


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
