"""Deterministic phrase-grammar melody engine.

The repository fingerprint supplies a short, singable four-bar hook.  Lead
lines are assembled from antecedent/consequent phrases derived from that hook:
the question ends on a non-tonic chord tone, the answer keeps the opening shape
and resolves to the tonic.  Module names only colour the hook with small
inflections, so a listener hears one identity rather than unrelated tunes.

The engine knows nothing about FluidSynth.  It emits :class:`MelodyEvent`
objects on the composer's four-beat construction grid, which instrument
renderers turn into MIDI.  That keeps the grammar testable and deterministic.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from symphony.theory import MODES, Chord, Key, build_chord

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids import cycles
    from symphony.form import Form, SectionPlan
    from symphony.styles import Style
    from symphony.variation import VariationPlan


@dataclass(frozen=True)
class Hook:
    """The fingerprint-pinned melodic identity of a repository."""

    id: str
    degrees: tuple[int, ...]
    beats: tuple[float, ...]
    durations: tuple[float, ...]
    split: int
    phrase_bars: int = 4

    @property
    def antecedent(self) -> tuple[int, ...]:
        return self.degrees[: self.split]

    @property
    def consequent(self) -> tuple[int, ...]:
        return self.degrees[self.split :]


@dataclass(frozen=True)
class MelodyEvent:
    beat: float
    duration: float
    degree: int
    phrase: int
    phrase_role: str
    is_hook: bool
    velocity: int


@dataclass(frozen=True)
class MelodyQuality:
    step_ratio: float
    leap_recovery: float
    rest_ratio: float
    hook_ratio: float
    phrase_count: int
    octave_leaps: int
    tritones: int
    clean: bool
    prepared_ratio: float = 0.0
    strong_chord_ratio: float = 0.0
    degree_step_ratio: float = 0.0

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "step_ratio": self.step_ratio,
            "leap_recovery": self.leap_recovery,
            "rest_ratio": self.rest_ratio,
            "hook_ratio": self.hook_ratio,
            "phrase_count": self.phrase_count,
            "octave_leaps": self.octave_leaps,
            "tritones": self.tritones,
            "clean": self.clean,
            "prepared_ratio": self.prepared_ratio,
            "strong_chord_ratio": self.strong_chord_ratio,
            "degree_step_ratio": self.degree_step_ratio,
        }


@dataclass(frozen=True)
class _PitchSpec:
    candidates: tuple[int, ...]
    intended_pc: int
    chord_pcs: frozenset[int]
    strong: bool
    target: float


# Four-bar hook rhythms.  Each row holds ten onsets: a five-note question, a
# breath, then a five-note answer.  The final note is held and leaves roughly
# one beat of air before the next phrase.
_HOOK_RHYTHMS: tuple[tuple[tuple[float, ...], tuple[float, ...]], ...] = (
    (
        (0.0, 1.5, 2.5, 4.0, 6.0, 8.0, 9.5, 10.5, 12.0, 14.0),
        (1.25, 0.70, 1.20, 1.70, 1.35, 1.25, 0.70, 1.25, 1.70, 1.05),
    ),
    (
        (0.0, 1.0, 2.0, 3.5, 6.0, 8.0, 9.0, 10.5, 12.5, 14.0),
        (0.80, 0.90, 1.30, 1.90, 1.55, 0.80, 0.90, 1.60, 1.25, 1.00),
    ),
    (
        (0.0, 1.5, 3.0, 4.5, 6.5, 8.5, 10.0, 11.0, 12.5, 14.0),
        (1.20, 1.00, 1.10, 1.70, 1.20, 1.10, 0.70, 1.20, 1.20, 1.55),
    ),
)

_LEAD_RANGES = {"violin": (55, 103), "guitar": (40, 76), "piano": (60, 96)}

# Curated four-bar hook shapes.  Each row is question (five notes) plus answer
# (five notes).  The question ends away from the tonic; the answer keeps the
# opening and cadences to the tonic, either down to scale degree 0 or up to the
# octave.  Intervals are steps except for one prepared leap in the leap variants.
_HOOK_FAMILIES: tuple[tuple[int, ...], ...] = (
    (2, 3, 4, 3, 2, 2, 3, 2, 1, 0),
    (2, 3, 5, 4, 3, 2, 3, 2, 1, 0),
    (4, 5, 6, 5, 4, 4, 5, 5, 6, 7),
    (4, 5, 7, 6, 5, 4, 5, 5, 6, 7),
    (4, 3, 2, 3, 4, 4, 3, 2, 1, 0),
)

_SECTION_TARGETS = {
    "intro": 65.0,
    "theme": 69.0,
    "development": 73.0,
    "climax": 83.0,
    "resolution": 70.0,
    "outro": 64.0,
}

# The lead stays below its true apex outside the climax, so the single highest
# note of the piece belongs to the climax.
_NON_CLIMAX_CEILING = {"violin": 84, "guitar": 69, "piano": 85}
_CLIMAX_CEILING = {"violin": 100, "guitar": 76, "piano": 94}


def build_hook(identity: str, module_names: tuple[str, ...]) -> Hook:
    """Build a four-bar question/answer hook from the repository fingerprint."""

    material = (identity + "|" + "|".join(module_names) + "|phrase-hook").encode("utf-8")
    digest = hashlib.sha256(material).digest()
    beats, durations = _HOOK_RHYTHMS[digest[8] % len(_HOOK_RHYTHMS)]
    degrees = _HOOK_FAMILIES[digest[9] % len(_HOOK_FAMILIES)]
    hook_id = hashlib.sha256(
        (identity + "|" + "|".join(module_names) + "|hook-id").encode("utf-8")
    ).hexdigest()[:12]
    return Hook(
        id=hook_id,
        degrees=degrees,
        beats=beats,
        durations=durations,
        split=5,
    )


def build_lead_line(
    form: "Form",
    section: "SectionPlan",
    plan: "VariationPlan",
    style: "Style",
    part: str,
    *,
    phrase_bars: int = 4,
) -> tuple[MelodyEvent, ...]:
    """Assemble a section's lead line from hook and answering phrases."""

    hook = _plan_hook(plan)
    if not hook.degrees or part not in _LEAD_RANGES:
        return ()
    phrase_bars = 4 if phrase_bars >= 4 else 2
    phrase_count = max(1, math.ceil(section.bars / phrase_bars))
    events: list[MelodyEvent] = []
    for phrase_index in range(phrase_count):
        local_start = phrase_index * phrase_bars
        local_bars = min(phrase_bars, section.bars - local_start)
        if local_bars <= 0:
            continue
        kind = _phrase_kind(section.name, phrase_index)
        if kind == "rest":
            continue
        if kind == "inflection":
            phrase_events = _inflection_phrase(
                hook, plan, section, local_start, phrase_index,
                _module_for_phrase(section, local_start),
            )
        elif kind in {"hook", "hook_variation"}:
            phrase_events = _hook_phrase(
                hook, plan, section, local_start, local_bars,
                phrase_index, variation=kind == "hook_variation",
            )
        else:
            phrase_events = _answer_phrase(
                hook, plan, section, local_start, local_bars, phrase_index
            )
        events.extend(phrase_events)
    events = _limit_density(events, style, part, section)
    return tuple(_shape_velocities(events, section, style, part))


