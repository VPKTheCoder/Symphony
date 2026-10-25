"""Regression checks for profile-pinned variation planning."""

from __future__ import annotations

import unittest
import tempfile
from dataclasses import replace
import random
from pathlib import Path

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import STYLES
from symphony.variation import fingerprint_distance, mode_family_for, sample_variation_plan

ROOT = Path(__file__).resolve().parents[1]


class VariationPinTests(unittest.TestCase):
    def test_profile_structure_and_mappings_stay_pinned_across_seeds(self) -> None:
        for profile_name in ("small", "large"):
            profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
            for style in STYLES.values():
                compositions = [
                    build_composition(profile, style, seed)
                    for seed in (1, 7, 20, 42, 99)
                ]
                reference = compositions[0]
                pinned = (
                    reference.form.tempo,
                    reference.form.total_bars,
                    reference.form.open_cadence,
                    tuple(
                        (
                            section.name,
                            section.start_bar,
                            section.bars,
                            tuple(module.name for module in section.modules),
                        )
                        for section in reference.form.sections
                    ),
                )
                family = mode_family_for(profile, style)
                for composition in compositions:
                    candidate = composition
                    current = (
                        candidate.form.tempo,
                        candidate.form.total_bars,
                        candidate.form.open_cadence,
                        tuple(
                            (
                                section.name,
                                section.start_bar,
                                section.bars,
                                tuple(module.name for module in section.modules),
                            )
                            for section in candidate.form.sections
                        ),
                    )
                    self.assertEqual(current, pinned)
                    self.assertEqual(candidate.variation_plan.mode_family, family)
                    self.assertIn(
                        candidate.form.key.mode,
                        style.mode_families[family],
                    )
                    self.assertEqual(
                        max(candidate.form.sections, key=lambda item: item.intensity).name,
                        "climax",
                    )

    def test_each_style_has_curated_pool_minimums(self) -> None:
        for style in STYLES.values():
            self.assertGreaterEqual(len(style.piano_patterns), 6)
            self.assertGreaterEqual(len(style.voicing_styles), 3)
            self.assertGreaterEqual(len(style.build_shapes), 3)
            self.assertGreaterEqual(len(style.arrangement_matrices), 3)
            self.assertGreaterEqual(len(style.bass_patterns), 4)
            self.assertGreaterEqual(len(style.drum_grooves), 3)
            self.assertGreaterEqual(len(style.guitar_programs), 1)
            self.assertGreaterEqual(len(style.motif_treatments), 4)
            for family in style.mode_families:
                for mode in style.mode_families[family]:
                    self.assertGreaterEqual(len(style.progression_pools[mode]), 4)
            for matrix in style.arrangement_matrices:
                for section, roles in matrix.rows:
                    instruments = dict(roles)
                    self.assertEqual(set(instruments), {"piano", "bass", "drums", "violin", "guitar"})
                    self.assertLessEqual(sum(role == "lead" for role in instruments.values()), 1)
                    if section != "climax":
                        self.assertLessEqual(sum(role != "out" for role in instruments.values()), 4)

    def test_same_seed_is_byte_deterministic(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        style = STYLES["anthem"]
        first = build_composition(profile, style, 42)
        second = build_composition(profile, style, 42)
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.mid"
            right = Path(directory) / "right.mid"
            first.midi.write(str(left))
            second.midi.write(str(right))
            self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_repo_dna_covers_twelve_roots_and_curated_meters(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        roots = set()
        meters = set()
        for index in range(48):
            candidate = replace(profile, name=f"dna-fixture-{index}")
            plan = sample_variation_plan(candidate, STYLES["cinematic"], random.Random(0))
            roots.add(plan.tonic_pc)
            meters.add(plan.meter)
        self.assertEqual(roots, set(range(12)))
        self.assertTrue(meters.issubset({(4, 4), (6, 8), (3, 4), (7, 8)}))

    def test_identity_pins_musical_dna_across_variation_indices(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        first = build_composition(profile, STYLES["cinematic"], 0)
        second = build_composition(profile, STYLES["cinematic"], 1)
        self.assertEqual(first.form.key, second.form.key)
        self.assertEqual(first.form.meter, second.form.meter)
        self.assertEqual(first.form.tempo, second.form.tempo)
        self.assertEqual(first.variation_plan.hook_id, second.variation_plan.hook_id)
        self.assertNotEqual(first.variation_plan.fingerprint(), second.variation_plan.fingerprint())

    def test_rhythm_section_respects_registers_and_drum_channel(self) -> None:
        profile = load_profile(ROOT / "profiles" / "large.json")
        composition = build_composition(profile, STYLES["anthem"], 42)
        tracks = {instrument.name: instrument for instrument in composition.midi.instruments}
        self.assertEqual(set(tracks), {"Piano", "Bass", "Drum Kit", "Violin", "Guitar"})
        self.assertTrue(all(note.pitch >= 49 for note in tracks["Piano"].notes))
        self.assertTrue(all(24 <= note.pitch <= 48 for note in tracks["Bass"].notes))
        self.assertTrue(all(55 <= note.pitch <= 103 for note in tracks["Violin"].notes))
        self.assertTrue(all(40 <= note.pitch <= 76 for note in tracks["Guitar"].notes))
        self.assertEqual(tracks["Drum Kit"].channel, 9)
        self.assertTrue(tracks["Drum Kit"].is_drum)

    def test_batch_diversity_gate_rejects_near_duplicates(self) -> None:
        profile = load_profile(ROOT / "profiles" / "large.json")
        style = STYLES["anthem"]
        accepted_fingerprints = []
        accepted_plans = []
        for seed in range(42, 46):
            composition = build_composition(
                profile,
                style,
                seed,
                avoid_fingerprints=accepted_fingerprints,
            )
            plan = composition.variation_plan
            accepted_fingerprints.append(plan.fingerprint())
            accepted_plans.append(plan)
        for index, plan in enumerate(accepted_plans):
            for previous in accepted_plans[:index]:
                self.assertGreaterEqual(fingerprint_distance(plan, previous), 4)
        self.assertTrue(any(item.startswith("m:") for item in accepted_plans[0].fingerprint()))


if __name__ == "__main__":
    unittest.main()
