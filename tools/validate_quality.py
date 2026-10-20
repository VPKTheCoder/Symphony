"""Quality sweep for scale, instrument lanes, coverage, and duration.

Run with ``python tools/validate_quality.py``. Checks seeds 1–20 for every
built-in profile/style pair. The breath before the last outro chord is the one
explicitly allowed end-of-phrase silence.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import STYLES
from symphony.theory import MODES
from tools.validate_silence import longest_internal_silence

SEEDS = range(1, 21)
MAX_SILENCE_BEATS = 1.5
MIN_DURATION_SECONDS = 120.0
MAX_DURATION_SECONDS = 240.0


def main() -> int:
    failures = 0
    for profile_path in sorted((ROOT / "profiles").glob("*.json")):
        profile = load_profile(profile_path)
        for style in STYLES.values():
            for seed in SEEDS:
                composition = build_composition(profile, style, seed)
                form = composition.form
                instruments = composition.midi.instruments
                allowed_pitch_classes = {
                    (form.key.tonic_pc + interval) % 12
                    for interval in MODES[form.key.mode]
                }
                out_of_scale = [
                    note.pitch
                    for instrument in instruments if not instrument.is_drum
                    for note in instrument.notes
                    if note.pitch % 12 not in allowed_pitch_classes
                ]
                lane_violations = []
                for instrument in instruments:
                    if instrument.is_drum:
                        if instrument.channel != 9:
                            lane_violations.append("drums not on channel 10")
                        continue
                    low, high = {
                        "Piano": (49, 108), "Bass": (24, 48),
                        "Violin": (55, 103), "Guitar": (40, 76),
                    }.get(instrument.name, (0, 127))
                    if any(not low <= note.pitch <= high for note in instrument.notes):
                        lane_violations.append(f"{instrument.name} outside {low}–{high}")
                outro = form.sections[-1]
                gap = longest_internal_silence(
                    [note for instrument in instruments for note in instrument.notes],
                    form.seconds_per_beat,
                    deliberate_phrase_rest_beat=(outro.end_bar - 2)
                    * form.beats_per_bar,
                )
                duration = form.estimated_seconds
                issues = []
                if out_of_scale:
                    issues.append(f"{len(out_of_scale)} out-of-scale notes")
                if lane_violations:
                    issues.extend(lane_violations)
                if gap[2] > MAX_SILENCE_BEATS:
                    issues.append(
                        f"{gap[2]:.2f}-beat silence at beats {gap[0]:.2f}–{gap[1]:.2f}"
                    )
                if not MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS:
                    issues.append(f"duration {duration / 60:.2f} min")
                label = f"{profile_path.stem}/{style.name}/seed={seed}"
                if issues:
                    print(f"FAIL {label}: " + "; ".join(issues))
                    failures += 1
                else:
                    print(
                        f"PASS {label}: scale, max gap {gap[2]:.2f} beats, "
                        f"duration {duration / 60:.2f} min"
                    )
    print(f"Checked {len(list((ROOT / 'profiles').glob('*.json'))) * len(STYLES) * len(SEEDS)} compositions.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
