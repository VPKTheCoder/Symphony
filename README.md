# Symphony

Turn a software codebase profile into an instrumental track.

## Listen

Repository-specific examples (160 kbps MP3, each under 5 MB):

- [fd — anthem: grand slow build and climax key change](examples/fd_anthem.mp3)
- [fd — cinematic: grand slow build and climax key change](examples/fd_cinematic.mp3)
- [ripgrep — anthem: heroic resolved cadences and soaring lead](examples/ripgrep_anthem.mp3)
- [ripgrep — cinematic: heroic resolved cadences and soaring lead](examples/ripgrep_cinematic.mp3)
- [bat — anthem: heroic resolved cadences and soaring lead](examples/bat_anthem.mp3)
- [bat — cinematic: heroic resolved cadences and soaring lead](examples/bat_cinematic.mp3)
- [Cinematic profile demo](examples/cinematic.mp3) · [Lo-fi profile demo](examples/lofi.mp3) · [Anthem profile demo](examples/anthem.mp3)

Each song has its own fingerprint-derived key and hook. The signature is
introduced, developed, brought back at the climax, and recalled in the outro.
See the timeline JSON emitted beside each render for timestamps and a listening
guide.

**Stage 2 lineup:** acoustic grand piano, bass, GM drum kit (MIDI channel 10),
violin lead, and guitar. All five tracks are implemented. The composer is
instrumental only.

## Setup

Requirements: Python 3.11+, Git, FluidSynth CLI, ffmpeg. The Python requirements
include the Tree-sitter runtime and Rust grammar used by Stage 1.

### Windows (PowerShell)

```powershell
python -m pip install -r requirements.txt
python tools/setup.py
```

### macOS / Linux (bash)

```bash
python3 -m pip install -r requirements.txt
python3 tools/setup.py
```

The setup helper downloads GeneralUser GS v1.471 from the author's release,
checks its SHA-256, and keeps the included license beside the SoundFont. It
prints FluidSynth and ffmpeg installation instructions for Windows, macOS, and
Linux. The renderer checks `SYMPHONY_SOUNDFONT` / `SYMPHONY_FLUIDSYNTH`, then
local tools, then `PATH`. For best compatibility use FluidSynth 2.3 or newer.

## Run

```powershell
python -m symphony.compose `
  --profile profiles/small.json `
  --style cinematic `
  --seed 42 `
  --out out/track
```

The same command in bash:

```bash
python -m symphony.compose --profile profiles/small.json --style cinematic --seed 42 --out out/track
```

Analyze a Rust repository, compose it, and render it (same form works in bash
and PowerShell):

