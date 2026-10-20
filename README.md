# Symphony

Turn a software codebase profile into an instrumental track.

**Stage 2, step 1 of 6 is built:** theory, functional harmony, piano voicing and
the complete MIDI → WAV → MP3 pipeline. Bass, drums, violin/leitmotifs and the
full code-metric tension map come in the next listening passes.

## Current previews

| Preview | Profile | Style | Length |
|---|---|---|---|
| `out/step1_small_cinematic` | healthy, 5 modules | cinematic | 3:10 |
| `out/step1_small_lofi` | healthy, 5 modules | lo-fi | 2:43 |
| `out/step1_large_cinematic` | messy, 12 modules | cinematic | 3:13 |
| `out/step1_large_lofi` | messy, 12 modules | lo-fi | 2:47 |

Each prefix has `.mid`, `.wav` and `.mp3`. The `.mid` is the deterministic
artifact; the audio has light reverb, mastering and a fade.

## Setup

Requirements: Python 3.11+, FluidSynth CLI, ffmpeg.

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

Fast MIDI-only pass:

```powershell
python -m symphony.compose --profile profiles/large.json --style lofi --seed 7 --out out/sketch --no-render
```

Styles: `cinematic`, `lofi`.

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
- `avg_complexity` maps inside the style tempo range (70–104 BPM for these two
  styles).
- Per-mode functional progression pools (for example I–V–vi–IV in major and
  i–VI–III–VII in minor).
- Chords are built by stacking scale tones, with style-dependent 7ths, 9ths and
  added 9ths. Every note stays inside the selected scale.
- Upper voices are chosen by exhaustive search with smooth rank-to-rank voice
  leading, wide spacing and a register target. Bass roots stay in C2–B2.

### Piano

- Cinematic: wide rolled voicings, sustained bass, sparse high replies,
  arpeggiated development, full climax and a long tonic coda.
- Lo-fi: swung eighths, softer dynamics, 7th/9th colour, syncopated stabs and a
  lower register.
- Humanization: per-note timing jitter, chord rolls, velocity accents and
  section/phrase dynamics. Sustain pedal is generated as CC64.
- Same-pitch overlaps are clipped so repeated notes retrigger cleanly.

### Rendering

- FluidSynth + GeneralUser GS, stereo 44.1 kHz.
- Gentle style-specific reverb from FluidSynth.
- ffmpeg loudness normalization, true-peak limiting, tail trim and fade.
- MP3 encoded from the mastered WAV.

## Determinism

A single `random.Random(seed)` is created in `build_composition()` and passed
explicitly to the form planner and instrument renderers. There is no global RNG.
The same profile + style + seed produces a byte-identical MIDI file.

## Metric mapping

| Input | Musical decision |
|---|---|
| `global.test_coverage`, `unsafe_ratio`, `avg_complexity` | Health → mode family |
| `avg_complexity` | Tempo within the style range |
| `call_path` order | Section order and module grouping |
| module `loc` | Section length (compressed with a square-root weight) |
| module `complexity` | Section intensity shading now; drum density, extensions and violin register next |
| `depended_by_count` | Long deep bass notes (step 2) |
| `unsafe_count` | Tritone/diminished moment, violin tremolo (step 5) |
| `test_coverage` | Open vs. resolved cadence (step 5) |
| `todo_count` | Rest or sus4 suspension (step 5) |
| repeated module in `call_path` | Leitmotif return (step 4) |

## Code map

```
symphony/
  theory.py          scales, chords, progressions, voicing
  styles.py          style parameter sets
  profile.py         typed profile loading / validation
  form.py            section pacing and harmony grid
  instruments/
    piano.py         piano arrangement
  compose.py         CLI and composition assembly
  render.py          FluidSynth + ffmpeg pipeline
profiles/
  small.json         healthy 5-module profile
  large.json         messy 12-module profile
```

## Not yet built

- Electric/acoustic bass and module-dependency bass logic.
- Drums and style grooves/fills.
- Violin leitmotifs generated from module-name hashes.
- Full module-level tension mapping and cadence control.
- Final render polish pass.
