"""Tests for objective scoring and ``--best-of`` selection."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from symphony.compose import (
    ScoredCandidate,
    build_composition,
    build_scored_candidates,
    main,
    select_best_candidate,
)
from symphony.profile import load_profile
from symphony.score import COMPONENT_WEIGHTS, ScoreReport, score_composition
from symphony.styles import get_style
from symphony.timeline import build_timeline, write_timeline

ROOT = Path(__file__).resolve().parents[1]


class ScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile(ROOT / "profiles" / "small.json")
        cls.style = get_style("cinematic")
        cls.composition = build_composition(cls.profile, cls.style, 3)
        cls.report = score_composition(cls.composition)
        cls.batch = build_scored_candidates(cls.profile, cls.style, 41, 3)

    def test_components_are_bounded_and_weights_sum_to_one(self) -> None:
        expected = {
            "phrase_grammar",
            "voice_leading",
            "density_balance",
            "rest_placement",
            "range_shape",
            "repetition",
        }
        self.assertEqual(set(COMPONENT_WEIGHTS), expected)
        self.assertAlmostEqual(sum(COMPONENT_WEIGHTS.values()), 1.0, places=9)
        payload = self.report.to_dict()
        self.assertEqual(set(payload["components"]), expected)
        self.assertGreaterEqual(payload["overall"], 0.0)
        self.assertLessEqual(payload["overall"], 100.0)
        for name, value in payload["components"].items():
            self.assertGreaterEqual(value, 0.0, name)
            self.assertLessEqual(value, 1.0, name)
        self.assertTrue(payload["details"])
        self.assertIn("phrase_step_ratio", payload["details"])
        self.assertIn("voice_smooth_ratio", payload["details"])
        self.assertIn("density_coverage", payload["details"])
        self.assertIn("rest_hygiene", payload["details"])
        self.assertIn("range_global_span", payload["details"])
        self.assertIn("repetition_progressions", payload["details"])

    def test_score_is_deterministic_for_the_same_seed(self) -> None:
        rebuilt = build_composition(self.profile, self.style, 3)
        self.assertEqual(score_composition(rebuilt).to_dict(), self.report.to_dict())

    def test_variation_indices_produce_distinct_scores(self) -> None:
        scores = {candidate.score.overall for candidate in self.batch}
        self.assertGreater(len(scores), 1)

    def test_candidates_use_consecutive_seeds_and_their_own_scores(self) -> None:
        self.assertEqual([candidate.index for candidate in self.batch], [0, 1, 2])
        self.assertEqual(
            [candidate.composition.seed for candidate in self.batch], [41, 42, 43]
        )
        for candidate in self.batch:
            direct = build_composition(
                self.profile, self.style, candidate.composition.seed
            )
            self.assertEqual(
                score_composition(direct).to_dict(), candidate.score.to_dict()
            )

    def test_best_of_winner_rebuilds_byte_for_byte_from_its_seed(self) -> None:
        winner = select_best_candidate(self.batch)
        self.assertEqual(winner.composition.seed, 41 + winner.index)
        rebuilt = build_composition(
            self.profile, self.style, winner.composition.seed
        )
        self.assertEqual(score_composition(rebuilt).to_dict(), winner.score.to_dict())
        with tempfile.TemporaryDirectory() as directory:
            winner_path = Path(directory) / "winner.mid"
            rebuilt_path = Path(directory) / "rebuilt.mid"
            winner.composition.midi.write(str(winner_path))
            rebuilt.midi.write(str(rebuilt_path))
            self.assertEqual(winner_path.read_bytes(), rebuilt_path.read_bytes())

    def test_equal_scores_keep_the_lower_candidate_index(self) -> None:
        tied = ScoreReport(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        candidates = tuple(
            ScoredCandidate(
                index=index,
                composition=candidate.composition,
                score=tied,
            )
            for index, candidate in enumerate(self.batch[:2])
        )
        self.assertEqual(select_best_candidate(candidates).index, 0)
        self.assertEqual(select_best_candidate(tuple(reversed(candidates))).index, 0)

    def test_best_of_requires_a_positive_count(self) -> None:
        with self.assertRaises(ValueError):
            build_scored_candidates(self.profile, self.style, 0, 0)
        with self.assertRaises(ValueError):
            select_best_candidate(())

    def test_best_of_and_variations_are_mutually_exclusive(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(
                    [
                        "--profile",
                        str(ROOT / "profiles" / "small.json"),
                        "--style",
                        "anthem",
                        "--out",
                        "unused",
                        "--best-of",
                        "2",
                        "--variations",
                        "2",
                    ]
                )
        self.assertEqual(caught.exception.code, 2)

    def test_timeline_score_and_selection_metadata(self) -> None:
        payload = self.report.to_dict()
        selection = {
            "best_of": 3,
            "candidate_index": 1,
            "candidate_seed": 42,
        }
        plain = build_timeline(self.composition)
        self.assertNotIn("score", plain)
        self.assertNotIn("selection", plain)
        timeline = build_timeline(
            self.composition, score=payload, selection=selection
        )
        self.assertEqual(timeline["score"], payload)
        self.assertEqual(timeline["selection"], selection)
        with tempfile.TemporaryDirectory() as directory:
            path = write_timeline(
                self.composition,
                Path(directory) / "track",
                score=payload,
                selection=selection,
            )
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written["score"], payload)
            self.assertEqual(written["selection"], selection)
            self.assertEqual(written["seed"], self.composition.seed)


if __name__ == "__main__":
    unittest.main()
