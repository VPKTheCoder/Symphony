"""Mastering-chain construction and loudnorm measurement parsing."""

from __future__ import annotations

import unittest
from pathlib import Path

from symphony.render import (
    _synth_command,
    mastering_filter,
    parse_loudnorm_json,
)
from symphony.styles import STYLES

MEASUREMENT = {
    "input_i": "-18.89",
    "input_tp": "0.89",
    "input_lra": "9.20",
    "input_thresh": "-29.19",
    "target_offset": "0.04",
}


class MasteringChainTests(unittest.TestCase):
    def test_mastering_hits_style_target_without_auto_level(self) -> None:
        for style in STYLES.values():
            spec = mastering_filter(style)
            self.assertIn(
                f"loudnorm=I={style.target_lufs:.1f}:TP=-1.5:LRA=11",
                spec,
                style.name,
            )
            self.assertIn("linear=true", spec, style.name)
            self.assertIn("highpass=f=20", spec, style.name)
            self.assertIn("afade=t=in:st=0:d=1.2", spec, style.name)
            # Auto-level would raise the master above the measured target.
            self.assertIn("alimiter=limit=0.95:level=false", spec, style.name)
            self.assertNotIn("level=true", spec, style.name)

    def test_second_pass_uses_the_measurement(self) -> None:
        spec = mastering_filter(STYLES["anthem"], MEASUREMENT)
        parameters = {
            "input_i": "measured_I",
            "input_tp": "measured_TP",
            "input_lra": "measured_LRA",
            "input_thresh": "measured_thresh",
            "target_offset": "offset",
        }
        for key, parameter in parameters.items():
            self.assertIn(f"{parameter}={MEASUREMENT[key]}", spec)
        self.assertIn("linear=true", spec)

    def test_measurement_parser_reads_loudnorm_summary(self) -> None:
        text = (
            "[Parsed_loudnorm_1 @ 0000] \n"
            "{\n"
            '\t"input_i" : "-18.89",\n'
            '\t"input_tp" : "0.89",\n'
            '\t"input_lra" : "9.20",\n'
            '\t"input_thresh" : "-29.19",\n'
            '\t"output_i" : "-14.04",\n'
            '\t"target_offset" : "0.04"\n'
            "}\n"
            "size=N/A time=00:02:55.30 bitrate=N/A speed=16.7x"
        )
        self.assertEqual(parse_loudnorm_json(text), MEASUREMENT)

    def test_measurement_parser_rejects_incomplete_or_silent_data(self) -> None:
        self.assertIsNone(parse_loudnorm_json("no loudnorm summary here"))
        self.assertIsNone(
            parse_loudnorm_json('{"input_i": "-inf", "input_tp": "0.0"}')
        )
        self.assertIsNone(
            parse_loudnorm_json(
                '{"input_i": "-18.0", "input_tp": "0.0", '
                '"input_lra": "8.0", "input_thresh": "-28.0"}'
            )
        )

    def test_synth_requests_float_output_and_style_reverb(self) -> None:
        style = STYLES["lofi"]
        command = _synth_command(
            "fluidsynth",
            Path("GeneralUser-GS.sf2"),
            Path("track.mid"),
            Path("raw.wav"),
            style,
        )
        self.assertIn("audio.file.format=float", command)
        self.assertIn("0.85", command)
        self.assertIn(f"synth.reverb.room-size={style.reverb_room:.3f}", command)
        self.assertEqual(command[-2], "GeneralUser-GS.sf2")
        self.assertEqual(command[-1], "track.mid")


if __name__ == "__main__":
    unittest.main()
