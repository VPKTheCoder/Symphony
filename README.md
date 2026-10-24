# Symphony

Turn a software codebase profile into an instrumental track.

**Stage 2 lineup:** acoustic grand piano, bass, GM drum kit (MIDI channel 10),
violin lead, and guitar. All five tracks are implemented. The composer is
instrumental only.

## Current previews

| Preview | Profile | Style | Length |
|---|---|---|---|
| `out/step1_small_cinematic` | healthy, 5 modules | cinematic | 3:10 |
| `out/step1_small_lofi` | healthy, 5 modules | lo-fi | 2:43 |
| `out/step1_large_cinematic` | messy, 12 modules | cinematic | 3:13 |
| `out/step1_large_lofi` | messy, 12 modules | lo-fi | 2:47 |

Step 1b listening previews (seed 42): `out/step1b_small_cinematic`,
`out/step1b_small_lofi`, `out/step1b_small_anthem`,
`out/step1b_large_cinematic`, `out/step1b_large_lofi`, and
`out/step1b_large_anthem`.

Checkpoint A (piano + bass + drums, seed 42): `out/checkpointA_small_cinematic`,
`out/checkpointA_small_lofi`, `out/checkpointA_small_anthem`, and the matching
`out/checkpointA_large_*` files. Piano+bass stage previews are in
`out/step2_bass_<profile>_<style>`.

Checkpoint B (full band, seed 42): `out/checkpointB_small_cinematic`,
`out/checkpointB_small_lofi`, `out/checkpointB_small_anthem`, and the matching
`out/checkpointB_large_*` files.

Each prefix has `.mid`, `.wav` and `.mp3`. The `.mid` is the deterministic
artifact; the audio has light reverb, mastering and a fade.

## Setup

Requirements: Python 3.11+, Git, FluidSynth CLI, ffmpeg. The Python requirements
include the Tree-sitter runtime and Rust grammar used by Stage 1.

```powershell
python -m pip install -r requirements.txt
```

Assets used here:

