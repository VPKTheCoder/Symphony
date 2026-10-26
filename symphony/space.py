"""Phrase-level breathing room for accompaniment parts.

A four-bar melody phrase needs somewhere to breathe.  Spacious styles make one
support instrument sit out a bar inside each phrase; the parts are staggered so
the whole arrangement does not drop out at once, and the piano remains the
harmonic anchor.  The final bar of a section is never a phrase rest: it belongs
to the cadence and its drum fill.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from symphony.form import Form, SectionPlan
from symphony.styles import Style

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pretty_midi

    from symphony.variation import VariationPlan

PHRASE_BARS = 4
TRACK_PARTS = {
    "Piano": "piano",
    "Bass": "bass",
    "Drum Kit": "drums",
    "Violin": "violin",
    "Guitar": "guitar",
}

# Preferred rest positions within a four-bar phrase.  Bass and drums breathe at
# the phrase tail; guitar rests one bar earlier so the two do not always vanish
# together.
_REST_POSITIONS = {
    "bass": (3, 2),
    "guitar": (2, 3),
    "drums": (3, 2),
}


def phrase_rest_bar(
    style: Style,
    section: SectionPlan,
    local_bar: int,
    part: str,
) -> bool:
    """Return whether *part* should leave this bar empty inside a phrase."""

    count = min(PHRASE_BARS, max(0, int(style.phrase_rest_bars)))
    positions = _REST_POSITIONS.get(part)
    if count == 0 or not positions:
        return False
    if section.name in {"intro", "outro"} or section.bars < PHRASE_BARS:
        return False
    # Keep the final bar intact for the cadence and any boundary fill.
    if local_bar >= section.bars - 1:
        return False
    return local_bar % PHRASE_BARS in positions[:count]


def phrase_rest_bars(
    style: Style,
    section: SectionPlan,
    part: str,
) -> tuple[int, ...]:
    """List the local bars where *part* rests, for tests and diagnostics."""

    return tuple(
        local_bar
        for local_bar in range(section.bars)
        if phrase_rest_bar(style, section, local_bar, part)
    )


def apply_space_policy(
    midi: "pretty_midi.PrettyMIDI",
    form: Form,
    style: Style,
    plan: "VariationPlan",
) -> None:
    """Make resting parts truly silent, including notes that ring across a line."""

    # This pass runs on the four-beat construction grid, before ``_apply_meter``
    # warps bars into the curated meter.
    bar_seconds = form.beats_per_bar * form.seconds_per_beat
    for instrument in midi.instruments:
        part = TRACK_PARTS.get(instrument.name)
        if part is None:
            continue
        for section in form.sections:
            section_start = section.start_bar * bar_seconds
            section_end = section.end_bar * bar_seconds
            if plan.role_for(section.name, part) == "out":
                _silence_span(instrument.notes, section_start, section_end)
                continue
            if plan.role_for(section.name, part) != "support":
                continue
            for local_bar in range(section.bars):
                if not phrase_rest_bar(style, section, local_bar, part):
                    continue
                rest_start = (section.start_bar + local_bar) * bar_seconds
                _silence_span(instrument.notes, rest_start, rest_start + bar_seconds)
        instrument.notes = [
            note for note in instrument.notes if note.end > note.start + 0.005
        ]


def _silence_span(notes: list, start: float, end: float) -> None:
    """Remove attacks inside a window and clip any note ringing into it."""

    kept = []
    for note in notes:
        if note.end <= start or note.start >= end:
            kept.append(note)
            continue
        if note.start >= start:
            continue
        cutoff = start - 0.01
        if cutoff > note.start + 0.005:
            note.end = min(note.end, cutoff)
            kept.append(note)
    notes[:] = kept
