"""Analyze and compare repository-driven musical identities."""

from __future__ import annotations

import argparse
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from symphony.analyze import analyze_repository, resolve_repository, write_profile
from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import STYLES


@dataclass(frozen=True)
class Identity:
    name: str
    key: str
    mode: str
    tempo: int
    meter: str
    progressions: tuple[str, ...]
    rhythms: tuple[str, ...]
    signature: str
    hook: tuple[int, ...]


def _identity(source: str, style_name: str) -> Identity:
    repository = resolve_repository(source)
    raw_profile = analyze_repository(repository, name=Path(source.rstrip("/")).name or repository.name)
    with tempfile.TemporaryDirectory(prefix="symphony-contrast-") as temporary:
        path = write_profile(raw_profile, Path(temporary) / "profile.json")
        profile = load_profile(path)
    composition = build_composition(profile, STYLES[style_name], 0)
    plan = composition.variation_plan
    return Identity(
        name=profile.name,
        key=composition.form.key.label,
        mode=composition.form.key.mode,
        tempo=composition.form.tempo,
        meter=f"{plan.meter[0]}/{plan.meter[1]}",
        progressions=tuple(identifier for _, identifier, _ in plan.progressions),
        rhythms=tuple(identifier for _, identifier in plan.rhythm_patterns),
        signature=plan.signature_id,
        hook=plan.hook_contour,
    )


def distance(left: Identity, right: Identity) -> tuple[int, str]:
    differences: list[str] = []
    if left.key != right.key:
        differences.append("key")
    if left.mode != right.mode:
        differences.append("mode")
    if abs(left.tempo - right.tempo) >= 6:
        differences.append("tempo")
    if left.meter != right.meter:
        differences.append("meter")
    progression_delta = sum(a != b for a, b in zip(left.progressions, right.progressions))
    if progression_delta >= 2:
        differences.append(f"progressions({progression_delta}/6)")
    rhythm_delta = sum(a != b for a, b in zip(left.rhythms, right.rhythms))
    if rhythm_delta >= 2:
        differences.append(f"rhythms({rhythm_delta}/6)")
    if left.signature != right.signature:
        differences.append("signature")
    if left.hook != right.hook:
        differences.append("hook-contour")
    return len(differences), ",".join(differences) or "shared"


def compare(sources: Sequence[str], style_name: str, *, threshold: int = 4) -> tuple[str, bool]:
    identities = [_identity(source, style_name) for source in sources]
    rows: list[tuple[str, str, int, str]] = []
    failed = False
    for index, left in enumerate(identities):
        for right in identities[index + 1 :]:
            value, components = distance(left, right)
            failed |= value < threshold
            rows.append((left.name, right.name, value, components))
    lines = [f"Contrast gate — {style_name} (minimum distance {threshold}/8)",
             "repo A | repo B | distance | differing identity dimensions",
             "---|---|---:|---"]
    lines.extend(f"{a} | {b} | {score}/8 | {fields}" for a, b, score, fields in rows)
    lines.append("IDENTITIES")
    lines.extend(
        f"{item.name}: {item.key}, {item.mode}, {item.tempo} BPM, {item.meter}; "
        f"progressions={','.join(item.progressions)}; rhythms={','.join(item.rhythms)}; "
        f"signature={item.signature}; hook={item.hook}"
        for item in identities
    )
    return "\n".join(lines), not failed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m symphony.contrast")
    parser.add_argument("repositories", nargs="+", help="Local Rust paths or cloneable Git URLs")
    parser.add_argument("--style", choices=sorted(STYLES), default="anthem")
    parser.add_argument("--threshold", type=int, default=4)
    args = parser.parse_args(argv)
    try:
        report, passed = compare(args.repositories, args.style, threshold=args.threshold)
        print(report)
        if not passed:
            print("FAIL: at least one pair is too musically close")
            return 1
        print("PASS: every repository pair clears the contrast threshold")
        return 0
    except Exception as exc:
        parser.exit(2, f"contrast analysis failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
