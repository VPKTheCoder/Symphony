"""Seeded, shared arrangement choices for a composition.

Profile-driven choices are pinned while curated arrangement choices are sampled
once here and then shared by form and instrument renderers.
"""

from __future__ import annotations

import random
import hashlib
from dataclasses import dataclass

from symphony.profile import Profile
from symphony.styles import ArrangementMatrix, BuildShape, Style
from symphony.theory import MAJORISH_MODES, Key
from symphony.identity import profile_fingerprint
from symphony.signatures import choose_signature
from symphony.melody import build_hook

SECTION_NAMES = ("intro", "theme", "development", "climax", "resolution", "outro")


@dataclass(frozen=True)
class VariationPlan:
    mode_family: str
    key: Key
    tonic_pc: int
    progressions: tuple[tuple[str, str, tuple[int, ...]], ...]
    rhythm_patterns: tuple[tuple[str, str], ...]
    voicing_style: str
    register_shift: int
    ornaments: tuple[tuple[str, str], ...]
    chord_colors: tuple[tuple[str, str], ...]
    build_shape: BuildShape
    arrangement_matrix: ArrangementMatrix
    # Reserved plug-in points for later instrument steps.
    bass_pattern: str | None = None
    drum_groove: str | None = None
    motif_treatment: str | None = None
    guitar_program: int = 27
    meter: tuple[int, int] = (4, 4)
    repo_fingerprint: str = ""
    hook_id: str = ""
    hook_contour: tuple[int, ...] = ()
    hook_beats: tuple[float, ...] = ()
    hook_durations: tuple[float, ...] = ()
    hook_split: int = 5
    signature_id: str = ""
    signature_name: str = ""
    signature_reason: str = ""
    signature_score: float = 0.0

    def progression_for(self, section: str) -> tuple[int, ...]:
        return next(values for name, _, values in self.progressions if name == section)

    def progression_id_for(self, section: str) -> str:
        return next(identifier for name, identifier, _ in self.progressions if name == section)

    def pattern_for(self, section: str) -> str:
        return next(identifier for name, identifier in self.rhythm_patterns if name == section)

    def ornament_for(self, section: str) -> str:
        return next(identifier for name, identifier in self.ornaments if name == section)

    def chord_color_for(self, section: str) -> str:
        return next(identifier for name, identifier in self.chord_colors if name == section)

    def role_for(self, section: str, instrument: str) -> str:
        return self.arrangement_matrix.role(section, instrument)

    def fingerprint(self) -> tuple[str, ...]:
        return (
            *(f"p:{name}:{identifier}" for name, identifier, _ in self.progressions),
            *(f"r:{name}:{identifier}" for name, identifier in self.rhythm_patterns),
            f"v:{self.voicing_style}",
            f"b:{self.build_shape.name}",
            f"t:{self.tonic_pc}",
            f"mode:{self.key.mode}",
            f"meter:{self.meter[0]}/{self.meter[1]}",
            f"hook:{self.hook_id}",
            f"signature:{self.signature_id}",
            f"m:{self.arrangement_matrix.name}",
            f"bp:{self.bass_pattern}",
            f"dg:{self.drum_groove}",
            f"mt:{self.motif_treatment}",
            f"gp:{self.guitar_program}",
        )

    def summary(self) -> str:
        progressions = ", ".join(
            f"{section}={identifier}"
            for section, identifier, _ in self.progressions
        )
        patterns = ", ".join(
            f"{section}={identifier}" for section, identifier in self.rhythm_patterns
        )
        return (
            f"key={self.key.label} (family={self.mode_family}, tonic_pc={self.tonic_pc}); "
            f"meter={self.meter[0]}/{self.meter[1]}; repo_dna={self.repo_fingerprint[:12]}; "
            f"{self.signature_label}; "
            f"progressions[{progressions}]; patterns[{patterns}]; "
            f"voicing={self.voicing_style}; build={self.build_shape.name}; "
            f"matrix={self.arrangement_matrix.name}; bass={self.bass_pattern}; "
            f"drums={self.drum_groove}; motif={self.motif_treatment}; "
            f"guitar_program={self.guitar_program}"
        )

    @property
    def signature_label(self) -> str:
        return f"Signature: {self.signature_name}, because this repo is {self.signature_reason}"


def mode_family_for(profile: Profile, style: Style) -> str:
    if style.bright_mode_probability >= 1.0:
        return "majorish"
    if profile.health >= 0.70:
        return "majorish"
    if profile.health >= 0.48:
        return "modal"
    return "minorish"


def _progression_pool_for(
    style: Style, mode: str
) -> tuple[tuple[int, ...], ...]:
    """Return a style's validated four-bar pool for one mode."""

    pool = (style.progression_pools or {}).get(mode, ())
    if len(pool) < 4:
        raise ValueError(f"Style {style.name!r} needs four progressions for {mode}.")
    if len(set(pool)) != len(pool):
        raise ValueError(f"Style {style.name!r} has duplicate progressions for {mode}.")
    for progression in pool:
        if len(progression) != 4:
            raise ValueError(
                f"{style.name}/{mode}: progression {progression} must have four chords."
            )
        if any(degree < 1 or degree > 7 for degree in progression):
            raise ValueError(
                f"{style.name}/{mode}: progression {progression} must use "
                "diatonic degrees 1-7."
            )
    return pool


