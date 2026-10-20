"""Style parameter sets.

Styles deliberately share one composer path.  A style changes tempo, harmony
colour, voicings, dynamics, timing feel and later the rhythm-section settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    name: str
    tempo_range: tuple[int, int]
    target_seconds: float
    intro_bars: int
    outro_bars: int
    comp_style: str
    seventh_probability: float
    ninth_probability: float
    upper_voices: int
    upper_floor: int
    upper_ceiling: int
    upper_gap: int
    swing_ratio: float
    humanize_ms: tuple[int, int]
    velocity_floor: int
    velocity_ceiling: int
    velocity_curve: float
    pedal_changes_per_bar: int
    chord_roll_ms: tuple[int, int]
    reverb_room: float
    reverb_damping: float
    reverb_level: float
    target_lufs: float

    def tempo_for(self, avg_complexity: float, rng_value: float) -> int:
        low, high = self.tempo_range
        tempo = low + (high - low) * avg_complexity
        tempo += (rng_value * 2.0 - 1.0) * 2.0
        return max(58, min(132, round(tempo)))


CINEMATIC = Style(
    name="cinematic",
    tempo_range=(70, 104),
    target_seconds=188.0,
    intro_bars=8,
    outro_bars=8,
    comp_style="wide_roll",
    seventh_probability=0.42,
    ninth_probability=0.18,
    upper_voices=4,
    upper_floor=52,
    upper_ceiling=88,
    upper_gap=14,
    swing_ratio=0.0,
    humanize_ms=(9, 21),
    velocity_floor=32,
    velocity_ceiling=106,
    velocity_curve=1.0,
    pedal_changes_per_bar=1,
    chord_roll_ms=(4, 16),
    reverb_room=0.78,
    reverb_damping=0.34,
    reverb_level=0.56,
    target_lufs=-16.0,
)

LOFI = Style(
    name="lofi",
    tempo_range=(74, 92),
    target_seconds=164.0,
    intro_bars=8,
    outro_bars=8,
    comp_style="swung_comp",
    seventh_probability=0.96,
    ninth_probability=0.55,
    upper_voices=4,
    upper_floor=52,
    upper_ceiling=80,
    upper_gap=9,
    swing_ratio=0.60,
    humanize_ms=(11, 24),
    velocity_floor=35,
    velocity_ceiling=84,
    velocity_curve=0.85,
    pedal_changes_per_bar=2,
    chord_roll_ms=(5, 18),
    reverb_room=0.62,
    reverb_damping=0.52,
    reverb_level=0.48,
    target_lufs=-16.0,
)

STYLES: dict[str, Style] = {CINEMATIC.name: CINEMATIC, LOFI.name: LOFI}


def get_style(name: str) -> Style:
    try:
        return STYLES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown style {name!r}; choose from {', '.join(sorted(STYLES))}."
        ) from exc
