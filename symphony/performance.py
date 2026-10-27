"""Ensemble performance shaping: pocket, phrase dynamics and accents.

The composer writes on a four-beat grid.  This pass makes the parts behave like
one band instead of five quantized tracks: non-piano parts follow the style's
swing, accompaniment phrases swell and relax, and strong beats carry a small
accent.  Lead lines keep the expression written by the melody engine.

The pass is deliberately deterministic.  It uses no random source, runs before
the space policy so any note pushed toward a rest is still trimmed, and keeps
every note inside its original section.  The same profile, style and variation
index therefore remain byte-identical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from symphony.form import Form, SectionPlan
from symphony.space import TRACK_PARTS
from symphony.styles import Style

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pretty_midi

    from symphony.variation import VariationPlan

# A phrase grows through its first three bars and releases into the cadence.
# The values are relative shapes; the style scales them into velocity points.
_PHRASE_SHAPE = (0.0, 0.35, 0.70, 0.15)
_PHRASE_MEAN = sum(_PHRASE_SHAPE) / len(_PHRASE_SHAPE)


def groove_delay_beats(style: Style) -> float:
    """Return the delayed offbeat in beats, or zero for straight styles."""

    if style.swing_ratio <= 0.5:
        return 0.0
    return style.swing_ratio - 0.5


def phrase_dynamic_offset(style: Style, local_bar: int) -> float:
    """Velocity offset for a bar inside a four-bar phrase."""

    shape = _PHRASE_SHAPE[local_bar % len(_PHRASE_SHAPE)] - _PHRASE_MEAN
    return shape * style.phrase_dynamic


def metric_accent(style: Style, beat: float, part: str) -> float:
    """A small downbeat lift that leaves offbeats alone."""

    within = beat % 4.0
    if abs(within) < 1e-6:
        amount = style.metric_accent
    elif abs(within - 2.0) < 1e-6:
        amount = style.metric_accent * 0.40
    else:
        amount = 0.0
    if part == "drums":
        # The groove already separates kick, snare and hats.
        amount *= 0.35
    elif part == "piano":
        # Piano comping shapes its own downbeat accents.
        amount = 0.0
    return amount


def apply_performance_shaping(
    midi: "pretty_midi.PrettyMIDI",
    form: Form,
    style: Style,
    plan: "VariationPlan",
) -> None:
    """Apply the style's pocket and accompaniment phrasing to a composition."""

    bar_seconds = form.beats_per_bar * form.seconds_per_beat
    for instrument in midi.instruments:
        part = TRACK_PARTS.get(instrument.name)
        if part is None:
            continue
        _apply_swing(instrument, form, style, part, bar_seconds)
        _apply_dynamics(instrument, form, style, plan, part, bar_seconds)
        instrument.notes.sort(key=lambda note: (note.start, note.pitch))


def _apply_swing(
    instrument: "pretty_midi.Instrument",
    form: Form,
    style: Style,
    part: str,
    bar_seconds: float,
) -> None:
    delay = groove_delay_beats(style) * form.seconds_per_beat
    if delay <= 0.0 or part == "piano":
        # Piano applies swing when it writes notes; shifting it again would
        # double-swing the comping.
        return

    notes = sorted(instrument.notes, key=lambda note: (note.start, note.pitch))
    delays = [_half_beat_delay(note.start, form, delay, bar_seconds) for note in notes]
    for index, (note, note_delay) in enumerate(zip(notes, delays)):
        if note_delay <= 0.0:
            continue
        section = _section_at(form, note.start, bar_seconds)
        if section is None:
            continue
        new_start = note.start + note_delay
        section_end = section.end_bar * bar_seconds
        new_start = min(new_start, section_end - 1e-4)
        if index + 1 < len(notes):
            # Never let a swung note overtake a separate later attack.  Notes
            # sharing an onset (a chord, a kick and snare, a strum spread) all
            # shift together and must not clamp each other.
            next_original = notes[index + 1].start
            if next_original > note.start + 1e-4:
                next_start = next_original + delays[index + 1]
                if new_start >= next_start - 1e-5:
                    continue
        note.end += new_start - note.start
        note.start = new_start


def _half_beat_delay(
    start: float,
    form: Form,
    delay: float,
    bar_seconds: float,
) -> float:
    """Return the swing delay for a note sitting on a half beat."""

    section = _section_at(form, start, bar_seconds)
    if section is None:
        return 0.0
    local_beats = (start - section.start_bar * bar_seconds) / form.seconds_per_beat
    fraction = local_beats % 1.0
    if abs(fraction - 0.5) <= 0.08:
        return delay
    return 0.0


def _apply_dynamics(
    instrument: "pretty_midi.Instrument",
    form: Form,
    style: Style,
    plan: "VariationPlan",
    part: str,
    bar_seconds: float,
) -> None:
    if style.phrase_dynamic <= 0.0 and style.metric_accent <= 0.0:
        return
    for note in instrument.notes:
        section = _section_at(form, note.start, bar_seconds)
        if section is None:
            continue
        if plan.role_for(section.name, part) != "support":
            continue
        offset = _dynamic_offset(style, note.start, form, section, part, bar_seconds)
        note.velocity = int(max(1, min(127, round(note.velocity + offset))))


def _dynamic_offset(
    style: Style,
    start: float,
    form: Form,
    section: SectionPlan,
    part: str,
    bar_seconds: float,
) -> float:
    local_beats = (start - section.start_bar * bar_seconds) / form.seconds_per_beat
    # A bar boundary can land a hair below the integer because of floating-point
    # seconds; absorb that before choosing the phrase position.
    local_bar = int(local_beats / form.beats_per_bar + 1e-9)
    beat = max(0.0, local_beats - local_bar * form.beats_per_bar)
    offset = phrase_dynamic_offset(style, local_bar)
    offset += metric_accent(style, beat, part)
    if part == "drums":
        # Keep the phrase movement under the kit rather than on top of it.
        offset = phrase_dynamic_offset(style, local_bar) * 0.60 + metric_accent(
            style, beat, part
        )
    return offset


def _section_at(form: Form, start: float, bar_seconds: float) -> SectionPlan | None:
    for section in form.sections:
        if section.start_bar * bar_seconds - 1e-9 <= start < (
            section.end_bar * bar_seconds
        ) - 1e-9:
            return section
    return None
