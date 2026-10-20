"""Musical form: section plan, pacing, module grouping and harmony grid."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from symphony.profile import ModuleProfile, Profile
from symphony.styles import Style
from symphony.theory import Key, choose_key, pick_progression

CONTENT_SECTIONS = ("theme", "development", "climax", "resolution")
SECTION_BASE_INTENSITY = {
    "intro": 0.16,
    "theme": 0.46,
    "development": 0.68,
    "climax": 0.95,
    "resolution": 0.52,
    "outro": 0.20,
}
SECTION_LOAD_WEIGHT = {
    "theme": 1.00,
    "development": 1.12,
    "climax": 0.95,
    "resolution": 0.90,
}


@dataclass(frozen=True)
class SectionPlan:
    name: str
    start_bar: int
    bars: int
    intensity: float
    modules: tuple[ModuleProfile, ...]
    degrees: tuple[int, ...]
    bars_per_chord: int
    open_cadence: bool
    is_final: bool = False

    @property
    def end_bar(self) -> int:
        return self.start_bar + self.bars


@dataclass(frozen=True)
class Form:
    key: Key
    tempo: int
    total_bars: int
    sections: tuple[SectionPlan, ...]
    target_seconds: float
    health: float
    open_cadence: bool

    @property
    def beats_per_bar(self) -> int:
        return 4

    @property
    def seconds_per_beat(self) -> float:
        return 60.0 / self.tempo

    @property
    def estimated_seconds(self) -> float:
        return (
            self.total_bars
            * self.beats_per_bar
            * self.seconds_per_beat
        )


def build_form(profile: Profile, style: Style, rng: random.Random) -> Form:
    key = choose_key(profile.health, rng, style.bright_mode_probability)
    tempo = style.tempo_for(profile.global_metrics.avg_complexity, rng.random())

    seconds_per_bar = 4.0 * 60.0 / tempo
    raw_bars = style.target_seconds / seconds_per_bar
    total_bars = int(round(raw_bars / 4.0) * 4)
    total_bars = max(40, min(88, total_bars))

    modules = profile.modules_by_name
    path = [modules[name] for name in profile.call_path]
    grouped = _group_path(path)
    content_bars = total_bars - style.intro_bars - style.outro_bars
    content_bars = max(16, (content_bars // 4) * 4)
    content_bars = min(content_bars, total_bars - style.intro_bars - style.outro_bars)

    if content_bars <= 0:
        content_bars = 16
    bar_allocation = _allocate_bars(
        grouped,
        content_bars,
    )
    # If the clamp produced an awkward remainder, return it to development.
    missing = content_bars - sum(bar_allocation.values())
    if missing:
        bar_allocation["development"] += missing

    open_cadence = profile.global_metrics.test_coverage < 0.55
    progressions = {
        role: pick_progression(key, role, rng)
        for role in ("intro", "main", "development", "climax", "resolution", "outro")
    }

    sections: list[SectionPlan] = []
    start_bar = 0
    role_to_progression = {
        "intro": "intro",
        "theme": "main",
        "development": "development",
        "climax": "climax",
        "resolution": "resolution",
        "outro": "outro",
    }
    role_to_modules = {
        "intro": (),
        "theme": grouped["theme"],
        "development": grouped["development"],
        "climax": grouped["climax"],
        "resolution": grouped["resolution"],
        "outro": (),
    }
    role_bars = {
        "intro": style.intro_bars,
        "theme": bar_allocation["theme"],
        "development": bar_allocation["development"],
        "climax": bar_allocation["climax"],
        "resolution": bar_allocation["resolution"],
        "outro": style.outro_bars,
    }

    for role in ("intro", "theme", "development", "climax", "resolution", "outro"):
        bars = role_bars[role]
        bars_per_chord = 2 if role in ("intro", "outro") else 1
        section_modules = role_to_modules[role]
        intensity = _section_intensity(role, section_modules)
        progression = progressions[role_to_progression[role]]
        degrees = _degrees_for_bars(
            progression,
            bars=bars,
            bars_per_chord=bars_per_chord,
            cadence_tonic=role in ("resolution", "outro"),
        )
        sections.append(
            SectionPlan(
                name=role,
                start_bar=start_bar,
                bars=bars,
                intensity=intensity,
                modules=section_modules,
                degrees=degrees,
                bars_per_chord=bars_per_chord,
                open_cadence=open_cadence and role == "resolution",
                is_final=role == "outro",
            )
        )
        start_bar += bars

    return Form(
        key=key,
        tempo=tempo,
        total_bars=start_bar,
        sections=tuple(sections),
        target_seconds=style.target_seconds,
        health=profile.health,
        open_cadence=open_cadence,
    )


def _group_path(path: list[ModuleProfile]) -> dict[str, tuple[ModuleProfile, ...]]:
    """Split the call path in order across the four content sections."""

    count = len(path)
    if count < 4:
        weights = (1.0, 1.2, 1.0, 0.8)
        allocation = _apportion_units(weights, max(1, count))
        # Keep the path's order, even when a mock profile is unusually short.
        groups: list[list[ModuleProfile]] = [list() for _ in range(4)]
        cursor = 0
        for index, amount in enumerate(allocation):
            groups[index] = path[cursor : cursor + amount]
            cursor += amount
        while cursor < count:
            groups[-1].append(path[cursor])
            cursor += 1
        return {name: tuple(group) for name, group in zip(CONTENT_SECTIONS, groups)}

    weights = (1.00, 1.25, 1.10, 0.85)
    extras = _apportion_units(weights, count - 4)
    counts = [1 + extra for extra in extras]

    groups = []
    cursor = 0
    for amount in counts:
        groups.append(tuple(path[cursor : cursor + amount]))
        cursor += amount
    while cursor < count:
        groups[-1] = groups[-1] + (path[cursor],)
        cursor += 1

    assigned = {
        role: group
        for role, group in zip(CONTENT_SECTIONS, groups)
        if group
    }
    return assigned | {
        role: ()
        for role in CONTENT_SECTIONS
        if role not in assigned
    }


def _allocate_bars(
    grouped: dict[str, tuple[ModuleProfile, ...]],
    total: int,
) -> dict[str, int]:
    minimum = 4
    units_total = max(0, (total - minimum * len(CONTENT_SECTIONS)) // 4)
    weights = []
    for role in CONTENT_SECTIONS:
        loc = sum(module.loc for module in grouped.get(role, ())) or 1
        load = math.sqrt(loc)
        weights.append(load * SECTION_LOAD_WEIGHT[role])

    extra_units = _apportion_units(weights, units_total)
    return {
        role: minimum + 4 * extra
        for role, extra in zip(CONTENT_SECTIONS, extra_units)
    }


def _apportion_units(weights: tuple[float, ...] | list[float], units: int) -> list[int]:
    """Largest-remainder apportionment for integer units."""

    if units <= 0:
        return [0 for _ in weights]
    total_weight = sum(weights)
    if total_weight <= 0:
        return [units // len(weights) for _ in weights]

    raw = [units * weight / total_weight for weight in weights]
    result = [int(math.floor(value)) for value in raw]
    remaining = units - sum(result)
    order = sorted(
        range(len(weights)),
        key=lambda index: (-(raw[index] - result[index]), index),
    )
    for index in order[:remaining]:
        result[index] += 1
    return result


def _degrees_for_bars(
    progression: tuple[int, ...],
    *,
    bars: int,
    bars_per_chord: int,
    cadence_tonic: bool,
) -> tuple[int, ...]:
    degrees = []
    for bar in range(bars):
        chord_index = (bar // bars_per_chord) % len(progression)
        degrees.append(progression[chord_index])
    if cadence_tonic and degrees:
        cadence_start = max(0, bars - bars_per_chord)
        for index in range(cadence_start, bars):
            degrees[index] = 1
    return tuple(degrees)


def _section_intensity(role: str, modules: tuple[ModuleProfile, ...]) -> float:
    base = SECTION_BASE_INTENSITY[role]
    if not modules:
        return base
    complexity = sum(module.complexity for module in modules) / len(modules)
    # Keep the fixed dramatic arc dominant; module data only shapes it slightly
    # until the dedicated tension pass.
    shaped = base + (complexity - 0.5) * 0.08
    return max(0.05, min(1.0, shaped))
