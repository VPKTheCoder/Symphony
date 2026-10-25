"""Phrase-grammar melody tests: hook identity, smoothness and climax shape."""

from __future__ import annotations

import unittest
from pathlib import Path

from symphony.compose import build_composition
from symphony.melody import (
    build_hook,
    build_lead_line,
    melody_quality,
    plan_pitches,
)
from symphony.profile import load_profile
from symphony.styles import STYLES
from symphony.theory import MODES

ROOT = Path(__file__).resolve().parents[1]
PARTS = ("violin", "guitar", "piano")
CASES = (
    ("fd", "cinematic", 0),
    ("fd", "cinematic", 1),
    ("fd", "anthem", 0),
    ("small", "cinematic", 0),
    ("small", "anthem", 1),
    ("fd", "contemplative", 0),
    ("small", "contemplative", 1),
)


class MelodyGrammarTests(unittest.TestCase):
    def test_hook_is_deterministic_and_has_question_answer_shape(self) -> None:
        first = build_hook("repo-identity", ("main", "parser", "scheduler"))
        second = build_hook("repo-identity", ("main", "parser", "scheduler"))
        self.assertEqual(first, second)
        self.assertEqual(len(first.degrees), 10)
        self.assertEqual(len(first.beats), 10)
        self.assertEqual(len(first.durations), 10)
        self.assertEqual(first.split, 5)
        self.assertEqual(first.beats, tuple(sorted(first.beats)))
        self.assertTrue(all(duration > 0.0 for duration in first.durations))
        # The question ends away from the tonic; the answer settles on it.
        self.assertNotEqual(first.antecedent[-1] % 7, 0)
        self.assertEqual(first.consequent[-1] % 7, 0)

    def test_hook_uses_steps_and_at_most_one_prepared_leap(self) -> None:
        for identity in ("alpha", "beta", "gamma", "delta", "epsilon"):
            hook = build_hook(identity, ("lib", "main"))
            intervals = [
                right - left
                for left, right in zip(hook.degrees, hook.degrees[1:])
            ]
            leaps = [
                index for index, interval in enumerate(intervals)
                if abs(interval) >= 2
            ]
            self.assertLessEqual(len(leaps), 1, identity)
            for index in leaps:
                # The leap is approached by a step in its direction and left by
                # a step in the opposite direction.
                self.assertLessEqual(abs(intervals[index - 1]), 1)
                self.assertGreater(intervals[index - 1] * intervals[index], 0)
                if index + 1 < len(intervals):
                    self.assertLessEqual(abs(intervals[index + 1]), 1)
                    self.assertLess(intervals[index + 1] * intervals[index], 0)

    def test_hook_identity_survives_style_change(self) -> None:
        profile = load_profile(ROOT / "profiles" / "fd.json")
        plans = [
            build_composition(profile, STYLES[style], 0).variation_plan
            for style in ("cinematic", "anthem", "lofi")
        ]
        self.assertEqual(plans[0].hook_id, plans[1].hook_id)
        self.assertEqual(plans[0].hook_id, plans[2].hook_id)
        self.assertEqual(plans[0].hook_contour, plans[1].hook_contour)
        self.assertEqual(plans[0].hook_contour, plans[2].hook_contour)

    def test_lead_lines_are_smooth_scale_safe_and_phrase_shaped(self) -> None:
        for profile_name, style_name, seed in CASES:
            profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
            style = STYLES[style_name]
            composition = build_composition(profile, style, seed)
            form = composition.form
            plan = composition.variation_plan
            base_scale = {
                (form.key.tonic_pc + interval) % 12
                for interval in MODES[form.key.mode]
            }
            for section in form.sections:
                for part in PARTS:
                    if plan.role_for(section.name, part) != "lead":
                        continue
                    events = build_lead_line(form, section, plan, style, part)
                    self.assertTrue(events)
                    quality = melody_quality(
                        events,
                        form,
                        part,
                        section=section,
                        total_beats=section.bars * 4.0,
                        style=style,
                    )
                    label = f"{profile_name}/{style_name}/{seed}/{section.name}/{part}"
                    self.assertGreaterEqual(quality.step_ratio, 0.70, label)
                    self.assertGreaterEqual(quality.prepared_ratio, 0.99, label)
                    self.assertGreaterEqual(quality.leap_recovery, 0.99, label)
                    self.assertGreaterEqual(quality.strong_chord_ratio, 0.99, label)
                    self.assertEqual(quality.octave_leaps, 0, label)
                    self.assertEqual(quality.tritones, 0, label)
                    self.assertTrue(quality.clean, label)
                    pitches = plan_pitches(form, section, events, part, style)
                    self.assertTrue(
                        all(pitch % 12 in base_scale for pitch in pitches), label
                    )

    def test_highest_note_belongs_to_the_climax(self) -> None:
        for profile_name, style_name, seed in CASES:
            profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
            style = STYLES[style_name]
            composition = build_composition(profile, style, seed)
            form = composition.form
            plan = composition.variation_plan
            bar_seconds = form.meter_beats_per_bar * form.seconds_per_beat
            climax = next(
                section for section in form.sections if section.name == "climax"
            )
            start = climax.start_bar * bar_seconds
            end = climax.end_bar * bar_seconds
            notes = [
                note
                for instrument in composition.midi.instruments
                if not instrument.is_drum
                for note in instrument.notes
            ]
            apex = max(notes, key=lambda note: note.pitch)
            self.assertGreaterEqual(apex.start, start, f"{profile_name}/{style_name}/{seed}")
            self.assertLess(apex.start, end - 1e-6, f"{profile_name}/{style_name}/{seed}")

    def test_composed_notes_remain_in_the_active_scale(self) -> None:
        for profile_name, style_name, seed in CASES:
            profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
            style = STYLES[style_name]
            composition = build_composition(profile, style, seed)
            form = composition.form
            plan = composition.variation_plan
            bar_seconds = form.meter_beats_per_bar * form.seconds_per_beat
            climax = next(
                section for section in form.sections if section.name == "climax"
            )
            start = climax.start_bar * bar_seconds
            end = climax.end_bar * bar_seconds
            base_scale = {
                (form.key.tonic_pc + interval) % 12
                for interval in MODES[form.key.mode]
            }
            transposed = {(pitch + 2) % 12 for pitch in base_scale}
            for instrument in composition.midi.instruments:
                if instrument.is_drum:
                    continue
                for note in instrument.notes:
                    if (
                        plan.signature_id == "sprawl"
                        and start - 1e-6 <= note.start < end - 1e-6
                    ):
                        scale = transposed
                    else:
                        scale = base_scale
                    self.assertIn(
                        note.pitch % 12,
                        scale,
                        f"{profile_name}/{style_name}/{seed}/{instrument.name}/"
                        f"{note.pitch}@{note.start:.2f}",
                    )


if __name__ == "__main__":
    unittest.main()