- **GeneralUser GS v1.471** – `soundfonts/GeneralUser-GS.sf2`
  ([source](https://github.com/ROCKNIX/generaluser-gs), by S. Christian Collins).
- **FluidSynth 2.6.1 Windows x64** – `tools/fluidsynth/.../bin/fluidsynth.exe`.
- **ffmpeg** – found on `PATH`.

The renderer looks for the SoundFont and FluidSynth locally first. You can
override either with `SYMPHONY_SOUNDFONT` or `SYMPHONY_FLUIDSYNTH`, or install
both on `PATH`.

## Run

```powershell
python -m symphony.compose `
  --profile profiles/small.json `
  --style cinematic `
  --seed 42 `
  --out out/track
```

Produces:

```
out/track.mid
out/track.wav
out/track.mp3
```

Add `--stems` to write one WAV per instrument beside the full mix:

```powershell
python -m symphony.compose --profile profiles/small.json --style anthem --seed 42 --out out/track --stems
```

Fast MIDI-only pass:

```powershell
python -m symphony.compose --profile profiles/large.json --style lofi --seed 7 --out out/sketch --no-render
```

Styles: `cinematic`, `lofi`, `anthem`.

## Stage 1: Rust analyzer

The analyzer reads Rust syntax with `tree-sitter` and `tree-sitter-rust`. It
uses tracked and non-ignored untracked files, honors `.gitignore`, and skips
`target/`, `vendor/`, `build/`, `build.rs`, and files marked as generated.
Cargo workspace crates become top-level groups in module names. Small modules
are folded into their parent or an `other` group so a profile contains at most
14 modules.

Analyze a local repository and save a profile in the schema accepted by the
composer:

```powershell
python -m symphony.analyze D:/code/my-rust-app --out profiles/my-rust-app.json
```

Pass `--entry <module>` to choose the call-path root. For libraries without a
`main()`, the analyzer starts at `lib.rs` and follows its module declaration
order. `--explain` prints each module metric beside its musical mapping.

```powershell
python -m symphony.analyze D:/code/my-rust-app `
  --out profiles/my-rust-app.json `
  --entry app::search `
  --explain
```

### Metric derivation

- **LOC:** nonblank code lines; comment-only lines are excluded.
- **Complexity:** per-function counts of `if`, match arms, loops, `&&`, `||`,
  and `?`, summed in each module, then combined rank and logarithmic normalized
  to 0–1 across the repository.
- **Unsafe:** counts of unsafe blocks, unsafe functions, and unsafe impls.
  Global `unsafe_ratio` is unsafe constructs divided by unsafe constructs plus
  function count.
- **TODO:** TODO/FIXME comments plus `todo!()` and `unimplemented!()` calls.
- **Dependencies:** internal module references from `crate::`, `super::`,
  `self::`, and module declarations; incoming module edges become
  `depended_by_count`.
- **Coverage:** `coverage_source: "proxy"` labels the default proxy. It compares
  test functions (`#[test]`, `#[cfg(test)]` modules, and `tests/`) to public
  functions, clamped to 0–1. This is not execution-based code coverage. Supply
  `--lcov path/to/lcov.info` to use LCOV line coverage instead; the output then
  labels `coverage_source` as `lcov`.
- **Global metrics:** `avg_complexity` averages module complexity ranks;
  `test_coverage` weights module coverage by public function count; and
  `unsafe_ratio` uses the count ratio above. They all remain in 0–1.

For example, generate `fd`'s profile with an optional explanation:

```powershell
python -m symphony.analyze out/.repo-cache/fd --out profiles/fd.json --explain
```

### Analyze, compose and render in one command

`--repo` accepts a local path or a Git URL. URLs are cloned with
`git clone --depth 1` into `out/.repo-cache/` and reused on later runs.

```powershell
python -m symphony.compose `
  --repo https://github.com/sharkdp/fd `
  --style anthem `
  --seed 42 `
  --out out/fd-anthem `
  --explain
```

This writes `out/fd-anthem.profile.json`, the MIDI/WAV/MP3, and
`out/fd-anthem.timeline.json`. The timeline records each section's start and
end time, its module mapping, and timestamps for complexity, unsafe, TODO and
coverage-cadence moments. Every compose run prints a listening-guide table at
the end. Profile-based composition also writes a timeline and guide.

## What is implemented

### Form

- Six sections: intro → theme → development → climax → resolution → outro.
- The call path is split in order across the four content sections. The intro
  and outro are framing material.
- Section bars scale with the summed LOC of their modules; the total is
  compressed to a 2–4 minute target independent of codebase size.
- Fixed dramatic intensity arc, with a small amount of module-complexity
  shading already applied.

### Key, tempo and harmony

- Health from coverage, unsafe ratio and average complexity selects a mode
  family: major/lydian, dorian/mixolydian, or minor/phrygian.
- `avg_complexity` maps inside the style tempo range (cinematic 70–104 BPM,
  lo-fi 83–102 BPM, anthem 120–140 BPM).
- Per-mode functional progression pools (for example I–V–vi–IV in major and
  i–VI–III–VII in minor).
- Chords are built by stacking scale tones, with style-dependent 7ths, 9ths and
  added 9ths. Every note stays inside the selected scale.
- Upper voices are chosen with smooth voice leading and a style-specific
  register target.

### Instruments

- Cinematic: wide rolled voicings, sustained bass, sparse high replies,
  arpeggiated development, full climax and a long tonic coda.
- Lo-fi: swung eighths, softer dynamics, 7th/9th colour, syncopated stabs and a
  lower register.
- Anthem: bright major-family harmony, driving syncopated chord accents,
  punchy articulation, short pedal and octave doubling in the climax.
- Humanization: per-note timing jitter, chord rolls, velocity accents and
  section/phrase dynamics. Sustain pedal is generated as CC64.
- Same-pitch overlaps are clipped so repeated notes retrigger cleanly.
- Piano left hand stays above C3; bass occupies C1–C3.
- Bass follows chord roots with curated passing-tone, syncopated, and sustained
  patterns. High dependency load favors longer, deeper roots.
- The GM drum kit uses MIDI channel 10. Style grooves drop out in the intro and
  outro; fills occur only at section boundaries, with a build before the climax.
- The `VariationPlan` samples a curated arrangement matrix for all five parts.
  Each section assigns every instrument `out`, `support`, or `lead`; at most one
  part leads and at least one rests outside the climax.
- Piano, bass, and drums carry per-track CC7 volume, CC10 pan, and CC91 reverb.
- Violin motifs are two-bar, scale-constrained phrases derived from a stable
  hash of each module name. Returning modules reuse their motif identity;
  phrases repeat, transpose, invert, extend, or fragment, with chord tones on
  strong beats, contour, rests, and unsafe-hotspot tremolo.
- Cinematic guitar uses clean/acoustic arpeggios and swells that enter in the
  later sections. Lo-fi uses soft jazzy stabs. Anthem uses driving power-chord
  eighths and a guitar hook in the climax or when the violin rests.
- Violin stays at G3 or above; guitar stays between E2 and E5. Guitar avoids
  parallel melody doubling outside deliberate lead passages.
- All five tracks carry CC7 volume, CC10 pan, and CC91 reverb. Piano and violin
  sit right of center, guitar left of center, and bass/drums center.

### Rendering

- FluidSynth + GeneralUser GS, stereo 44.1 kHz.
- Gentle style-specific reverb from FluidSynth.
- ffmpeg loudness normalization, true-peak limiting, tail trim and fade.
- MP3 encoded from the mastered WAV.

## Determinism

A single `random.Random(seed)` is created in `build_composition()` and passed
explicitly to the form planner and instrument renderers. Instruments share the
plan for structural decisions. There is no global RNG.
The same profile + style + seed produces a byte-identical MIDI file.

## Variations

Each composition samples one `VariationPlan`. The profile pins the mode family,
tempo, section order and lengths, and module-to-section mapping. The plan varies
the key within that family, per-section progressions and piano patterns, chord
color, voicing/register, ornaments, build shape, bass/drum patterns, guitar
program, motif treatment, and arrangement matrix. Its fingerprint is checked
against earlier tracks in a batch; near-duplicate plans are resampled
deterministically. Module motif identities remain pinned to their names.

Generate a distinct batch with consecutive seeds and numbered output files:

```powershell
python -m symphony.compose `
  --profile profiles/small.json `
  --style anthem `
  --seed 42 `
  --variations 4 `
  --out out/anthem
```

This writes `out/anthem_v1.mid/.wav/.mp3` through `out/anthem_v4.mid/.wav/.mp3`
and prints each plan summary. Quality checks across seeds 1–20 for all profile
and style combinations:

```powershell
python tools/validate_quality.py
python -m unittest discover -s tests -v
```

Check note coverage (all profile/style pairs, seeds 1, 7, 42 and 99):

```powershell
python tools/validate_silence.py
```

## Metric mapping

| Input | Musical decision |
|---|---|
| `global.test_coverage`, `unsafe_ratio`, `avg_complexity` | Health → mode family |
| `avg_complexity` | Tempo within the style range |
| `call_path` order | Section order and module grouping |
| module `loc` | Section length (compressed with a square-root weight) |
| module `complexity` | Section intensity shading, busier drums, higher violin register, denser guitar rhythm |
| `depended_by_count` | Longer, deeper bass notes |
| `unsafe_count` | In-scale tritone/diminished moment and violin tremolo |
| `test_coverage` | Open vs. resolved cadence |
| `todo_count` | Brief rest and sus4 suspension in the rhythm section |
| repeated module in `call_path` | Returning deterministic leitmotif |

## Code map

```
symphony/
  theory.py          scales, chords, progressions, voicing
  styles.py          style parameter sets
  profile.py         typed profile loading / validation
  form.py            section pacing and harmony grid
  instruments/
    piano.py         piano arrangement
    bass.py          root-following bass
    drums.py         style grooves and boundary fills
    motifs.py        stable module-name-derived motif shapes
    violin.py        motif lead and development
    guitar.py        style-specific comping and lead hooks
  compose.py         CLI and composition assembly
  render.py          FluidSynth + ffmpeg pipeline
profiles/
  small.json         healthy 5-module profile
  large.json         messy 12-module profile
```

The full-band Checkpoint B previews are ready for listening; the next step is to
collect feedback and make any mix or arrangement adjustments.
