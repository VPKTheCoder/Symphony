"""Style parameter sets.

Styles deliberately share one composer path.  A style changes tempo, harmony
colour, voicings, dynamics, timing feel and later the rhythm-section settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PianoPattern:
    name: str
    intro: tuple[float, ...]
    theme: tuple[float, ...]
    development: tuple[float, ...]
    climax: tuple[float, ...]
    texture: str


@dataclass(frozen=True)
class VoicingStyle:
    name: str
    max_gap: int
    low_shift: int
    high_shift: int
    target_shift: int


@dataclass(frozen=True)
class BuildShape:
    name: str
    theme_shift: float
    development_shift: float
    resolution_shift: float


@dataclass(frozen=True)
class BassPattern:
    name: str
    support_beats: tuple[float, ...]
    lead_beats: tuple[float, ...]
    duration: float
    passing_tone: bool = True


@dataclass(frozen=True)
class DrumGroove:
    name: str
    kick: tuple[float, ...]
    snare: tuple[float, ...]
    hats: tuple[float, ...]
    fill_pitch: int


@dataclass(frozen=True)
class ArrangementMatrix:
    name: str
    rows: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]

    def role(self, section: str, instrument: str) -> str:
        row = next(roles for section_name, roles in self.rows if section_name == section)
        return next(role for instrument_name, role in row if instrument_name == instrument)


def _arrangement_matrix(
    name: str,
    leads: dict[str, str],
    outs: dict[str, tuple[str, ...]],
) -> ArrangementMatrix:
    instruments = ("piano", "bass", "drums", "violin", "guitar")
    sections = ("intro", "theme", "development", "climax", "resolution", "outro")
    rows = []
    for section in sections:
        lead = leads[section]
        row = tuple(
            (instrument, "out" if instrument in outs.get(section, ()) else
             "lead" if instrument == lead else "support")
            for instrument in instruments
        )
        rows.append((section, row))
    return ArrangementMatrix(name, tuple(rows))


_CINEMATIC_LEADS = {
    "intro": "piano", "theme": "violin", "development": "violin",
    "climax": "violin", "resolution": "piano", "outro": "piano",
}
_ANTHEM_LEADS = {
    "intro": "piano", "theme": "violin", "development": "violin",
    "climax": "guitar", "resolution": "violin", "outro": "piano",
}
_LOFI_LEADS = {
    "intro": "piano", "theme": "violin", "development": "violin",
    "climax": "violin", "resolution": "piano", "outro": "piano",
}

CINEMATIC_MATRICES = (
    _arrangement_matrix("c_opening", _CINEMATIC_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("c_arpeggio", _CINEMATIC_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("c_swell", {**_CINEMATIC_LEADS, "development": "guitar"}, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("violin",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
)
LOFI_MATRICES = (
    _arrangement_matrix("l_lazy", _LOFI_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("l_hazy", _LOFI_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("l_pocket", {**_LOFI_LEADS, "development": "guitar"}, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("violin",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
)
ANTHEM_MATRICES = (
    _arrangement_matrix("a_hook", _ANTHEM_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("a_drive", _ANTHEM_LEADS, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("guitar",), "development": ("guitar",),
        "resolution": ("guitar",),
        "outro": ("bass", "drums", "violin", "guitar"),
    }),
    _arrangement_matrix("a_call_response", {**_ANTHEM_LEADS, "theme": "guitar"}, {
        "intro": ("bass", "drums", "violin", "guitar"),
        "theme": ("violin",), "development": ("guitar",),
        "resolution": ("guitar",), "outro": ("bass", "drums", "violin", "guitar"),
    }),
)

BASS_PATTERNS = (
    BassPattern("root_hold", (0.0,), (0.0, 2.0), 4.0),
    BassPattern("two_step", (0.0, 2.0), (0.0, 1.0, 2.0, 3.0), 1.7),
    BassPattern("offbeat_anchor", (0.0, 2.5), (0.0, 1.5, 2.5, 3.5), 1.0),
    BassPattern("walking_pass", (0.0, 2.0), (0.0, 1.0, 2.0, 3.0), 0.9),
    BassPattern("syncopated_drive", (0.0, 1.5, 2.5), (0.0, 0.75, 1.5, 2.5, 3.5), 0.75),
)

DRUM_GROOVES = {
    "cinematic": (
        DrumGroove("cinematic_pulse", (0.0, 2.0), (2.0,), (1.0, 3.0), 45),
        DrumGroove("cinematic_toms", (0.0,), (2.0,), (1.0, 2.5, 3.5), 47),
        DrumGroove("cinematic_half_time", (0.0,), (2.0,), (1.0, 3.0), 50),
    ),
    "lofi": (
        DrumGroove("lofi_swing", (0.0, 2.5), (2.0,), (0.5, 1.5, 2.5, 3.5), 37),
        DrumGroove("lofi_brush", (0.0,), (2.0,), (0.5, 1.5, 2.5, 3.5), 39),
        DrumGroove("lofi_late", (0.0, 2.5), (2.5,), (1.0, 2.0, 3.0), 37),
    ),
    "anthem": (
        DrumGroove("anthem_drive", (0.0, 2.0), (1.0, 3.0), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), 50),
        DrumGroove("anthem_four", (0.0, 1.0, 2.0, 3.0), (1.0, 3.0), (0.5, 1.5, 2.5, 3.5), 47),
        DrumGroove("anthem_push", (0.0, 1.5, 2.5), (1.0, 3.0), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), 50),
    ),
}


MODE_FAMILIES: dict[str, tuple[str, ...]] = {
    "majorish": ("major", "lydian", "mixolydian", "dorian", "minor", "phrygian"),
    "modal": ("major", "lydian", "mixolydian", "dorian", "minor", "phrygian"),
    "minorish": ("major", "lydian", "mixolydian", "dorian", "minor", "phrygian"),
}

# Curated four-chord progressions shared by the three style pools. Each style
# owns this map explicitly so later changes can specialize its harmony.
PROGRESSION_POOLS: dict[str, tuple[tuple[int, ...], ...]] = {
    "major": ((1, 5, 6, 4), (6, 4, 1, 5), (1, 6, 4, 5), (4, 1, 5, 6)),
    "lydian": ((1, 2, 6, 5), (1, 5, 2, 6), (6, 2, 1, 5), (2, 5, 1, 6)),
    "dorian": ((1, 4, 1, 7), (1, 7, 4, 5), (4, 1, 5, 7), (4, 5, 1, 7)),
    "mixolydian": ((1, 7, 4, 1), (1, 4, 5, 7), (4, 1, 7, 5), (4, 5, 1, 7)),
    "minor": ((1, 6, 3, 7), (1, 4, 7, 3), (6, 3, 7, 1), (4, 1, 6, 7)),
    "phrygian": ((1, 2, 6, 7), (1, 7, 6, 2), (6, 7, 1, 2), (2, 1, 7, 6)),
}

VOICING_STYLES = (
    VoicingStyle("wide", max_gap=14, low_shift=0, high_shift=0, target_shift=0),
    VoicingStyle("open", max_gap=11, low_shift=2, high_shift=2, target_shift=3),
    VoicingStyle("close", max_gap=8, low_shift=-2, high_shift=-2, target_shift=-3),
    VoicingStyle("bright", max_gap=10, low_shift=0, high_shift=4, target_shift=5),
)

BUILD_SHAPES = (
    BuildShape("gradual", theme_shift=-0.02, development_shift=0.01, resolution_shift=0.0),
    BuildShape("surging", theme_shift=-0.06, development_shift=0.04, resolution_shift=-0.02),
    BuildShape("steady", theme_shift=0.03, development_shift=-0.03, resolution_shift=0.02),
    BuildShape("late_lift", theme_shift=-0.03, development_shift=-0.01, resolution_shift=-0.02),
)

CINEMATIC_PATTERNS = (
    PianoPattern("bloom", (0.0, 2.0), (0.5, 2.5), (0.0, 1.0, 2.0, 3.0), (0.0, 2.0), "block"),
    PianoPattern("wide_pulse", (0.0, 2.5), (0.0, 2.0), (0.0, 1.5, 2.5), (0.0, 1.5, 2.5), "block"),
    PianoPattern("broken_arp", (0.5, 2.5), (0.5, 2.5, 3.5), (0.0, 0.5, 1.5, 2.0, 3.0, 3.5), (0.0, 1.0, 2.0, 3.0), "broken"),
    PianoPattern("falling_arp", (1.0, 3.0), (1.0, 3.0), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0, 3.0), "broken"),
    PianoPattern("soft_stabs", (0.0, 2.5), (0.5, 2.5), (0.5, 1.5, 2.5, 3.5), (0.0, 2.0), "stabs"),
    PianoPattern("rolling_eighths", (0.0, 2.0), (0.0, 1.5, 3.0), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), (0.0, 1.0, 2.0, 3.0), "broken"),
    PianoPattern("high_reply", (0.0, 2.0), (0.5, 3.0), (0.0, 1.0, 2.0, 3.0), (0.0, 1.5, 2.5), "high"),
    PianoPattern("cadence_swell", (0.0, 2.0), (0.0, 2.5), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0, 3.0), "block"),
)

LOFI_PATTERNS = (
    PianoPattern("lazy_backbeat", (0.0, 2.5), (1.5, 3.5), (0.5, 1.5, 2.5, 3.5), (0.0, 2.5), "stabs"),
    PianoPattern("dusty_skip", (0.0, 2.0), (0.5, 2.5, 3.5), (0.5, 1.5, 2.5, 3.5), (0.0, 1.5, 3.0), "block"),
    PianoPattern("swinging_walk", (0.0, 2.0), (0.0, 1.5, 3.0), (0.5, 1.5, 2.5, 3.5), (0.0, 1.5, 2.5), "broken"),
    PianoPattern("late_stabs", (0.5, 2.5), (1.0, 2.5), (0.5, 1.0, 2.5, 3.5), (0.5, 2.0, 3.5), "stabs"),
    PianoPattern("soft_triplet", (0.0, 2.0), (0.5, 2.0, 3.5), (0.0, 1.0, 2.0, 3.0), (0.0, 1.5, 2.5, 3.5), "broken"),
    PianoPattern("offbeat_glow", (0.0, 2.5), (0.5, 2.5), (0.5, 1.5, 2.0, 3.0), (0.0, 1.5, 2.5), "high"),
    PianoPattern("lazy_roll", (0.0, 2.0), (0.0, 2.0, 3.5), (0.0, 0.5, 1.5, 2.0, 3.0, 3.5), (0.0, 1.0, 2.0, 3.0), "broken"),
    PianoPattern("hazy_answer", (0.5, 2.5), (1.5, 3.5), (0.5, 1.5, 2.5, 3.0), (0.0, 2.0, 3.5), "high"),
)

ANTHEM_PATTERNS = (
    PianoPattern("anthem_drive", (0.0, 1.5, 2.5), (0.0, 0.75, 1.5, 2.0, 2.75, 3.5), (0.0, 0.5, 1.5, 2.0, 2.5, 3.0, 3.5), (0.0, 1.0, 1.5, 2.0, 3.0, 3.5), "block"),
    PianoPattern("offbeat_push", (0.0, 1.0, 2.5), (0.0, 1.0, 1.75, 2.5, 3.25), (0.0, 0.5, 1.75, 2.5, 3.25), (0.0, 1.0, 1.75, 2.5, 3.5), "stabs"),
    PianoPattern("eighth_charge", (0.0, 2.0), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), "broken"),
    PianoPattern("stadium_stabs", (0.0, 2.0), (0.0, 1.5, 2.5, 3.5), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0, 3.0), "block"),
    PianoPattern("rising_pulse", (0.0, 2.5), (0.0, 1.0, 2.0, 3.0), (0.0, 0.5, 1.5, 2.5, 3.5), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), "broken"),
    PianoPattern("syncopated_lift", (0.0, 1.5, 3.0), (0.0, 0.75, 2.0, 2.75), (0.0, 0.75, 1.5, 2.75, 3.5), (0.0, 0.75, 1.5, 2.0, 2.75, 3.5), "stabs"),
    PianoPattern("four_square", (0.0, 2.0), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 2.0, 3.0), "block"),
    PianoPattern("bright_arpeggio", (0.0, 2.0), (0.0, 0.75, 1.5, 2.25, 3.0, 3.5), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5), "broken"),
)


@dataclass(frozen=True)
class Style:
    name: str
    tempo_range: tuple[int, int]
    target_seconds: float
    intro_bars: int
    outro_bars: int
    comp_style: str
    seventh_probability: float
    ninth_probability: float
    upper_voices: int
    upper_floor: int
    upper_ceiling: int
    upper_gap: int
    swing_ratio: float
    humanize_ms: tuple[int, int]
    velocity_floor: int
    velocity_ceiling: int
    velocity_curve: float
    pedal_changes_per_bar: int
    chord_roll_ms: tuple[int, int]
    reverb_room: float
    reverb_damping: float
    reverb_level: float
    target_lufs: float
    bright_mode_probability: float = 0.0
    climax_octaves: bool = False
    eleventh_probability: float = 0.0
    mode_families: dict[str, tuple[str, ...]] | None = None
    progression_pools: dict[str, tuple[tuple[int, ...], ...]] | None = None
    piano_patterns: tuple[PianoPattern, ...] = ()
    voicing_styles: tuple[VoicingStyle, ...] = VOICING_STYLES
    build_shapes: tuple[BuildShape, ...] = BUILD_SHAPES
    chord_colors: tuple[str, ...] = ("triad", "seventh", "ninth")
    ornament_pool: tuple[str, ...] = ("none", "pickup", "answer")
    arrangement_matrices: tuple[ArrangementMatrix, ...] = ()
    bass_patterns: tuple[BassPattern, ...] = BASS_PATTERNS
    drum_grooves: tuple[DrumGroove, ...] = ()
    violin_program: int = 40
    guitar_programs: tuple[int, ...] = (27,)
    meters: tuple[tuple[int, int], ...] = ((4, 4),)
    motif_treatments: tuple[str, ...] = (
        "repeat", "transpose", "invert", "extend", "fragment"
    )

    def tempo_for(self, avg_complexity: float, rng_value: float) -> int:
        low, high = self.tempo_range
        tempo = low + (high - low) * avg_complexity
        tempo += (rng_value * 2.0 - 1.0) * max(3.0, (high - low) * 0.12)
        return max(low, min(high, round(tempo)))


CINEMATIC = Style(
    name="cinematic",
    tempo_range=(60, 118),
    target_seconds=188.0,
    intro_bars=8,
    outro_bars=8,
    comp_style="wide_roll",
    seventh_probability=0.42,
    ninth_probability=0.18,
    upper_voices=4,
    upper_floor=52,
    upper_ceiling=88,
    upper_gap=14,
    swing_ratio=0.0,
    humanize_ms=(9, 21),
    velocity_floor=32,
    velocity_ceiling=106,
    velocity_curve=1.0,
    pedal_changes_per_bar=1,
    chord_roll_ms=(4, 16),
    reverb_room=0.78,
    reverb_damping=0.34,
    reverb_level=0.56,
    target_lufs=-16.0,
    mode_families=MODE_FAMILIES,
    progression_pools=PROGRESSION_POOLS,
    piano_patterns=CINEMATIC_PATTERNS,
    chord_colors=("triad", "seventh", "ninth"),
    ornament_pool=("none", "high_reply", "turn", "rising_fill"),
    arrangement_matrices=CINEMATIC_MATRICES,
    drum_grooves=DRUM_GROOVES["cinematic"],
    guitar_programs=(25, 27),
    meters=((4, 4), (6, 8), (3, 4), (7, 8)),
)

LOFI = Style(
    name="lofi",
    tempo_range=(72, 110),
    target_seconds=164.0,
    intro_bars=8,
    outro_bars=8,
    comp_style="swung_comp",
    seventh_probability=0.96,
    ninth_probability=0.66,
    upper_voices=4,
    upper_floor=52,
    upper_ceiling=80,
    upper_gap=9,
    swing_ratio=0.62,
    humanize_ms=(11, 24),
    velocity_floor=35,
    velocity_ceiling=84,
    velocity_curve=0.85,
    pedal_changes_per_bar=2,
    chord_roll_ms=(5, 18),
    reverb_room=0.62,
    reverb_damping=0.52,
    reverb_level=0.48,
    target_lufs=-16.0,
    eleventh_probability=0.12,
    mode_families=MODE_FAMILIES,
    progression_pools=PROGRESSION_POOLS,
    piano_patterns=LOFI_PATTERNS,
    chord_colors=("seventh", "ninth", "eleventh"),
    ornament_pool=("none", "pickup", "late_answer", "turn"),
    arrangement_matrices=LOFI_MATRICES,
    drum_grooves=DRUM_GROOVES["lofi"],
    guitar_programs=(24, 27),
    meters=((4, 4), (6, 8), (3, 4), (7, 8)),
)

ANTHEM = Style(
    name="anthem",
    tempo_range=(108, 150),
    target_seconds=174.0,
    intro_bars=4,
    outro_bars=4,
    comp_style="driving",
    seventh_probability=0.28,
    ninth_probability=0.16,
    upper_voices=4,
    upper_floor=55,
    upper_ceiling=96,
    upper_gap=9,
    swing_ratio=0.5,
    humanize_ms=(2, 8),
    velocity_floor=48,
    velocity_ceiling=118,
    velocity_curve=0.85,
    pedal_changes_per_bar=4,
    chord_roll_ms=(0, 3),
    reverb_room=0.48,
    reverb_damping=0.42,
    reverb_level=0.35,
    target_lufs=-14.0,
    bright_mode_probability=0.35,
    climax_octaves=True,
    mode_families={
        "majorish": MODE_FAMILIES["majorish"],
        "modal": MODE_FAMILIES["modal"],
        "minorish": MODE_FAMILIES["minorish"],
    },
    progression_pools=PROGRESSION_POOLS,
    piano_patterns=ANTHEM_PATTERNS,
    chord_colors=("triad", "seventh", "ninth"),
    ornament_pool=("none", "pickup", "rising_fill", "octave_answer"),
    arrangement_matrices=ANTHEM_MATRICES,
    drum_grooves=DRUM_GROOVES["anthem"],
    guitar_programs=(27, 29),
    meters=((4, 4), (7, 8)),
)

STYLES: dict[str, Style] = {
    CINEMATIC.name: CINEMATIC,
    LOFI.name: LOFI,
    ANTHEM.name: ANTHEM,
}


def get_style(name: str) -> Style:
    try:
        return STYLES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown style {name!r}; choose from {', '.join(sorted(STYLES))}."
        ) from exc
