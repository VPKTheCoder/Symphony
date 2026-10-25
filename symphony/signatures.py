"""Normalized repository feature extremes mapped to curated music gestures."""

from __future__ import annotations

from dataclasses import dataclass
import math

from symphony.profile import Profile


@dataclass(frozen=True)
class Signature:
    id: str
    name: str
    reason: str
    score: float

    @property
    def label(self) -> str:
        return f"Signature: {self.name}, because {self.reason}"


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _saturate(value: float, scale: float) -> float:
    value = max(0.0, value)
    return value / (value + scale) if value else 0.0


def normalized_signature_scores(profile: Profile) -> dict[str, float]:
    features = profile.rust_features
    metrics = profile.global_metrics
    loc = max(1, metrics.total_loc)
    functions = max(1, int(features.get("function_count", 0)))
    unsafe = metrics.unsafe_ratio
    todos = float(features.get("todo_count", sum(item.todo_count for item in profile.modules)))
    module_count = int(features.get("module_count", len(profile.modules)))
    result_load = (
        float(features.get("try_operators_per_100_functions", 0.0))
        + float(features.get("result_types_per_100_functions", 0.0))
        + float(features.get("unwrap_expect_panic_per_100_functions", 0.0)) * 0.55
    )
    traits_load = (
        float(features.get("traits_per_100_functions", 0.0))
        + float(features.get("impls_per_100_functions", 0.0))
        + float(features.get("generics_per_100_functions", 0.0))
        + float(features.get("lifetimes_per_100_functions", 0.0)) * 0.4
    )
    iterator_load = float(features.get("iterator_calls_per_100_functions", 0.0))
    max_chain = float(features.get("max_iterator_chain_length", 0.0))
    dependency_hub = float(features.get("dependency_hub_concentration", 0.0))
    todo_per_kloc = 1000.0 * todos / loc
    return {
        "unsafe": _bounded(unsafe / 0.05),
        "complexity": _bounded(metrics.avg_complexity),
        "result": _saturate(result_load, 34.0),
        "traits_generics": _saturate(traits_load, 28.0),
        "async": _bounded(float(features.get("async_fn_ratio", 0.0)) / 0.5),
        "iterator": _bounded(0.45 * max(0.0, max_chain - 2.0) / 6.0 + 0.55 * _saturate(iterator_load, 18.0)),
        "todos": _saturate(todo_per_kloc, 4.0),
        "hub": _bounded((dependency_hub - 0.1) / 0.75),
        "sprawl": _bounded(
            0.60 * math.log1p(loc) / math.log1p(250_000)
            + 0.40 * module_count / 14.0
        ),
        "clean": _bounded(
            metrics.test_coverage
            * max(0.0, 1.0 - unsafe / 0.05)
            * max(0.0, 1.0 - todo_per_kloc / 20.0)
        ),
    }


def choose_signature(profile: Profile) -> Signature:
    scores = normalized_signature_scores(profile)
    feature = max(scores, key=lambda name: (scores[name], -tuple(scores).index(name)))
    reasons = {
        "unsafe": ("tritone riff with violin tremolo and a dark pedal drone", "unsafe-heavy"),
        "complexity": ("odd-meter accents and busy hats", "complexity-heavy"),
        "result": ("call-and-response phrases that stumble, then recover", "Result-heavy"),
        "traits_generics": ("canon on the hook", "trait-heavy"),
        "async": ("syncopated interlocking layers", "async-heavy"),
        "iterator": ("flowing scalar runs and rising sequences", "iterator-heavy"),
        "todos": ("suspended chords and a hanging final note", "TODO-heavy"),
        "hub": ("pedal-tone bass drone", "dependency-hub-heavy"),
        "sprawl": ("grand slow build with a climax key change", "large and sprawling"),
        "clean": ("heroic resolved cadences and a soaring lead", "clean and well-tested"),
    }
    name, reason = reasons[feature]
    return Signature(feature, name, reason, scores[feature])
