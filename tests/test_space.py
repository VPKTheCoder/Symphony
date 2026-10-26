"""Arrangement space: density caps, phrase rests and resting parts."""

from __future__ import annotations

import unittest
from pathlib import Path

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.space import TRACK_PARTS, phrase_rest_bars
from symphony.styles import STYLES

ROOT = Path(__file__).resolve().parents[1]
SPACIOUS_STYLES = ("cinematic", "lofi", "contemplative")
CASES = (("fd", 0), ("small", 1))
SECTION_NAMES = ("intro", "theme", "development", "climax", "resolution", "outro")


def _active_notes(composition, section) -> dict[str, list]:
    form = composition.form
    bar_seconds = form.meter_beats_per_bar * form.seconds_per_beat
    start = section.start_bar * bar_seconds
    end = section.end_bar * bar_seconds
    result = {}
    for instrument in composition.midi.instruments:
        notes = [
            note
            for note in instrument.notes
            if note.start < end - 1e-6 and note.end > start + 1e-6
        ]
        if notes:
            result[instrument.name] = notes
    return result


class ArrangementSpaceTests(unittest.TestCase):
    def test_matrices_never_crowd_or_double_a_lead(self) -> None:
        for style in STYLES.values():
            for matrix in style.arrangement_matrices:
                for section, _row in matrix.rows:
                    self.assertLessEqual(
                        len(matrix.leads(section)), 1,
                        f"{style.name}/{matrix.name}/{section}",
                    )
                    self.assertLessEqual(
                        len(matrix.active(section)),
                        style.active_limit_for(section),
                        f"{style.name}/{matrix.name}/{section}",
                    )
                if style.name in SPACIOUS_STYLES:
                    quiet = sum(
                        len(matrix.active(section)) <= 3
                        for section, _row in matrix.rows
                    )
                    self.assertGreaterEqual(
                        quiet, 4,
                        f"{style.name}/{matrix.name} must rest two parts "
                        "in most sections",
                    )

    def test_spacious_styles_keep_two_parts_out_in_most_sections(self) -> None:
        for style_name in SPACIOUS_STYLES:
            style = STYLES[style_name]
            for profile_name, seed in CASES:
                profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
                composition = build_composition(profile, style, seed)
                plan = composition.variation_plan
                quiet_sections = 0
                for section in composition.form.sections:
                    sounding = _active_notes(composition, section)
                    self.assertLessEqual(
                        len(sounding),
                        style.active_limit_for(section.name),
                        f"{style_name}/{profile_name}/{seed}/{section.name}",
                    )
                    if len(sounding) <= 3:
                        quiet_sections += 1
                    leads = [
                        part for part in TRACK_PARTS.values()
                        if plan.role_for(section.name, part) == "lead"
                    ]
                    self.assertLessEqual(len(leads), 1)
                    for track_name, part in TRACK_PARTS.items():
                        if plan.role_for(section.name, part) == "out":
                            self.assertNotIn(
                                track_name, sounding,
                                f"{style_name}/{profile_name}/{seed}/"
                                f"{section.name}/{track_name} should rest",
                            )
                self.assertGreaterEqual(
                    quiet_sections, 4,
                    f"{style_name}/{profile_name}/{seed}",
                )

    def test_phrase_rests_are_silent_for_support_parts(self) -> None:
        for style_name in SPACIOUS_STYLES:
            style = STYLES[style_name]
            self.assertGreater(style.phrase_rest_bars, 0)
            for profile_name, seed in CASES:
                profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
                composition = build_composition(profile, style, seed)
                form = composition.form
                plan = composition.variation_plan
                bar_seconds = form.meter_beats_per_bar * form.seconds_per_beat
                tracks = {
                    instrument.name: instrument
                    for instrument in composition.midi.instruments
                }
                restful_sections = 0
                for section in form.sections:
                    section_has_rest = False
                    for track_name, part in TRACK_PARTS.items():
                        if plan.role_for(section.name, part) != "support":
                            continue
                        for local_bar in phrase_rest_bars(style, section, part):
                            section_has_rest = True
                            start = (
                                section.start_bar + local_bar
                            ) * bar_seconds
                            end = start + bar_seconds
                            self.assertFalse(
                                any(
                                    note.start < end - 1e-6
                                    and note.end > start + 1e-6
                                    for note in tracks[track_name].notes
                                ),
                                f"{style_name}/{profile_name}/{seed}/"
                                f"{section.name}/{part}/bar {local_bar}",
                            )
                    if section_has_rest:
                        restful_sections += 1
                self.assertGreaterEqual(
                    restful_sections, 3,
                    f"{style_name}/{profile_name}/{seed}",
                )

    def test_anthem_keeps_its_full_arrangement(self) -> None:
        style = STYLES["anthem"]
        self.assertEqual(style.phrase_rest_bars, 0)
        self.assertGreaterEqual(style.max_piano_attacks_per_bar, 9)
        profile = load_profile(ROOT / "profiles" / "small.json")
        composition = build_composition(profile, style, 0)
        expected = {
            "intro": 1,
            "theme": 4,
            "development": 4,
            "climax": 5,
            "resolution": 4,
            "outro": 1,
        }
        for section in composition.form.sections:
            self.assertEqual(
                len(_active_notes(composition, section)),
                expected[section.name],
                section.name,
            )

    def test_spacious_styles_have_tighter_note_budgets(self) -> None:
        for style_name in SPACIOUS_STYLES:
            style = STYLES[style_name]
            self.assertLessEqual(style.max_active_parts, 3)
            self.assertLessEqual(style.climax_max_active_parts, 4)
            self.assertLess(style.max_piano_attacks_per_bar, 9)


if __name__ == "__main__":
    unittest.main()
