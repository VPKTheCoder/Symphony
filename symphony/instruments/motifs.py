"""Stable, module-name-derived leitmotif shapes shared by lead instruments."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from symphony.form import SectionPlan
from symphony.profile import ModuleProfile


@dataclass(frozen=True)
class MotifEvent:
    beat: float
    duration: float
    degree: int


RHYTHMS = (
    ((0.0, 1.55), (2.0, 0.85), (3.0, 0.78), (4.0, 1.50), (6.0, 0.86), (7.0, 0.80)),
    ((0.0, 1.60), (1.75, 0.72), (3.0, 0.90), (4.5, 1.12), (6.0, 1.62)),
    ((0.0, 1.10), (1.5, 1.16), (3.25, 0.66), (4.0, 1.58), (6.0, 1.82)),
)
CONTOURS = (
    (0, 1, 3, 2, 4, 3, 1, 0),
    (0, 2, 1, 4, 3, 5, 2, 1),
    (0, -1, 2, 4, 3, 1, 2, 0),
    (0, 3, 4, 2, 5, 4, 2, 1),
)


def module_motif(module_name: str) -> tuple[MotifEvent, ...]:
    """Return a curated two-bar motif selected only by a stable name hash."""

    digest = hashlib.sha256(module_name.encode("utf-8")).digest()
    rhythm = RHYTHMS[digest[0] % len(RHYTHMS)]
    contour = CONTOURS[digest[1] % len(CONTOURS)]
    rotation = digest[2] % len(contour)
    degrees = contour[rotation:] + contour[:rotation]
    return tuple(
        MotifEvent(beat, duration, degrees[index % len(degrees)])
        for index, (beat, duration) in enumerate(rhythm)
    )


def module_bar_spans(
    section: SectionPlan,
) -> tuple[tuple[ModuleProfile, int, int], ...]:
    """Assign each module a stable contiguous span of section bars."""

    modules = section.modules
    if not modules or section.bars <= 0:
        return ()
    if len(modules) > section.bars:
        modules = modules[: section.bars]
    remaining = section.bars - len(modules)
    total_weight = sum(max(1, module.loc) for module in modules)
    raw = [remaining * max(1, module.loc) / total_weight for module in modules]
    extras = [int(value) for value in raw]
    left = remaining - sum(extras)
    order = sorted(range(len(modules)), key=lambda i: (raw[i] - extras[i], -i), reverse=True)
    for index in order[:left]:
        extras[index] += 1
    spans = []
    cursor = 0
    for module, extra in zip(modules, extras):
        count = 1 + extra
        spans.append((module, cursor, cursor + count))
        cursor += count
    return tuple(spans)


def developed_degree(degree: int, treatment: str, phrase_index: int) -> int | None:
    """Apply a restrained, diatonic development to a motif phrase."""

    if treatment == "fragment" and phrase_index % 2 == 1 and degree not in (0, 1):
        return None
    if treatment == "transpose" and phrase_index % 2 == 1:
        return degree + 2
    if treatment == "invert" and phrase_index % 2 == 1:
        return 4 - degree
    return degree
