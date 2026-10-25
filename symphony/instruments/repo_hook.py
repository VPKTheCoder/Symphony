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
            if plan.signature_id == "result":
                if part == "violin" and index >= 4:
                    continue
                if part in {"piano", "guitar"} and index < 4:
                    continue
            relative_beat = phrase_start * 4.0 + beat_offset
            if relative_beat >= section.bars * 4.0:
                continue
            degree = plan.hook_contour[index]
            if section.name == "development":
                degree = 6 - degree
            if plan.signature_id == "todos" and section.name in {"development", "climax", "outro"} and index == 7:
                degree = 1
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
            if plan.signature_id == "todos" and index == 7:
                duration = 2.5
            if plan.signature_id == "canon":
                beat += {"piano": 0.0, "bass": 2.0, "drums": 1.0, "violin": 3.0, "guitar": 1.5}[part]
            elif plan.signature_id == "async":
                beat += {"piano": 0.5, "bass": 0.0, "drums": 0.75, "violin": 1.0, "guitar": 1.5}[part]
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

        if plan.signature_id == "iterator" and part in {"violin", "guitar", "piano"}:
            run_start = section.start_bar * 4.0 + phrase_start * 4.0 + 10.0
            for run_index in range(8):
                degree = (plan.hook_contour[run_index % 8] + run_index) % 7
                pitch_class = (form.key.tonic_pc + form.key.intervals[degree]) % 12
                pitch = min(
                    (candidate for candidate in range(low, high + 1) if candidate % 12 == pitch_class),
                    key=lambda candidate: abs(candidate - (center + run_index * 0.7)),
                )
                beat = run_start + run_index * 0.25
                start = beat * form.seconds_per_beat
                instrument.notes.append(pretty_midi.Note(62, pitch, start, start + 0.19 * form.seconds_per_beat))

    if part == "bass" and plan.signature_id == "hub":
        tonic_pc = form.key.tonic_pc
        pedal = min(
            (candidate for candidate in range(24, 49) if candidate % 12 == tonic_pc),
            key=lambda candidate: abs(candidate - 31),
        )
        for bar in range(section.bars):
            beat = (section.start_bar + bar) * 4.0
            start = beat * form.seconds_per_beat
            end = min((beat + 3.85) * form.seconds_per_beat, form.estimated_seconds)
            instrument.notes.append(pretty_midi.Note(55, pedal, start, max(start + 0.02, end)))

    if part == "drums" and plan.signature_id == "complexity":
        for bar in range(section.bars):
            bar_start = (section.start_bar + bar) * 4.0
            for index in range(8):
                beat = bar_start + 0.25 + index * 0.5
                start = beat * form.seconds_per_beat
                instrument.notes.append(
                    pretty_midi.Note(48 + (index % 3) * 7, 42, start, start + 0.12 * form.seconds_per_beat)
                )

    if plan.signature_id == "unsafe" and part == "violin":
        scale_pcs = [(form.key.tonic_pc + interval) % 12 for interval in form.key.intervals]
        tritone = next(
            ((left, right) for left in scale_pcs for right in scale_pcs if (right - left) % 12 == 6),
            None,
        )
        if tritone:
            for phrase_start in range(0, section.bars, 4):
                for index in range(8):
                    pitch_class = tritone[index % 2]
                    pitch = min(
                        (candidate for candidate in range(55, 104) if candidate % 12 == pitch_class),
                        key=lambda candidate: abs(candidate - 83),
                    )
                    beat = (section.start_bar + phrase_start) * 4.0 + 8.0 + index * 0.25
                    start = beat * form.seconds_per_beat
                    instrument.notes.append(pretty_midi.Note(72, pitch, start, start + 0.18 * form.seconds_per_beat))

    if plan.signature_id == "clean" and part == "violin":
        for phrase_start in range(0, section.bars, 4):
            beat = (section.start_bar + phrase_start) * 4.0 + 12.0
            degree = 0
            pitch_class = (form.key.tonic_pc + form.key.intervals[degree]) % 12
            pitch = min((candidate for candidate in range(78, 104) if candidate % 12 == pitch_class), key=lambda value: abs(value - 91))
            start = beat * form.seconds_per_beat
            instrument.notes.append(pretty_midi.Note(108, pitch, start, start + 1.5 * form.seconds_per_beat))