def sample_variation_plan(
    profile: Profile,
    style: Style,
    rng: random.Random,
) -> VariationPlan:
    """Sample all arrangement decisions from the composition's seeded RNG."""

    signature = choose_signature(profile)
    family = "majorish" if signature.id == "clean" else mode_family_for(profile, style)
    family_pool = (style.mode_families or {}).get(family)
    if not family_pool:
        raise ValueError(f"Style {style.name!r} has no modes for family {family!r}.")
    identity = profile_fingerprint(profile)
    base = hashlib.sha256(f"{identity}:{style.name}".encode("utf-8")).digest()
    dna_rng = random.Random(int.from_bytes(base[:8], "big"))
    tonic_pc = int.from_bytes(base[8:12], "big") % 12
    health = profile.health
    weights = []
    for candidate in family_pool:
        if candidate == "major":
            weight = 0.20 + 1.45 * health
        elif candidate == "lydian":
            weight = 0.15 + 0.90 * health
        elif candidate == "mixolydian":
            weight = 0.48 + 0.32 * health
        elif candidate == "dorian":
            weight = 0.35 + 0.45 * (1.0 - health)
        elif candidate == "minor":
            weight = 0.10 + 1.00 * (1.0 - health)
        else:  # phrygian
            weight = 0.05 + 0.70 * (1.0 - health)
        if candidate in MAJORISH_MODES:
            weight *= 1.0 + style.bright_mode_probability
        weights.append(weight)
    mode = dna_rng.choices(family_pool, weights=weights, k=1)[0]
    meter = style.meters[int.from_bytes(base[12:16], "big") % len(style.meters)]
    top_modules = sorted(profile.modules, key=lambda item: (-item.loc, item.name))[:3]
    # The signature hook is generated by the same antecedent/consequent phrase
    # grammar that writes the lead lines.  It is pinned to the fingerprint, so
    # every variation index develops the same recognisable idea.
    hook = build_hook(identity, tuple(module.name for module in top_modules))
    hook_contour = hook.degrees
    hook_id = hook.id
    if signature.id == "complexity" and (7, 8) in style.meters:
        meter = (7, 8)
    key = Key(tonic_pc=tonic_pc, mode=mode)

    progression_pool = _progression_pool_for(style, mode)
    pool_indices = list(range(len(progression_pool)))
    frame_indices = style.frame_indices_for(mode, len(progression_pool))
    intro_index = rng.choice(frame_indices)
    content_indices = [index for index in pool_indices if index != intro_index]
    rng.shuffle(content_indices)
    chosen_indices = {"intro": intro_index, "outro": intro_index}
    for offset, section in enumerate(
        ("theme", "development", "climax", "resolution")
    ):
        chosen_indices[section] = content_indices[offset % len(content_indices)]
    progressions = tuple(
        (
            section,
            f"{style.name}_{mode}_p{chosen_indices[section] + 1}",
            progression_pool[chosen_indices[section]],
        )
        for section in SECTION_NAMES
    )

    if len(style.piano_patterns) < 6:
        raise ValueError(f"Style {style.name!r} needs at least six piano patterns.")
    rhythm_patterns = tuple(
        (section, rng.choice(style.piano_patterns).name)
        for section in SECTION_NAMES
    )
    voicing = rng.choice(style.voicing_styles)
    shape = rng.choice(style.build_shapes)
    if signature.id == "sprawl":
        shape = next((item for item in style.build_shapes if item.name == "gradual"), shape)
    ornaments = tuple(
        (section, rng.choice(style.ornament_pool)) for section in SECTION_NAMES
    )
    color_weights = {
        "triad": max(0.02, 1.0 - style.seventh_probability),
        "seventh": max(0.02, style.seventh_probability - style.ninth_probability),
        "ninth": max(0.02, style.ninth_probability - style.eleventh_probability),
        "eleventh": max(0.02, style.eleventh_probability),
    }
    available_colors = [color for color in style.chord_colors]
    weights = [color_weights[color] for color in available_colors]
    colors = tuple(
        (section, rng.choices(available_colors, weights=weights, k=1)[0])
        for section in SECTION_NAMES
    )
    if not style.arrangement_matrices:
        raise ValueError(f"Style {style.name!r} has no arrangement matrices.")
    if not style.bass_patterns or not style.drum_grooves:
        raise ValueError(f"Style {style.name!r} needs bass and drum pools.")
    matrix = rng.choice(style.arrangement_matrices)
    style.validate_arrangement(matrix)
    bass_pattern = rng.choice(style.bass_patterns).name
    drum_groove = rng.choice(style.drum_grooves).name
    motif_treatment = rng.choice(style.motif_treatments)
    guitar_program = rng.choice(style.guitar_programs)

    return VariationPlan(
        mode_family=family,
        key=key,
        tonic_pc=tonic_pc,
        progressions=progressions,
        rhythm_patterns=rhythm_patterns,
        voicing_style=voicing.name,
        register_shift=voicing.target_shift,
        ornaments=ornaments,
        chord_colors=colors,
        build_shape=shape,
        arrangement_matrix=matrix,
        bass_pattern=bass_pattern,
        drum_groove=drum_groove,
        motif_treatment=motif_treatment,
        guitar_program=guitar_program,
        meter=meter,
        repo_fingerprint=identity,
        hook_id=hook_id,
        hook_contour=hook_contour,
        hook_beats=hook.beats,
        hook_durations=hook.durations,
        hook_split=hook.split,
        signature_id=signature.id,
        signature_name=signature.name,
        signature_reason=signature.reason,
        signature_score=signature.score,
    )


def fingerprint_distance(left: VariationPlan, right: VariationPlan) -> int:
    """Count changed arrangement traits (the fingerprints have equal length)."""

    return sum(a != b for a, b in zip(left.fingerprint(), right.fingerprint()))
