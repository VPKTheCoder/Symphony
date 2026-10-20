"""Scales, functional harmony, chord construction and piano voicing.

Everything in this module is deterministic when given the same arguments and
the same ``random.Random`` instance.  Notes from a scale never leave that scale
unless a caller explicitly builds a chromatic tension later.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

PC_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

MODES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
}

MAJORISH_MODES = ("major", "lydian", "mixolydian")
MINORISH_MODES = ("dorian", "minor", "phrygian")

COMMON_ROOTS = (0, 2, 4, 5, 7, 9, 10)

Progressions = dict[str, dict[str, tuple[tuple[int, ...], ...]]]
PROGRESSIONS: Progressions = {
    "major": {
        "intro": ((1, 4), (1, 5), (1, 6)),
        "main": ((1, 5, 6, 4), (6, 4, 1, 5), (1, 6, 4, 5), (1, 4, 6, 5)),
        "development": ((6, 4, 1, 5), (2, 5, 1, 6), (4, 5, 6, 4), (1, 3, 6, 4)),
        "climax": ((4, 5, 6, 4), (1, 5, 6, 4), (6, 4, 5, 5), (4, 5, 1, 6)),
        "resolution": ((4, 5, 1, 1), (2, 5, 1, 1), (5, 6, 4, 1)),
        "outro": ((1, 4), (1, 5), (1, 6)),
    },
    "lydian": {
        "intro": ((1, 2), (1, 5)),
        "main": ((1, 2, 1, 5), (1, 5, 2, 6), (1, 2, 6, 5)),
        "development": ((2, 5, 1, 6), (6, 2, 1, 5), (1, 6, 2, 5)),
        "climax": ((1, 2, 6, 5), (4, 5, 1, 2), (1, 6, 2, 5)),
        "resolution": ((2, 5, 1, 1), (5, 2, 1, 1), (6, 5, 1, 1)),
        "outro": ((1, 2), (1, 5)),
    },
    "dorian": {
        "intro": ((1, 4), (1, 7), (1, 5)),
        "main": ((1, 4, 1, 7), (1, 4, 5, 7), (1, 7, 4, 1)),
        "development": ((1, 7, 4, 1), (4, 5, 1, 7), (4, 1, 5, 7)),
        "climax": ((4, 5, 1, 7), (1, 7, 4, 5), (4, 5, 7, 1)),
        "resolution": ((4, 1, 5, 1), (7, 4, 1, 1), (5, 1, 1, 1)),
        "outro": ((1, 4), (1, 7)),
    },
    "mixolydian": {
        "intro": ((1, 7), (1, 4), (1, 5)),
        "main": ((1, 7, 4, 1), (1, 4, 1, 7), (1, 4, 5, 7)),
        "development": ((1, 4, 1, 7), (7, 4, 1, 5), (4, 1, 7, 5)),
        "climax": ((4, 5, 1, 1), (1, 7, 4, 5), (4, 1, 7, 1)),
        "resolution": ((4, 1, 7, 1), (7, 4, 1, 1), (5, 4, 1, 1)),
        "outro": ((1, 4), (1, 7)),
    },
    "minor": {
        "intro": ((1, 6), (1, 4), (1, 7)),
        "main": ((1, 6, 3, 7), (1, 4, 7, 3), (1, 7, 6, 7)),
        "development": ((1, 4, 6, 7), (6, 3, 7, 1), (4, 1, 6, 7)),
        "climax": ((4, 6, 7, 1), (1, 6, 3, 7), (4, 7, 1, 1)),
        "resolution": ((4, 5, 1, 1), (6, 7, 1, 1), (7, 3, 6, 1)),
        "outro": ((1, 6), (1, 7)),
    },
    "phrygian": {
        "intro": ((1, 2), (1, 7), (1, 6)),
        "main": ((1, 2, 1, 7), (1, 6, 7, 1), (1, 2, 6, 7)),
        "development": ((1, 7, 6, 2), (1, 2, 7, 1), (6, 7, 1, 2)),
        "climax": ((1, 2, 6, 7), (1, 6, 2, 1), (2, 7, 1, 1)),
        "resolution": ((2, 7, 1, 1), (7, 2, 1, 1), (6, 7, 1, 1)),
        "outro": ((1, 2), (1, 7)),
    },
}


@dataclass(frozen=True)
class Key:
    tonic_pc: int
    mode: str

    @property
    def tonic_name(self) -> str:
        return PC_NAMES[self.tonic_pc % 12]

    @property
    def label(self) -> str:
        return f"{self.tonic_name} {self.mode}"

    @property
    def intervals(self) -> tuple[int, ...]:
        return MODES[self.mode]


@dataclass(frozen=True)
class ChordTone:
    role: str
    pitch_class: int
    semitones_from_root: int


@dataclass(frozen=True)
class Chord:
    degree: int
    root_pc: int
    tones: tuple[ChordTone, ...]
    symbol: str
    quality: str
    suspended: bool = False

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple(tone.pitch_class for tone in self.tones)

    def role_pc(self, role: str) -> int | None:
        for tone in self.tones:
            if tone.role == role:
                return tone.pitch_class
        return None

    def has_role(self, role: str) -> bool:
        return any(tone.role == role for tone in self.tones)


def choose_key(
    health: float,
    rng: random.Random,
    bright_mode_probability: float = 0.0,
) -> Key:
    """Pick a mode family from health, then a key from the seeded RNG."""

    if bright_mode_probability > 0.0 and rng.random() < bright_mode_probability:
        mode = rng.choice(MAJORISH_MODES)
    elif health >= 0.70:
        mode = "major" if rng.random() < 0.68 else "lydian"
    elif health >= 0.48:
        mode = "dorian" if rng.random() < 0.55 else "mixolydian"
    else:
        mode = "minor" if rng.random() < 0.62 else "phrygian"

    tonic_pc = COMMON_ROOTS[rng.randrange(len(COMMON_ROOTS))]
    return Key(tonic_pc=tonic_pc, mode=mode)


def pick_progression(key: Key, role: str, rng: random.Random) -> tuple[int, ...]:
    choices = PROGRESSIONS[key.mode][role]
    return choices[rng.randrange(len(choices))]


def build_chord(
    key: Key,
    degree: int,
    *,
    seventh: bool = False,
    ninth: bool = False,
    add9: bool = False,
    eleventh: bool = False,
    sus4: bool = False,
) -> Chord:
    """Stack scale thirds (and optional extensions) from a scale degree."""

    root_abs = _degree_semitones(key, degree)
    specs: list[tuple[str, int]] = [("root", degree)]
    if sus4:
        specs.append(("fourth", degree + 3))
    else:
        specs.append(("third", degree + 2))
    specs.append(("fifth", degree + 4))
    if seventh or ninth or eleventh:
        specs.append(("seventh", degree + 6))
    if (ninth or add9) and not _would_be_flat_nine(key, degree):
        specs.append(("ninth", degree + 8))
    if eleventh:
        specs.append(("eleventh", degree + 10))

    tones: list[ChordTone] = []
    for role, scale_degree in specs:
        absolute = _degree_semitones(key, scale_degree)
        tones.append(
            ChordTone(
                role=role,
                pitch_class=(key.tonic_pc + absolute) % 12,
                semitones_from_root=absolute - root_abs,
            )
        )

    by_role = {tone.role: tone for tone in tones}
    third = by_role.get("third")
    fifth = by_role["fifth"]
    triad_quality = _triad_quality(
        third.semitones_from_root % 12 if third else None,
        fifth.semitones_from_root % 12,
    )
    if sus4:
        triad_quality = "sus4"

    seventh_tone = by_role.get("seventh")
    ninth_tone = by_role.get("ninth")
    eleventh_tone = by_role.get("eleventh")
    base_suffix = {
        "major": "",
        "minor": "m",
        "dim": "dim",
        "aug": "aug",
        "sus4": "sus4",
    }.get(triad_quality, "")
    suffix = base_suffix
    if seventh_tone:
        seventh_interval = seventh_tone.semitones_from_root % 12
        if triad_quality == "major":
            suffix = "maj7" if seventh_interval == 11 else "7"
        elif triad_quality == "minor":
            suffix = "m7" if seventh_interval == 10 else "mMaj7"
        elif triad_quality == "dim":
            suffix = "dim7" if seventh_interval == 9 else "m7b5"
        else:
            suffix = f"{base_suffix}7"
    if ninth_tone:
        if seventh_tone and triad_quality == "major" and suffix == "maj7":
            suffix = "maj9"
        elif seventh_tone and triad_quality == "major":
            suffix = "9"
        elif seventh_tone and triad_quality == "minor" and suffix == "m7":
            suffix = "m9"
        else:
            suffix = f"{suffix}9"
    elif add9:
        suffix = f"{suffix}add9"
    if eleventh_tone:
        suffix = f"{suffix}11"

    root_name = PC_NAMES[(key.tonic_pc + root_abs) % 12]
    return Chord(
        degree=degree,
        root_pc=(key.tonic_pc + root_abs) % 12,
        tones=tuple(tones),
        symbol=f"{root_name}{suffix}",
        quality=triad_quality,
        suspended=sus4,
    )


def scale_pitches(key: Key, low: int, high: int) -> list[int]:
    return [pitch for pitch in range(low, high + 1) if pitch % 12 in _scale_pcs(key)]


def nearest_pitch_with_pc(
    pitch_class: int,
    target: int,
    low: int,
    high: int,
) -> int:
    candidates = [
        pitch
        for pitch in range(max(0, low), min(127, high) + 1)
        if pitch % 12 == pitch_class % 12
    ]
    if not candidates:
        raise ValueError("No pitch with the requested class fits that range.")
    return min(candidates, key=lambda pitch: (abs(pitch - target), pitch))


def voice_upper(
    chord: Chord,
    *,
    low: int,
    high: int,
    previous: tuple[int, ...] | None,
    target_top: float,
    voices: int,
    max_gap: int,
    rng: random.Random,
) -> tuple[int, ...]:
    """Choose a wide upper voicing with smooth rank-to-rank movement.

    The search is exhaustive but tiny: typically 12-18 candidate pitches and
    four voices.  This keeps voice-leading deterministic and avoids the
    "every chord in root position" sound.
    """

    pitch_classes = set(chord.pitch_classes)
    candidates = [p for p in range(low, high + 1) if p % 12 in pitch_classes]
    if len(candidates) < voices:
        candidates = [p for p in range(low - 12, high + 13) if p % 12 in pitch_classes]

    essential = {
        chord.role_pc("third"),
        chord.role_pc("fourth"),
        chord.role_pc("seventh"),
        chord.role_pc("ninth"),
    }
    essential.discard(None)
    required_count = min(len(pitch_classes), voices)
    desired_span = min(24.0, max(9.0, max_gap * (voices - 1) * 0.55))

    best: tuple[float, tuple[int, ...]] | None = None
    for combo in itertools.combinations(candidates, voices):
        spans = [b - a for a, b in zip(combo, combo[1:])]
        if not spans or min(spans) < 2 or max(spans) > max_gap:
            continue
        span = combo[-1] - combo[0]
        if span < 7 or span > 30:
            continue
        pcs = {pitch % 12 for pitch in combo}
        if len(pcs) < required_count or not essential.issubset(pcs):
            continue

        score = 0.0
        score += abs(combo[-1] - target_top) * 0.85
        score += abs(span - desired_span) * 0.32
        score += max(0, 62 - combo[0]) * 0.35

        # Prefer a comfortable hand shape and avoid too many seconds.
        score += sum(2.5 for gap in spans if gap <= 2)
        score += sum(0.35 for gap in spans if gap >= max_gap - 1)

        if previous is not None and len(previous) == voices:
            movements = [abs(new - old) for old, new in zip(previous, combo)]
            score += sum(movements) * 0.55
            score += movements[-1] * 1.25
            score += max(0.0, movements[-1] - 5.0) * 2.2
            score += abs(sum(combo) / voices - sum(previous) / voices) * 0.18
            common_pcs = {p % 12 for p in previous} & pcs
            score -= len(common_pcs) * 0.8
        else:
            score += abs(sum(combo) / voices - desired_span / 2 - low) * 0.04

        score += rng.random() * 0.9
        if best is None or score < best[0]:
            best = (score, combo)

    if best is None:
        raise ValueError(
            f"Could not voice {chord.symbol} in [{low}, {high}] with {voices} voices."
        )

    return best[1]


def choose_bass(
    chord: Chord,
    *,
    previous: int | None,
    center: int,
    rng: random.Random,
) -> int:
    """Pick a root in a warm left-hand register with modest root movement."""

    candidates = [
        pitch for pitch in range(36, 48) if pitch % 12 == chord.root_pc % 12
    ]
    if not candidates:
        candidates = [((chord.root_pc - 36) % 12) + 36]

    best: tuple[float, int] | None = None
    for pitch in candidates:
        score = abs(pitch - center) * 0.9
        if previous is not None:
            movement = abs(pitch - previous)
            score += movement * 1.15
            score += max(0, movement - 7) * 1.8
        score += rng.random() * 0.55
        if best is None or score < best[0]:
            best = (score, pitch)

    assert best is not None
    return best[1]


def chord_tone_near(
    chord: Chord,
    *,
    target: int,
    low: int,
    high: int,
    rng: random.Random,
    avoid: int | None = None,
) -> int:
    """Choose a chord tone near a register target (used for small replies)."""

    pcs = chord.pitch_classes
    candidates = [
        pitch
        for pitch in range(low, high + 1)
        if pitch % 12 in pcs and pitch != avoid
    ]
    if not candidates:
        return nearest_pitch_with_pc(chord.root_pc, target, low, high)
    return min(candidates, key=lambda pitch: (abs(pitch - target), rng.random()))


def _triad_quality(third_semitones: int | None, fifth_semitones: int) -> str:
    if third_semitones == 4 and fifth_semitones == 7:
        return "major"
    if third_semitones == 3 and fifth_semitones == 7:
        return "minor"
    if third_semitones == 3 and fifth_semitones == 6:
        return "dim"
    if third_semitones == 4 and fifth_semitones == 8:
        return "aug"
    return ""


def _scale_pcs(key: Key) -> set[int]:
    return {(key.tonic_pc + interval) % 12 for interval in key.intervals}


def _degree_semitones(key: Key, scale_degree: int) -> int:
    index = scale_degree - 1
    octave, step = divmod(index, 7)
    return octave * 12 + key.intervals[step]


def _would_be_flat_nine(key: Key, degree: int) -> bool:
    root = _degree_semitones(key, degree)
    ninth = _degree_semitones(key, degree + 8)
    return (ninth - root) % 12 == 1
