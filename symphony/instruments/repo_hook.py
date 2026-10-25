"""The shared, repo-specific four-bar hook played across the band."""

from __future__ import annotations

import pretty_midi

from symphony.form import Form, SectionPlan
from symphony.variation import VariationPlan


HOOK_BEATS = (0.0, 1.5, 4.0, 6.5, 8.0, 9.5, 12.0, 14.0)
HOOK_DURATIONS = (1.0, 0.8, 1.25, 0.8, 1.0, 0.8, 1.4, 1.0)
HOOK_SECTIONS = {"intro", "theme", "development", "climax", "outro"}


def add_repo_hook(
    instrument: pretty_midi.Instrument,
    form: Form,
    section: SectionPlan,
    plan: VariationPlan,
    part: str,
) -> None:
    if section.name not in HOOK_SECTIONS or not plan.hook_contour:
        return
    ranges = {
        "piano": (60, 96, 78),
        "bass": (24, 48, 34),
        "violin": (55, 103, 79),
        "guitar": (40, 76, 64),
    }
    low, high, center = ranges.get(part, (55, 103, 79))
    for phrase_start in range(0, section.bars, 4):
        phrase_index = phrase_start // 4
        for index, beat_offset in enumerate(HOOK_BEATS):
            relative_beat = phrase_start * 4.0 + beat_offset
            if relative_beat >= section.bars * 4.0:
                continue
            degree = plan.hook_contour[index]
            if section.name == "development":
                degree = 6 - degree
            if phrase_index % 2:
                degree = (degree + 1) % 7
            scale_degree = degree % 7
            pitch_class = (form.key.tonic_pc + form.key.intervals[scale_degree]) % 12
            target = center + section.intensity * (7 if part == "violin" else 3) + (degree - 3) * 1.4
            pitch = min(
                (candidate for candidate in range(low, high + 1) if candidate % 12 == pitch_class),
                key=lambda candidate: abs(candidate - target),
            )
            beat = (section.start_bar * 4.0) + relative_beat
            duration = HOOK_DURATIONS[index]
            if part == "bass":
                duration = min(1.2, duration)
            if part == "guitar" and index % 2:
                duration *= 0.75
            if part == "drums":
                drum_pitch = 36 if index % 4 == 0 else 45 if index % 2 == 0 else 42
                velocity = 62 if section.name == "climax" else 52
                instrument.notes.append(
                    pretty_midi.Note(
                        velocity=velocity,
                        pitch=drum_pitch,
                        start=beat * form.seconds_per_beat,
                        end=(beat + 0.14) * form.seconds_per_beat,
                    )
                )
                continue
            velocity = {
                "piano": 62 if section.name != "climax" else 78,
                "bass": 52 if section.name != "climax" else 68,
                "violin": 76 if section.name != "climax" else 94,
                "guitar": 50 if section.name != "climax" else 67,
            }[part]
            start = beat * form.seconds_per_beat
            end = (beat + duration) * form.seconds_per_beat
            instrument.notes.append(pretty_midi.Note(velocity, pitch, start, end))
