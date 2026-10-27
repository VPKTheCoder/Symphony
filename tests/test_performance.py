"""Performance shaping: shared swing, phrase dynamics and safe note bounds."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pretty_midi

from symphony.compose import build_composition
from symphony.performance import (
    apply_performance_shaping,
    groove_delay_beats,
    metric_accent,
    phrase_dynamic_offset,
)
from symphony.profile import load_profile
from symphony.styles import STYLES

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("small", "cinematic", 0),
    ("small", "lofi", 1),
    ("small", "anthem", 0),
    ("small", "contemplative", 1),
    ("fd", "cinematic", 1),
    ("fd", "lofi", 0),
)


def _support_section(composition, part: str):
    for section in composition.form.sections:
        if (
            composition.variation_plan.role_for(section.name, part) == "support"
            and section.bars >= 4
        ):
            return section
    raise AssertionError(f"No support section for {part}")


def _probe(composition, part: str, events: tuple[tuple[int, float, int, int], ...]):
    """Build a one-instrument MIDI probe inside a real composition's section."""

    form = composition.form
    section = _support_section(composition, part)
    beat_seconds = form.seconds_per_beat
    bar_beats = form.beats_per_bar
    instrument = pretty_midi.Instrument(program=32, name=part.title())
    instrument.channel = 1
    for local_bar, beat, velocity, pitch in events:
        start = (
            (section.start_bar + local_bar) * bar_beats + beat
        ) * beat_seconds
        instrument.notes.append(
            pretty_midi.Note(
                velocity=velocity,
                pitch=pitch,
                start=start,
                end=start + 0.4 * beat_seconds,
            )
        )
    midi = pretty_midi.PrettyMIDI(initial_tempo=form.tempo, resolution=960)
    midi.instruments.append(instrument)
    return midi, form, section, instrument


class PerformanceShapingTests(unittest.TestCase):
    def test_groove_delay_follows_the_style_swing(self) -> None:
        self.assertAlmostEqual(groove_delay_beats(STYLES["lofi"]), 0.12)
        for style_name in ("cinematic", "anthem", "contemplative"):
            self.assertEqual(groove_delay_beats(STYLES[style_name]), 0.0)

    def test_phrase_arc_peaks_mid_phrase_and_releases(self) -> None:
        for style_name in ("cinematic", "lofi", "anthem", "contemplative"):
            style = STYLES[style_name]
            offsets = [phrase_dynamic_offset(style, bar) for bar in range(4)]
            self.assertGreater(offsets[2], offsets[0], style_name)
            self.assertGreater(offsets[2], offsets[3], style_name)
            self.assertGreater(offsets[1], offsets[0], style_name)
            self.assertAlmostEqual(
                offsets[0], phrase_dynamic_offset(style, 4), places=9
            )

    def test_metric_accent_marks_downbeats_without_drowning_the_kit(self) -> None:
        style = STYLES["cinematic"]
        self.assertGreater(
            metric_accent(style, 0.0, "bass"),
            metric_accent(style, 1.0, "bass"),
        )
        self.assertGreater(
            metric_accent(style, 0.0, "bass"),
            metric_accent(style, 2.0, "bass"),
        )
        self.assertEqual(metric_accent(style, 1.0, "bass"), 0.0)
        self.assertLess(
            metric_accent(style, 0.0, "drums"),
            metric_accent(style, 0.0, "bass"),
        )
        self.assertEqual(metric_accent(style, 0.0, "piano"), 0.0)

    def test_lofi_swing_is_applied_to_a_support_part(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        style = STYLES["lofi"]
        composition = build_composition(profile, style, 1)
        midi, form, section, instrument = _probe(
            composition,
            "bass",
            ((0, 0.0, 80, 40), (0, 0.5, 80, 50), (2, 0.0, 80, 43)),
        )
        before = {
            note.pitch: note.start for note in instrument.notes
        }
        apply_performance_shaping(midi, form, style, composition.variation_plan)
        after = {note.pitch: note.start for note in instrument.notes}
        delay = groove_delay_beats(style) * form.seconds_per_beat
        self.assertAlmostEqual(after[50], before[50] + delay, places=6)
        # Downbeats are not swung.
        self.assertAlmostEqual(after[40], before[40], places=6)
        self.assertAlmostEqual(after[43], before[43], places=6)

    def test_support_phrase_arc_raises_the_middle_and_softens_the_release(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        for style_name in ("cinematic", "lofi", "anthem", "contemplative"):
            style = STYLES[style_name]
            composition = build_composition(profile, style, 1)
            midi, form, _section, instrument = _probe(
                composition,
                "bass",
                (
                    (0, 0.0, 80, 40),
                    (2, 0.0, 80, 43),
                    (3, 0.0, 80, 45),
                    (2, 0.0, 127, 52),
                ),
            )
            apply_performance_shaping(
                midi, form, style, composition.variation_plan
            )
            notes = {note.pitch: note for note in instrument.notes}
            self.assertGreater(notes[43].velocity, notes[40].velocity, style_name)
            self.assertGreater(notes[43].velocity, notes[45].velocity, style_name)
            self.assertEqual(notes[52].velocity, 127, style_name)

    def test_lead_expression_is_left_to_the_melody_engine(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        style = STYLES["cinematic"]
        composition = build_composition(profile, style, 0)
        section = next(
            section for section in composition.form.sections
            if composition.variation_plan.role_for(section.name, "violin") == "lead"
        )
        form = composition.form
        instrument = pretty_midi.Instrument(program=40, name="Violin")
        instrument.channel = 3
        start = (section.start_bar + 2) * form.beats_per_bar * form.seconds_per_beat
        instrument.notes.append(
            pretty_midi.Note(77, 72, start, start + form.seconds_per_beat * 0.8)
        )
        midi = pretty_midi.PrettyMIDI(initial_tempo=form.tempo, resolution=960)
        midi.instruments.append(instrument)
        apply_performance_shaping(midi, form, style, composition.variation_plan)
        self.assertEqual(instrument.notes[0].velocity, 77)

    def test_composed_notes_stay_valid_and_sorted(self) -> None:
        for profile_name, style_name, seed in CASES:
            profile = load_profile(ROOT / "profiles" / f"{profile_name}.json")
            composition = build_composition(
                profile, STYLES[style_name], seed
            )
            for instrument in composition.midi.instruments:
                starts = [note.start for note in instrument.notes]
                self.assertEqual(
                    starts,
                    sorted(starts),
                    f"{profile_name}/{style_name}/{seed}/{instrument.name}",
                )
                for note in instrument.notes:
                    label = (
                        f"{profile_name}/{style_name}/{seed}/"
                        f"{instrument.name}/{note.pitch}"
                    )
                    self.assertGreaterEqual(note.start, 0.0, label)
                    self.assertGreater(note.end, note.start, label)
                    self.assertGreaterEqual(note.velocity, 1, label)
                    self.assertLessEqual(note.velocity, 127, label)

    def test_lofi_performance_is_byte_deterministic(self) -> None:
        profile = load_profile(ROOT / "profiles" / "small.json")
        style = STYLES["lofi"]
        first = build_composition(profile, style, 42)
        second = build_composition(profile, style, 42)
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.mid"
            right = Path(directory) / "right.mid"
            first.midi.write(str(left))
            second.midi.write(str(right))
            self.assertEqual(left.read_bytes(), right.read_bytes())


if __name__ == "__main__":
    unittest.main()
