"""Curated style harmony: four-bar pools, cadence support and determinism."""

from __future__ import annotations

import itertools
import random
import unittest
from pathlib import Path

from symphony.profile import load_profile
from symphony.styles import STYLES
from symphony.theory import MODES, Key, build_chord
from symphony.variation import SECTION_NAMES, sample_variation_plan

ROOT = Path(__file__).resolve().parents[1]
TONIC_PC = 0


def _cadence_chord(pool, bars_per_chord: int):
    """The chord under the answer phrase's final bar of a four-bar phrase."""

    index = (4 - 1) // bars_per_chord
    for progression in pool:
        yield progression, progression[index % len(progression)]


def _contains_tonic(mode: str, degree: int) -> bool:
    chord = build_chord(Key(tonic_pc=TONIC_PC, mode=mode), degree, seventh=True)
    return TONIC_PC in chord.pitch_classes


class ProgressionPoolTests(unittest.TestCase):
    def test_every_style_covers_every_mode_with_four_bar_pools(self) -> None:
        for style in STYLES.values():
            self.assertIsNotNone(style.progression_pools, style.name)
            for mode in MODES:
                pool = style.progression_pools[mode]
                self.assertEqual(len(pool), 5, f"{style.name}/{mode}")
                self.assertEqual(len(set(pool)), len(pool), f"{style.name}/{mode}")
                for progression in pool:
                    self.assertEqual(len(progression), 4, progression)
                    for degree in progression:
                        self.assertGreaterEqual(degree, 1, progression)
                        self.assertLessEqual(degree, 7, progression)

    def test_pools_are_style_specific(self) -> None:
        for left, right in itertools.combinations(STYLES.values(), 2):
            shared = sum(
                left.progression_pools[mode] == right.progression_pools[mode]
                for mode in MODES
            )
            self.assertLessEqual(
                shared,
                1,
                f"{left.name} and {right.name} share {shared} mode pools.",
            )

    def test_every_chord_stays_inside_the_mode(self) -> None:
        for style in STYLES.values():
            for mode in MODES:
                scale = {(TONIC_PC + interval) % 12 for interval in MODES[mode]}
                for progression in style.progression_pools[mode]:
                    for degree in progression:
                        chord = build_chord(
                            Key(tonic_pc=TONIC_PC, mode=mode),
                            degree,
                            seventh=True,
                            ninth=True,
                            eleventh=True,
                        )
                        self.assertLessEqual(
                            set(chord.pitch_classes),
                            scale,
                            f"{style.name}/{mode}/{progression}/{degree}",
                        )

    def test_most_progressions_support_the_answer_cadence(self) -> None:
        # The answer phrase ends in bar four, so its chord depends on how many
        # bars each style holds a chord.  At least three of five loops must keep
        # the tonic available there; the remaining loops may end openly.
        for style in STYLES.values():
            for mode in MODES:
                supported = sum(
                    _contains_tonic(mode, degree)
                    for _, degree in _cadence_chord(
                        style.progression_pools[mode],
                        style.content_bars_per_chord,
                    )
                )
                self.assertGreaterEqual(
                    supported,
                    3,
                    f"{style.name}/{mode} supports only {supported} cadences.",
                )

    def test_sampled_ids_are_style_qualified_and_deterministic(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        for style in STYLES.values():
            first = sample_variation_plan(profile, style, random.Random(0))
            second = sample_variation_plan(profile, style, random.Random(0))
            self.assertEqual(first.progressions, second.progressions)
            pool = style.progression_pools[first.key.mode]
            for section in SECTION_NAMES:
                identifier = first.progression_id_for(section)
                self.assertTrue(
                    identifier.startswith(f"{style.name}_{first.key.mode}_p"),
                    identifier,
                )
                self.assertIn(first.progression_for(section), pool)
            # Intro and outro frame the piece; the content sections deal the
            # rest of the pool before any progression is reused.
            self.assertEqual(
                first.progression_id_for("intro"),
                first.progression_id_for("outro"),
            )
            content = {
                first.progression_for(section)
                for section in ("theme", "development", "climax", "resolution")
            }
            self.assertEqual(len(content), min(4, len(pool) - 1))
            self.assertEqual(
                {first.progression_for(section) for section in SECTION_NAMES},
                set(pool),
            )

    def test_contemplative_minor_frames_with_calm_vamps(self) -> None:
        # Regression: i-VI and III-VI frames made the outro solo skip too often.
        # The pool still supplies all five progressions; only the frame is
        # restricted to the two tonic-compatible vamps.
        profile = load_profile(ROOT / "profiles" / "fd.json")
        style = STYLES["contemplative"]
        pool = style.progression_pools["minor"]
        allowed = style.frame_indices_for("minor", len(pool))
        self.assertEqual(len(allowed), 2)
        for seed in range(12):
            plan = sample_variation_plan(profile, style, random.Random(seed))
            self.assertEqual(plan.key.mode, "minor")
            frame = plan.progression_for("intro")
            self.assertIn(pool.index(frame), allowed)
            self.assertEqual(frame, plan.progression_for("outro"))
            self.assertEqual(
                {plan.progression_for(section) for section in SECTION_NAMES},
                set(pool),
            )

    def test_loop_can_be_repeated_across_a_section(self) -> None:
        # Four chords are one phrase of harmony; the form repeats the loop.
        for style in STYLES.values():
            for mode in MODES:
                for progression in style.progression_pools[mode]:
                    self.assertEqual(
                        [progression[index % 4] for index in range(8)],
                        list(progression) + list(progression),
                    )


if __name__ == "__main__":
    unittest.main()
