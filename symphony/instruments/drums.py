"""Style-specific GM drum kit grooves with boundary-only fills."""

from __future__ import annotations

import random

import pretty_midi

from symphony.form import Form
from symphony.styles import DrumGroove, Style
from symphony.variation import VariationPlan
from symphony.space import phrase_rest_bar
from symphony.instruments.repo_hook import add_repo_hook

DRUM_CHANNEL = 9  # MIDI channel 10


def render_drums(
    form: Form, style: Style, profile, rng: random.Random, plan: VariationPlan
) -> pretty_midi.Instrument:
    instrument = pretty_midi.Instrument(program=0, is_drum=True, name="Drum Kit")
    instrument.channel = DRUM_CHANNEL
    instrument.control_changes.extend(
        [
            pretty_midi.ControlChange(number=7, value=94, time=0.0),
            pretty_midi.ControlChange(number=10, value=64, time=0.0),
            pretty_midi.ControlChange(number=91, value=10, time=0.0),
        ]
    )
    groove = next(item for item in style.drum_grooves if item.name == plan.drum_groove)
    module_complexity = {
        module.name: module.complexity for module in profile.modules
    }
    for section in form.sections:
        if section.name in {"intro", "outro"} or plan.role_for(section.name, "drums") == "out":
            continue
        complexity = (
            sum(module_complexity[module.name] for module in section.modules)
            / max(1, len(section.modules))
        )
        density = min(
            style.drum_density_cap,
            0.65 + complexity * 0.08 + section.intensity * 0.16,
        )
        for local_bar in range(section.bars):
            if phrase_rest_bar(style, section, local_bar, "drums"):
                continue
            todo_rest = (
                local_bar == min(1, section.bars - 1)
                and any(module.todo_count > 0 for module in section.modules)
            )
            bar_start = (section.start_bar + local_bar) * form.beats_per_bar
            is_boundary_bar = local_bar == section.bars - 1
            build_bar = section.name == "development" and local_bar >= section.bars - 2
            for pitch, offsets, base_velocity in (
                (36, groove.kick, 92),
                (38, groove.snare, 76),
                (42, groove.hats, 47),
            ):
                for beat in offsets:
                    if todo_rest and beat < 1.0:
                        continue
                    if rng.random() > density:
                        continue
                    velocity = int(
                        (
                            base_velocity
                            + int(section.intensity * 12)
                            + rng.randint(-5, 5)
                        ) * style.drum_gain
                    )
                    if build_bar and pitch == 42:
                        velocity += int(9 * style.drum_gain)
                    _hit(instrument, pitch, bar_start + beat, velocity, form)
            # Fills happen only on the final bar before a section boundary.
            if is_boundary_bar and style.drum_fills:
                fill_count = 2 + min(4, round(complexity / 2.0))
                for fill_index in range(fill_count):
                    beat = 4.0 - (fill_count - fill_index) * (0.5 if style.name == "anthem" else 0.25)
                    pitch = groove.fill_pitch if fill_index % 2 else 45
                    _hit(instrument, pitch, bar_start + max(0.0, beat), 58 + fill_index * 5, form)
    for section in form.sections:
        add_repo_hook(instrument, form, section, plan, "drums")
    instrument.notes.sort(key=lambda note: (note.start, note.pitch))
    return instrument


def _hit(
    instrument: pretty_midi.Instrument,
    pitch: int,
    beat: float,
    velocity: int,
    form: Form,
) -> None:
    start = max(0.0, beat * form.seconds_per_beat)
    instrument.notes.append(
        pretty_midi.Note(
            velocity=max(1, min(127, velocity)),
            pitch=pitch,
            start=start,
            end=start + min(0.18, form.seconds_per_beat * 0.2),
        )
    )
