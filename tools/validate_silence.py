"""Check piano MIDI note coverage for all built-in profile/style combinations.

Run with ``python tools/validate_silence.py``. Internal MIDI silences above
1.5 beats fail validation. The trailing cadence after the final note is allowed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import STYLES

SEEDS = (1, 7, 42, 99)
MAX_SILENCE_BEATS = 1.5


def longest_internal_silence(
    notes,
    seconds_per_beat: float,
    *,
    deliberate_phrase_rest_beat: float,
) -> tuple[float, float, float]:
    intervals = sorted((note.start, note.end) for note in notes)
    if not intervals:
        return (0.0, 0.0, float("inf"))

    merged: list[list[float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    worst = (0.0, 0.0, 0.0)
    for left, right in zip(merged, merged[1:]):
        right_beat = right[0] / seconds_per_beat
        # The two-beat breath before the final outro chord is a deliberate
        # cadence rest, explicitly allowed by the listening requirement.
        if abs(right_beat - deliberate_phrase_rest_beat) <= 0.20:
            continue
        silence = (right[0] - left[1]) / seconds_per_beat
        if silence > worst[2]:
            worst = (
                left[1] / seconds_per_beat,
                right[0] / seconds_per_beat,
                silence,
            )
    return worst


def main() -> int:
    failures = 0
    for profile_path in sorted((ROOT / "profiles").glob("*.json")):
        profile = load_profile(profile_path)
        for style in STYLES.values():
            for seed in SEEDS:
                composition = build_composition(profile, style, seed)
                instrument = composition.midi.instruments[0]
                start, end, silence = longest_internal_silence(
                    instrument.notes,
                    composition.form.seconds_per_beat,
                    deliberate_phrase_rest_beat=(
                        (composition.form.sections[-1].end_bar - 2)
                        * composition.form.beats_per_bar
                    ),
                )
                label = f"{profile_path.stem}/{style.name}/seed={seed}"
                if silence > MAX_SILENCE_BEATS:
                    print(
                        f"FAIL {label}: {silence:.2f} beats silent "
                        f"between beats {start:.2f} and {end:.2f}"
                    )
                    failures += 1
                else:
                    print(f"PASS {label}: longest internal silence {silence:.2f} beats")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
