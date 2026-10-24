from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from symphony.compose import build_composition
from symphony.profile import load_profile
from symphony.styles import get_style
from symphony.timeline import build_timeline, format_listening_guide, write_timeline


class TimelineTests(unittest.TestCase):
    def test_sections_moments_guide_and_serialization(self) -> None:
        profile = load_profile(Path(__file__).parents[1] / "profiles" / "small.json")
        composition = build_composition(profile, get_style("anthem"), 42)
        timeline = build_timeline(composition)
        self.assertEqual(len(timeline["sections"]), 6)
        for section in timeline["sections"]:
            self.assertLessEqual(section["start_time"], section["end_time"])
            for moment in section["moments"]:
                self.assertGreaterEqual(moment["time"], section["start_time"])
                self.assertLessEqual(moment["time"], section["end_time"])
        self.assertTrue(timeline["listening_guide"])
        self.assertIn("Listening guide", format_listening_guide(timeline))
        with tempfile.TemporaryDirectory() as directory:
            path = write_timeline(composition, Path(directory) / "track")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), timeline)


if __name__ == "__main__":
    unittest.main()
