"""Profile loading and validation.

The Analyzer is deliberately out of scope for this stage.  These dataclasses
mirror the hand-written profiles in ``profiles/`` and give the composer a
small, typed boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProfileError(ValueError):
    """Raised when a profile is missing data or internally inconsistent."""


@dataclass(frozen=True)
class GlobalMetrics:
    total_loc: int
    unsafe_ratio: float
    test_coverage: float
    avg_complexity: float


@dataclass(frozen=True)
class ModuleProfile:
    name: str
    loc: int
    complexity: float
    unsafe_count: int
    depends_on: tuple[str, ...]
    depended_by_count: int
    test_coverage: float
    todo_count: int


@dataclass(frozen=True)
class Profile:
    name: str
    global_metrics: GlobalMetrics
    modules: tuple[ModuleProfile, ...]
    call_path: tuple[str, ...]

    @property
    def modules_by_name(self) -> dict[str, ModuleProfile]:
        return {module.name: module for module in self.modules}

    @property
    def health(self) -> float:
        """A single 0..1 health estimate used for key/mode selection."""

        metrics = self.global_metrics
        return _clamp(
            0.50 * metrics.test_coverage
            + 0.25 * (1.0 - metrics.unsafe_ratio)
            + 0.25 * (1.0 - metrics.avg_complexity),
            0.0,
            1.0,
        )


def load_profile(path: str | Path) -> Profile:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProfileError("Profile root must be a JSON object.")

    try:
        metrics = GlobalMetrics(
            total_loc=_as_int(raw["global"]["total_loc"], "global.total_loc"),
            unsafe_ratio=_as_ratio(raw["global"]["unsafe_ratio"], "global.unsafe_ratio"),
            test_coverage=_as_ratio(
                raw["global"]["test_coverage"], "global.test_coverage"
            ),
            avg_complexity=_as_ratio(
                raw["global"]["avg_complexity"], "global.avg_complexity"
            ),
        )
    except KeyError as exc:
        raise ProfileError(f"Missing field: {exc.args[0]}") from exc

    modules: list[ModuleProfile] = []
    for index, item in enumerate(raw.get("modules", [])):
        prefix = f"modules[{index}]"
        try:
            module = ModuleProfile(
                name=_as_text(item["name"], f"{prefix}.name"),
                loc=_as_int(item["loc"], f"{prefix}.loc"),
                complexity=_as_ratio(item["complexity"], f"{prefix}.complexity"),
                unsafe_count=_as_int(
                    item["unsafe_count"], f"{prefix}.unsafe_count"
                ),
                depends_on=tuple(
                    _as_text(dep, f"{prefix}.depends_on[]")
                    for dep in item.get("depends_on", [])
                ),
                depended_by_count=_as_int(
                    item["depended_by_count"], f"{prefix}.depended_by_count"
                ),
                test_coverage=_as_ratio(
                    item["test_coverage"], f"{prefix}.test_coverage"
                ),
                todo_count=_as_int(item["todo_count"], f"{prefix}.todo_count"),
            )
        except KeyError as exc:
            raise ProfileError(f"Missing field: {prefix}.{exc.args[0]}") from exc
        if module.loc <= 0:
            raise ProfileError(f"{prefix}.loc must be positive.")
        modules.append(module)

    if not modules:
        raise ProfileError("Profile must contain at least one module.")

    names = {module.name for module in modules}
    if len(names) != len(modules):
        raise ProfileError("Module names must be unique.")

    call_path = tuple(
        _as_text(name, "call_path[]") for name in raw.get("call_path", [])
    )
    if not call_path:
        raise ProfileError("call_path must contain at least one module name.")
    missing = sorted(set(call_path) - names)
    if missing:
        raise ProfileError(f"call_path references unknown modules: {missing}")

    name = _as_text(raw.get("name", "untitled"), "name")
    return Profile(name=name, global_metrics=metrics, modules=tuple(modules), call_path=call_path)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_ratio(value: Any, field: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ProfileError(f"{field} must be between 0 and 1 (got {number}).")
    return number


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileError(f"{field} must be an integer.")
    if value < 0:
        raise ProfileError(f"{field} must not be negative.")
    return value


def _as_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{field} must be a non-empty string.")
    return value
