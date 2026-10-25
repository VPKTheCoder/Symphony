"""Contemplative style: slow harmony, ostinato, restraint and a long cadence."""

from __future__ import annotations

import unittest
from pathlib import Path

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import STYLES

ROOT = Path(__file__).resolve().parents[1]


class ContemplativeStyleTests(unittest.TestCase):
    def _composition(self, profile_name: str = "fd", seed: int = 0):
        profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
        return build_composition(profile, STYLES["contemplative"], seed)

    def test_style_is_slow_and_restrained(self) -> None:
        style = STYLES["contemplative"]
        self.assertEqual(style.tempo_range, (60, 84))
        self.assertTrue(set(style.meters).issubset({(4, 4), (6, 8)}))
        self.assertEqual(style.comp_style, "ostinato")
        self.assertEqual(style.content_bars_per_chord, 2)
        self.assertGreaterEqual(style.final_chord_beats, 8.0)
        self.assertGreater(style.final_ritardando, 0.0)
        self.assertLessEqual(style.drum_gain, 0.5)

    def test_arrangement_is_additive_and_drums_belong_to_the_climax(self) -> None:
        style = STYLES["contemplative"]
        for matrix in style.arrangement_matrices:
            for section, roles in matrix.rows:
                role = dict(roles)
                if section == "intro":
                    self.assertEqual(
                        {name for name, value in role.items() if value != "out"},
                        {"piano"},
                    )
                if section in {"theme", "development", "climax", "resolution"}:
                    self.assertEqual(role["violin"], "lead")
                if section != "climax":
                    self.assertEqual(role["drums"], "out")
                self.assertLessEqual(
                    sum(value == "lead" for value in role.values()), 1
                )

    def test_slow_harmony_ostinato_and_long_final_chord(self) -> None:
        composition = self._composition()
        form = composition.form
        plan = composition.variation_plan
        style = STYLES["contemplative"]
        self.assertTrue(60 <= form.tempo <= 84)
        self.assertIn(form.meter, {(4, 4), (6, 8)})
        for section in form.sections:
            self.assertEqual(section.bars_per_chord, 2)
        self.assertTrue(
            plan.role_for("intro", "piano") == "lead"
            and all(
                plan.role_for("intro", part) == "out"
                for part in ("bass", "drums", "violin", "guitar")
            )
        )
        tracks = {track.name: track for track in composition.midi.instruments}
        # The ostinato keeps a pulse even under a two-bar harmony.
        intro = form.sections[0]
        bar_seconds = form.meter_beats_per_bar * form.seconds_per_beat
        intro_notes = [
            note for note in tracks["Piano"].notes
            if intro.start_bar * bar_seconds <= note.start < intro.end_bar * bar_seconds
        ]
        self.assertGreaterEqual(len(intro_notes), intro.bars * 2)
        # Drums are absent outside the climax.
        climax = next(section for section in form.sections if section.name == "climax")
        start = climax.start_bar * bar_seconds
        end = climax.end_bar * bar_seconds
        self.assertTrue(
            all(start <= note.start < end for note in tracks["Drum Kit"].notes)
        )
        # The final tonic rings beyond the notated bar line.
        last_bar_end = form.total_bars * bar_seconds
        piano_end = max(note.end for note in tracks["Piano"].notes)
        self.assertGreater(piano_end, last_bar_end + 2.0)
        self.assertEqual(style.final_chord_beats, 8.0)

    def test_same_seed_is_byte_deterministic(self) -> None:
        import tempfile

        first = self._composition("small", 7)
        second = self._composition("small", 7)
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.mid"
            right = Path(directory) / "right.mid"
            first.midi.write(str(left))
            second.midi.write(str(right))
            self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_sustained_violin_hook_is_lead_not_background(self) -> None:
        composition = self._composition("small", 0)
        form = composition.form
        plan = composition.variation_plan
        tracks = {track.name: track for track in composition.midi.instruments}
        for section in form.sections:
            if plan.role_for(section.name, "violin") == "lead":
                self.assertEqual(section.name in {
                    "theme", "development", "climax", "resolution"
                }, True)
        lengths = [
            note.end - note.start
            for note in tracks["Violin"].notes
        ]
        self.assertTrue(lengths)
        self.assertGreater(max(lengths), form.seconds_per_beat * 1.2)


if __name__ == "__main__":
    unittest.main()