def build_hook_fragment(
    form: "Form",
    section: "SectionPlan",
    plan: "VariationPlan",
    style: "Style",
    part: str = "piano",
    *,
    bars: int = 2,
    bar_offset: int = 0,
) -> tuple[MelodyEvent, ...]:
    """A short statement of the hook's question for piano or outro."""

    hook = _plan_hook(plan)
    if not hook.degrees:
        return ()
    cutoff = bars * 4.0
    selected = [
        (degree, beat, duration)
        for degree, beat, duration in zip(hook.degrees, hook.beats, hook.durations)
        if beat < cutoff
    ]
    base = (section.start_bar + bar_offset) * 4.0
    events = [
        MelodyEvent(
            beat=base + beat,
            duration=min(duration, max(0.5, cutoff - beat - 0.2)),
            degree=degree,
            phrase=0,
            phrase_role="antecedent",
            is_hook=True,
            velocity=0,
        )
        for degree, beat, duration in selected
    ]
    return tuple(_shape_velocities(events, section, style, part))


def pitch_for_event(
    form: "Form",
    section: "SectionPlan",
    event: MelodyEvent,
    part: str,
    style: "Style",
    *,
    previous_pitch: int | None = None,
    previous_leap: int = 0,
) -> int:
    """Turn a scale-degree event into a playable, chord-aware MIDI pitch."""

    low, high = _LEAD_RANGES[part]
    high = min(
        high,
        _CLIMAX_CEILING[part] if section.name == "climax" else _NON_CLIMAX_CEILING[part],
    )
    bar = min(max(0, section.bars - 1), max(0, int(_section_relative_beat(section, event) // 4.0)))
    # Sevenths count as chord tones: the piano and guitar usually colour the
    # harmony, so the melody should not be nudged off a consonant seventh.
    chord = build_chord(form.key, section.degrees[bar], seventh=True)
    strong = _is_strong_beat(event.beat)
    target = _register_target(section, style, part, event, event.degree)
    pitch = _best_pitch(form.key, event.degree, target, low, high, previous_pitch)
    if strong:
        # Keep the phrase's scale degree; nudge the pitch class to the nearest
        # chord tone on strong beats instead of rewriting the contour.
        pitch = _nearest_chord_tone(pitch, chord, low, high, previous_pitch)
    return _smooth_pitch(
        pitch, previous_pitch, previous_leap, form.key, low, high,
        chord if strong else None,
    )


def plan_pitches(
    form: "Form",
    section: "SectionPlan",
    events: tuple[MelodyEvent, ...],
    part: str,
    style: "Style",
    *,
    previous_pitch: int | None = None,
) -> list[int]:
    """Choose a whole lead line with a small deterministic beam search.

    The search balances five things at once: stay near the section's register,
    put chord tones on strong beats, move by step, prepare and resolve leaps,
    and keep the written hook contour.  Choosing pitches note-by-note cannot see
    the next interval; a short beam keeps the phrase singable.
    """

    if not events:
        return []
    low, high = _LEAD_RANGES[part]
    high = min(
        high,
        _CLIMAX_CEILING[part] if section.name == "climax" else _NON_CLIMAX_CEILING[part],
    )
    scale_pcs = frozenset((form.key.tonic_pc + interval) % 12 for interval in MODES[form.key.mode])
    specs: list[_PitchSpec] = []
    for event in events:
        bar = min(
            max(0, section.bars - 1),
            max(0, int(_section_relative_beat(section, event) // 4.0)),
        )
        chord = build_chord(form.key, section.degrees[bar], seventh=True)
        chord_pcs = frozenset(pc for pc in chord.pitch_classes if pc in scale_pcs)
        intended_pc = _scale_pc(form.key, event.degree)
        strong = _is_strong_beat(event.beat)
        target = _register_target(section, style, part, event, event.degree)
        allowed = set(chord_pcs) if strong and chord_pcs else set(scale_pcs)
        candidates = tuple(
            pitch
            for pitch in range(low, high + 1)
            if pitch % 12 in allowed and abs(pitch - target) <= 14
        )
        if not candidates:
            candidates = (
                _best_pitch(form.key, event.degree, target, low, high, previous_pitch),
            )
        specs.append(
            _PitchSpec(
                candidates=candidates,
                intended_pc=intended_pc,
                chord_pcs=chord_pcs,
                strong=strong,
                target=target,
            )
        )

    # State is (previous-previous pitch, previous pitch).  Future cost only
    # depends on the last two notes, so one best path per state is enough.
    states: dict[tuple[int | None, int | None], tuple[float, tuple[int, ...]]] = {
        (None, previous_pitch): (0.0, ())
    }
    for spec in specs:
        expanded: dict[tuple[int | None, int | None], tuple[float, tuple[int, ...]]] = {}
        for (prev_prev, prev), (cost, sequence) in states.items():
            for candidate in spec.candidates:
                total = (
                    cost
                    + _note_cost(candidate, spec)
                    + _interval_cost(prev_prev, prev, candidate)
                )
                key = (prev, candidate)
                current = expanded.get(key)
                if current is None or total < current[0] - 1e-9:
                    expanded[key] = (total, sequence + (candidate,))
        if not expanded:
            break
        # Keep the search bounded but wide enough to preserve the contour.
        states = dict(
            sorted(expanded.items(), key=lambda item: (item[1][0], item[1][1]))[:96]
        )
    if not states:
        return [previous_pitch or low] * len(events)
    _, best = min(states.values(), key=lambda item: (item[0], item[1]))
    return list(best)


def _note_cost(candidate: int, spec: _PitchSpec) -> float:
    cost = abs(candidate - spec.target) * 0.10
    if spec.strong and candidate % 12 not in spec.chord_pcs:
        cost += 7.0
    if candidate % 12 != spec.intended_pc:
        deviation = min(
            (candidate - spec.intended_pc) % 12,
            (spec.intended_pc - candidate) % 12,
        )
        cost += 2.0 + deviation * 0.85
    elif candidate % 12 in spec.chord_pcs:
        # A tiny reward keeps chord tones on weak beats as well.
        cost -= 0.15
    return cost


def _interval_cost(prev_prev: int | None, prev: int | None, candidate: int) -> float:
    if prev is None:
        return 0.0
    interval = candidate - prev
    distance = abs(interval)
    cost = distance * 0.10
    if distance == 0:
        cost += 0.8
    elif distance <= 2:
        pass
    elif distance <= 4:
        cost += 2.0
    elif distance <= 7:
        cost += 5.0
    else:
        cost += 12.0
    if distance > 12:
        cost += 25.0
    if distance % 12 == 6:
        cost += 30.0

    if prev_prev is not None:
        previous_interval = prev - prev_prev
        if distance >= 3:
            if not (abs(previous_interval) <= 2 and previous_interval * interval > 0):
                cost += 3.5
        if abs(previous_interval) >= 3:
            if not (abs(interval) <= 2 and interval * previous_interval < 0):
                cost += 9.0
    return cost


def render_lead_notes(
    instrument,
    form: "Form",
    section: "SectionPlan",
    plan: "VariationPlan",
    style: "Style",
    part: str,
    *,
    previous_pitch: int | None = None,
) -> int | None:
    """Append a grammar-generated lead line; return its final pitch."""

    events = build_lead_line(form, section, plan, style, part)
    pitches = plan_pitches(form, section, events, part, style)
    overlay = float(getattr(style, "legato_overlap", 0.0) or 0.0)
    for index, (event, pitch) in enumerate(zip(events, pitches)):
        start = event.beat * form.seconds_per_beat
        duration = event.duration * form.seconds_per_beat
        if overlay and event.duration >= 0.5:
            duration += overlay * form.seconds_per_beat
        if part == "guitar":
            start += (index % 3) * 0.004
        start = max(0.0, start)
        end = max(start + 0.06, start + duration)
        instrument.notes.append(
            _note(event.velocity, pitch, start, end)
        )
    return pitches[-1] if pitches else previous_pitch


def render_hook_fragment(
    instrument,
    form: "Form",
    section: "SectionPlan",
    plan: "VariationPlan",
    style: "Style",
    *,
    part: str = "piano",
    bars: int = 2,
    bar_offset: int = 0,
    octave: int = 0,
    velocity_scale: float = 0.82,
) -> None:
    """Append a quiet high-register hook statement to a part."""

    events = build_hook_fragment(
        form, section, plan, style, part, bars=bars, bar_offset=bar_offset
    )
    previous: int | None = None
    overlay = float(getattr(style, "legato_overlap", 0.0) or 0.0)
    for event in events:
        pitch = pitch_for_event(
            form, section, event, part, style, previous_pitch=previous
        )
        pitch = max(_LEAD_RANGES[part][0], min(_LEAD_RANGES[part][1], pitch + octave))
        previous = pitch
        start = event.beat * form.seconds_per_beat
        duration = event.duration * form.seconds_per_beat + overlay * form.seconds_per_beat
        instrument.notes.append(
            _note(max(12, int(event.velocity * velocity_scale)), pitch, start, start + duration)
        )


def melody_quality(
    events: tuple[MelodyEvent, ...],
    form: "Form",
    part: str,
    *,
    section: "SectionPlan | None" = None,
    total_beats: float | None = None,
    style: "Style | None" = None,
) -> MelodyQuality:
    """Score a phrase line for smoothness, space and hook recurrence."""

    if not events:
        return MelodyQuality(1.0, 1.0, 1.0, 0.0, 0, 0, 0, True)
    degrees = [event.degree for event in events]
    degree_intervals = [right - left for left, right in zip(degrees, degrees[1:])]
    degree_steps = sum(1 for interval in degree_intervals if abs(interval) <= 1)
    span_start = events[0].beat
    span_end = max(event.beat + event.duration for event in events)
    if total_beats is not None:
        span_end = max(span_end, span_start + total_beats)
    covered = sum(event.duration for event in events)
    rest_ratio = max(0.0, 1.0 - covered / max(1.0, span_end - span_start))
    hook_ratio = sum(1 for event in events if event.is_hook) / len(events)
    phrases = len({event.phrase for event in events})
    octave_leaps = 0
    tritones = 0
    prepared_ratio = 1.0
    leap_recovery = 1.0
    strong_chord_ratio = 1.0
    step_ratio = degree_steps / max(1, len(degree_intervals))
    if section is not None:
        pitches = plan_pitches(form, section, events, part, style or _DefaultStyle())
        scale_pcs = {
            (form.key.tonic_pc + interval) % 12 for interval in MODES[form.key.mode]
        }
        event_chord_pcs: list[frozenset[int]] = []
        for event in events:
            bar = min(
                max(0, section.bars - 1),
                max(0, int(_section_relative_beat(section, event) // 4.0)),
            )
            chord = build_chord(form.key, section.degrees[bar], seventh=True)
            event_chord_pcs.append(
                frozenset(pc for pc in chord.pitch_classes if pc in scale_pcs)
            )
        pitch_intervals = [right - left for left, right in zip(pitches, pitches[1:])]
        steps = sum(1 for interval in pitch_intervals if abs(interval) <= 2)
        step_ratio = steps / max(1, len(pitch_intervals))
        leap_indices = [
            index for index, interval in enumerate(pitch_intervals)
            if abs(interval) >= 3
        ]
        internal_leaps = [
            index for index in leap_indices
            if events[index].phrase == events[index + 1].phrase
        ]
        prepared = 0
        recovered = 0
        for index in internal_leaps:
            previous = pitch_intervals[index - 1] if index > 0 else None
            arpeggio = (
                abs(pitch_intervals[index]) <= 5
                and pitches[index] % 12 in event_chord_pcs[index]
                and pitches[index + 1] % 12 in event_chord_pcs[index + 1]
            )
            if (
                previous is None
                or events[index - 1].phrase != events[index].phrase
                or arpeggio
                or (abs(previous) <= 2 and previous * pitch_intervals[index] > 0)
            ):
                prepared += 1
            if index + 1 >= len(pitch_intervals):
                recovered += 1
            else:
                following = pitch_intervals[index + 1]
                if (
                    events[index + 1].phrase != events[index + 2].phrase
                    if index + 2 < len(events)
                    else True
                ):
                    recovered += 1
                elif abs(following) <= 2 and following * pitch_intervals[index] < 0:
                    recovered += 1
        prepared_ratio = prepared / len(internal_leaps) if internal_leaps else 1.0
        leap_recovery = recovered / len(internal_leaps) if internal_leaps else 1.0
        for left, right in zip(pitches, pitches[1:]):
            interval = abs(right - left)
            if interval > 12:
                octave_leaps += 1
            if interval % 12 == 6:
                tritones += 1
        strong_total = 0
        strong_tones = 0
        for event, pitch, chord_pcs in zip(events, pitches, event_chord_pcs):
            if not _is_strong_beat(event.beat):
                continue
            strong_total += 1
            if pitch % 12 in chord_pcs:
                strong_tones += 1
        strong_chord_ratio = strong_tones / max(1, strong_total)
    clean = (
        octave_leaps == 0
        and tritones == 0
        and prepared_ratio >= 0.99
        and leap_recovery >= 0.99
    )
    return MelodyQuality(
        step_ratio=step_ratio,
        leap_recovery=leap_recovery,
        rest_ratio=rest_ratio,
        hook_ratio=hook_ratio,
        phrase_count=phrases,
        octave_leaps=octave_leaps,
        tritones=tritones,
        clean=clean,
        prepared_ratio=prepared_ratio,
        strong_chord_ratio=strong_chord_ratio,
        degree_step_ratio=degree_steps / max(1, len(degree_intervals)),
    )


def _plan_hook(plan: "VariationPlan") -> Hook:
    return Hook(
        id=getattr(plan, "hook_id", ""),
        degrees=tuple(getattr(plan, "hook_contour", ()) or ()),
        beats=tuple(getattr(plan, "hook_beats", ()) or ()),
        durations=tuple(getattr(plan, "hook_durations", ()) or ()),
        split=int(getattr(plan, "hook_split", 5) or 5),
    )


def _phrase_kind(section_name: str, phrase_index: int) -> str:
    if section_name in {"intro", "outro"}:
        return "rest" if phrase_index else "hook"
    if section_name == "theme":
        return "hook" if phrase_index % 2 == 0 else "answer"
    if section_name == "development":
        return ("hook_variation", "inflection", "answer", "hook_variation")[phrase_index % 4]
    if section_name == "climax":
        return "hook_variation" if phrase_index % 2 == 0 else "answer"
    if section_name == "resolution":
        return "answer" if phrase_index % 2 == 0 else "hook"
    return "hook" if phrase_index % 2 == 0 else "rest"


def _hook_phrase(
    hook: Hook,
    plan: "VariationPlan",
    section: "SectionPlan",
    local_start: int,
    local_bars: int,
    phrase_index: int,
    *,
    variation: bool,
) -> list[MelodyEvent]:
    degrees = list(hook.degrees)
    beats = list(hook.beats)
    durations = list(hook.durations)
    if variation or section.name == "development":
        degrees = _vary_degrees(degrees, hook.split, plan, phrase_index)
        beats, durations = _displace_rhythm(beats, durations, plan, phrase_index)
    # The climax is lifted by register, not by rewriting the hook's intervals;
    # the highest note of the piece therefore belongs to the climax while the
    # phrase keeps its recognisable shape.
    limit = min(local_bars * 4.0, 15.6)
    return _events_from_grid(
        section, local_start, degrees, beats, durations, phrase_index,
        role="hook", is_hook=True, limit=limit,
    )


def _answer_phrase(
    hook: Hook,
    plan: "VariationPlan",
    section: "SectionPlan",
    local_start: int,
    local_bars: int,
    phrase_index: int,
) -> list[MelodyEvent]:
    # The answer is the hook's own consequent: it keeps the question's opening
    # and settles on the tonic.  Only the phrase's timing is new, so listeners
    # hear one idea answered rather than two unrelated melodies.
    degrees = list(hook.consequent)
    # Question (two notes), short link, then the answer cadence.  The held
    # final note leaves air before the next phrase.
    beats = [0.0, 1.5, 6.0, 8.0, 14.0]
    durations = [1.30, 1.00, 1.30, 1.00, 1.50]
    limit = min(local_bars * 4.0, 15.6)
    return _events_from_grid(
        section, local_start, degrees, beats, durations, phrase_index,
        role="answer", is_hook=False, limit=limit,
    )


def _inflection_phrase(
    hook: Hook,
    plan: "VariationPlan",
    section: "SectionPlan",
    local_start: int,
    phrase_index: int,
    module_name: str,
) -> list[MelodyEvent]:
    """Two-bar module inflection of the hook, followed by a two-bar breath."""

    digest = hashlib.sha256(
        f"{getattr(plan, 'repo_fingerprint', '')}:{module_name}:{phrase_index}:inflection".encode("utf-8")
    ).digest()
    take = 4
    degrees = list(hook.antecedent[:take])
    beats = list(hook.beats[:take])
    durations = list(hook.durations[:take])
    alter_index = digest[0] % len(degrees)
    degrees[alter_index] += 1 if digest[1] % 2 else -1
    degrees = [max(-1, min(8, degree)) for degree in degrees]
    cutoff = 7.4
    return _events_from_grid(
        section, local_start, degrees, beats, durations, phrase_index,
        role="inflection", is_hook=False, limit=cutoff,
    )


def _events_from_grid(
    section: "SectionPlan",
    local_start: int,
    degrees: list[int],
    beats: list[float],
    durations: list[float],
    phrase_index: int,
    *,
    role: str,
    is_hook: bool,
    limit: float,
) -> list[MelodyEvent]:
    base = (section.start_bar + local_start) * 4.0
    result = []
    for degree, beat, duration in zip(degrees, beats, durations):
        if beat >= limit:
            continue
        clipped = min(duration, max(0.25, limit - beat - 0.15))
        result.append(
            MelodyEvent(
                beat=base + beat,
                duration=clipped,
                degree=max(-2, min(14, degree)),
                phrase=phrase_index,
                phrase_role=role,
                is_hook=is_hook,
                velocity=0,
            )
        )
    return result


def _limit_density(
    events: list[MelodyEvent],
    style: "Style",
    part: str,
    section: "SectionPlan",
) -> list[MelodyEvent]:
    """Drop weak ornamental notes when a bar exceeds the style's lead budget."""

    cap = int(getattr(style, "lead_notes_per_bar", 4) or 4)
    if part == "guitar":
        cap = max(2, cap - 1)
    if section.name == "climax":
        cap += 1
    grouped: dict[int, list[MelodyEvent]] = {}
    for event in events:
        bar = int(event.beat // 4.0)
        grouped.setdefault(bar, []).append(event)
    kept: list[MelodyEvent] = []
    for bar in sorted(grouped):
        row = grouped[bar]
        if len(row) <= cap:
            kept.extend(row)
            continue
        # Keep the first attack, all strong-beat notes, and the final held note.
        selected = [row[0]]
        for candidate in row[1:-1]:
            if _is_strong_beat(candidate.beat) and len(selected) < max(1, cap - 2):
                selected.append(candidate)
        if len(selected) < cap:
            selected.append(row[-1])
        kept.extend(sorted(selected, key=lambda item: (item.beat, item.degree)))
    return kept


def _shape_velocities(
    events: list[MelodyEvent],
    section: "SectionPlan",
    style: "Style",
    part: str,
) -> list[MelodyEvent]:
    if not events:
        return []
    peak_degree = max(event.degree for event in events)
    peak_beat = max(
        (event.beat for event in events if event.degree == peak_degree),
        default=events[0].beat,
    )
    base = style.velocity_floor + (
        style.velocity_ceiling - style.velocity_floor
    ) * section.intensity ** style.velocity_curve
    if part == "guitar":
        base -= 4.0
    elif part == "piano":
        base -= 8.0
    result = []
    start = events[0].beat
    for event in events:
        relative = min(
            1.0,
            max(0.0, (event.beat - start) / max(1.0, peak_beat - start)),
        )
        arch = 0.86 + 0.18 * math.sin(math.pi * relative)
        if event.beat >= peak_beat:
            arch -= min(0.10, (event.beat - peak_beat) * 0.008)
        if _is_strong_beat(event.beat):
            arch += 0.04
        velocity = int(round(base * arch))
        result.append(
            MelodyEvent(
                beat=event.beat,
                duration=event.duration,
                degree=event.degree,
                phrase=event.phrase,
                phrase_role=event.phrase_role,
                is_hook=event.is_hook,
                velocity=max(18, min(style.velocity_ceiling + 8, velocity)),
            )
        )
    return result


def _register_target(
    section: "SectionPlan",
    style: "Style",
    part: str,
    event: MelodyEvent,
    resolved_degree: int,
) -> float:
    base = _SECTION_TARGETS.get(section.name, 70.0)
    if part == "guitar":
        base -= 10.0
    elif part == "piano":
        base += 2.0
    base += (style.upper_ceiling - 84.0) * 0.18
    if section.name == "climax":
        base += 4.0
    if event.phrase_role == "answer":
        base += 0.8
    return base + resolved_degree * 0.55


def _vary_degrees(
    degrees: list[int],
    split: int,
    plan: "VariationPlan",
    phrase_index: int,
) -> list[int]:
    """Curated hook transformations; never a fully re-randomized tune."""

    treatment = getattr(plan, "motif_treatment", None) or "repeat"
    if treatment == "invert":
        axis = degrees[0]
        return [max(-1, min(8, 2 * axis - degree)) for degree in degrees]
    if treatment == "transpose":
        return [max(-1, min(8, degree + 1)) for degree in degrees]
    if treatment == "fragment":
        head = degrees[: max(2, split)]
        return head + [max(-1, min(8, degree + 1)) for degree in head]
    if treatment == "extend":
        return [
            max(-1, min(8, degree + (1 if index == len(degrees) - 1 else 0)))
            for index, degree in enumerate(degrees)
        ]
    if phrase_index % 2:
        return [
            max(-1, min(8, degree + (1 if index % 3 == 2 else 0)))
            for index, degree in enumerate(degrees)
        ]
    return degrees


def _displace_rhythm(
    beats: list[float],
    durations: list[float],
    plan: "VariationPlan",
    phrase_index: int,
) -> tuple[list[float], list[float]]:
    """Displace the answer by a half beat without losing the downbeat hook."""

    shift = 0.5 if phrase_index % 2 == 0 else 0.75
    signature = getattr(plan, "signature_id", "")
    if signature == "async":
        shift += 0.25
    if signature == "canon":
        shift += 0.5
    displaced = []
    for index, beat in enumerate(beats):
        if index == 0:
            displaced.append(beat)
        elif beat < 8.0:
            displaced.append(min(7.6, beat + shift))
        else:
            displaced.append(min(15.2, beat + shift))
    return displaced, durations


def _scale_pc(key: Key, degree: int) -> int:
    octave, index = divmod(degree, 7)
    return (key.tonic_pc + MODES[key.mode][index]) % 12


def _best_pitch(
    key: Key,
    degree: int,
    target: float,
    low: int,
    high: int,
    previous: int | None,
) -> int:
    pc = _scale_pc(key, degree)
    candidates = [pitch for pitch in range(low, high + 1) if pitch % 12 == pc]
    if not candidates:
        candidates = [
            pitch for pitch in range(low - 12, high + 13) if pitch % 12 == pc
        ]
    if not candidates:
        return max(low, min(high, round(target)))

    def cost(pitch: int) -> tuple[float, int]:
        distance = abs(pitch - target) * 0.40
        continuity = abs(pitch - previous) * 1.15 if previous is not None else 0.0
        return (distance + continuity, pitch)

    return min(candidates, key=cost)


def _nearest_chord_tone(
    pitch: int,
    chord: Chord,
    low: int,
    high: int,
    previous: int | None,
) -> int:
    """Nudge a strong-beat pitch to the closest chord tone in the mode."""

    if pitch % 12 in chord.pitch_classes:
        return pitch
    window = range(max(low, pitch - 3), min(high, pitch + 3) + 1)
    candidates = [
        candidate for candidate in window
        if candidate % 12 in chord.pitch_classes
    ]
    if not candidates:
        return pitch

    def cost(candidate: int) -> tuple[float, int]:
        motion = abs(candidate - pitch)
        continuity = abs(candidate - previous) if previous is not None else 0
        return (motion * 1.0 + continuity * 0.35, candidate)

    return min(candidates, key=cost)


def _smooth_pitch(
    pitch: int,
    previous: int | None,
    previous_leap: int,
    key: Key,
    low: int,
    high: int,
    chord: Chord | None,
) -> int:
    if previous is None:
        return max(low, min(high, pitch))
    interval = pitch - previous
    while abs(interval) > 12:
        pitch += -12 if interval > 0 else 12
        interval = pitch - previous
    # A pitch-class tritone after octave folding is still harsh.  Prefer the
    # neighbouring scale tone rather than changing the phrase's scale degree
    # wholesale.
    if abs(interval) == 6:
        for offset in (-1, 1, -2, 2):
            candidate = pitch + offset
            if (
                low <= candidate <= high
                and _is_scale_pc(candidate, key)
                and (chord is None or candidate % 12 in chord.pitch_classes)
            ):
                pitch = candidate
                break
    # Every leap is answered by a step in the opposite direction.
    if abs(previous_leap) >= 3 and not (
        abs(interval) <= 2 and interval * previous_leap < 0
    ):
        anchor = previous + (-1 if previous_leap > 0 else 1) * 2
        candidates = [
            candidate
            for candidate in range(max(low, anchor - 2), min(high, anchor + 2) + 1)
            if _is_scale_pc(candidate, key)
            and (chord is None or candidate % 12 in chord.pitch_classes)
            and candidate != previous
        ]
        if candidates:
            pitch = min(
                candidates,
                key=lambda candidate: (
                    abs(candidate - anchor),
                    abs(candidate - pitch),
                    candidate,
                ),
            )
    return max(low, min(high, pitch))


def _is_scale_pc(pitch: int, key: Key) -> bool:
    return pitch % 12 in {(key.tonic_pc + interval) % 12 for interval in MODES[key.mode]}


def _is_strong_beat(beat: float) -> bool:
    within = beat % 4.0
    return abs(within) < 1e-6 or abs(within - 2.0) < 1e-6


def _section_relative_beat(section: "SectionPlan", event: MelodyEvent) -> float:
    return event.beat - section.start_bar * 4.0


def _module_for_phrase(section: "SectionPlan", local_start: int) -> str:
    if not section.modules:
        return "framing"
    if section.bars <= 0:
        return section.modules[0].name
    index = min(
        len(section.modules) - 1,
        int(local_start / section.bars * len(section.modules)),
    )
    return section.modules[index].name


def _note(velocity: int, pitch: int, start: float, end: float):
    import pretty_midi

    return pretty_midi.Note(
        velocity=max(1, min(120, int(velocity))),
        pitch=int(max(0, min(127, pitch))),
        start=float(start),
        end=float(end),
    )


class _DefaultStyle:
    """Fallback used only when a caller asks for melody diagnostics."""

    upper_ceiling = 88
    velocity_floor = 36
    velocity_ceiling = 104
    velocity_curve = 1.0
    lead_notes_per_bar = 4
    legato_overlap = 0.0