```bash
python -m symphony.compose --repo https://github.com/sharkdp/fd --style anthem --out out/fd-anthem
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
  and `?`. Global complexity uses an absolute sigmoid calibration of raw
  branch load per function; module complexity is rank/log normalized only
  within the repository for local emphasis.
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
- **Global metrics:** `avg_complexity` is the absolute calibrated signal;
  `test_coverage` weights the proxy (or LCOV, when provided) by public function
  count; and `unsafe_ratio` uses the count ratio above. All remain in 0–1.
- **Rust-specific optional features:** `rust_features` includes counts/ratios
  for traits, impls, generics, lifetimes, macros/proc-macro use, async functions,
  `?`, unwrap/expect/panic, closures, iterator chains/calls, clones, public API,
  module depth, and dependency-hub concentration. Older profile files remain
  valid without this field.

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

- A SHA-256 musical DNA fingerprint uses the crate/repository name and sorted
  module structure. It selects any of the twelve chromatic roots and nudges the
  metric-driven mode, tempo, and curated meter. Supported meters include 4/4,
  6/8, 3/4, and 7/8; tempo ranges are wider and vary by style.
- `--seed` is the variation index (default `0`). The base seed comes from the
  repository fingerprint and style, so the same repo/style/index reproduces a
  byte-identical MIDI file.
- Per-mode functional progression pools (for example I–V–vi–IV in major and
  i–VI–III–VII in minor).
- Chords are built from curated scale tones, with style-dependent 7ths, 9ths
  and added 9ths. Pitched notes are checked against the active scale; the
  sprawling signature deliberately transposes the climax up a whole step.
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

### Musical DNA, hook, and repository signature

- A four-bar, eight-note diatonic hook is derived from the fingerprint plus the
  three largest module names. Violin states it while piano/guitar double or
  answer; bass and drums share its rhythm. The hook appears in intro, theme,
  development, climax, and outro, with inversion and variation in development.
- Exactly one primary signature is selected from the strongest normalized
  repository feature. Its treatment is parameterized inside the same composer:

| Repository signal | Audible signature |
|---|---|
| Unsafe-heavy | In-scale tritone riff, violin tremolo, dark pedal |
| High complexity | Odd-meter accents and busy hats |
| Result/`?`-heavy | Call-and-response, stumble, then recovery |
| Trait/generic-heavy | Staggered canon imitating the hook |
| Async-heavy | Syncopated interlocking layers |
| Iterator-heavy | Flowing scalar runs and rising sequence |
| TODO-heavy | Suspensions and a hanging phrase ending |
| One dominant dependency hub | Pedal-tone bass drone |
| Large and sprawling | Slow gradual build and climax key change |
| Clean and well-tested | Bright major family, resolved cadence, soaring lead |

The exact signature and its reason are repeated in at least three timeline
sections and in the printed listening guide. Signatures used in the demo set:
fd uses the grand slow build/key change; ripgrep and bat use heroic resolved
cadences and soaring leads.

### Contrast gate

Run the default variation for a set of local Rust repositories or Git URLs and
fail when any pair differs in fewer than four identity dimensions (key, mode,
tempo, meter, progressions, rhythm, signature, hook contour):

```powershell
python -m symphony.contrast D:/code/fd D:/code/ripgrep D:/code/bat --style anthem
python -m symphony.contrast D:/code/fd D:/code/ripgrep D:/code/bat --style cinematic
```

For listening, start with the intro hook, listen for the named signature as the
piece develops, compare its return at the climax, then check whether the outro
recalls the hook. Each rendered `*.timeline.json` has section timestamps and
these listening prompts.

### Rendering

- FluidSynth + GeneralUser GS, stereo 44.1 kHz.
- Gentle style-specific reverb from FluidSynth.
- ffmpeg loudness normalization, true-peak limiting, tail trim and fade.
- MP3 encoded from the mastered WAV.

## Licensing

Symphony's code is licensed under Apache-2.0 (see [LICENSE](LICENSE)). See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party component
licenses and the SoundFont's accompanying license. Music generated by Symphony
belongs to whoever generates it; use it however you like.

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
| repository fingerprint | Root key, hook contour, stable DNA nudge for mode/meter/tempo |
| `global.test_coverage`, `unsafe_ratio`, `avg_complexity` | Health and metric-weighted mode selection |
| absolute global `avg_complexity` | Tempo and complexity signature selection |
| `call_path` order | Section order and module grouping |
| module `loc` | Section length (compressed with a square-root weight) |
| module `complexity` | Section intensity shading, busier drums, higher violin register, denser guitar rhythm |
| `depended_by_count` | Longer, deeper bass notes |
| `unsafe_count` | In-scale tritone/diminished moment and violin tremolo |
| `test_coverage` | Open vs. resolved cadence |
| `todo_count` | Brief rest and sus4 suspension in the rhythm section |
| repeated module in `call_path` | Returning deterministic leitmotif |
| optional `rust_features` ratios/counts | Select exactly one primary repository signature |
| `coverage_source: "proxy"` | Test-count estimate, not execution coverage; `--lcov` supplies real line coverage |

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

The compact MP3 demos in `examples/` are the shareable full-band previews.
