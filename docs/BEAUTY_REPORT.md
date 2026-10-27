# Musical beauty upgrade — final report

- Status: **Steps 1-8 complete.**
- Branch: `main`
- Step 8 baseline: `ebc233b` (Step 7 docs checkpoint)
- Last verified: 2026-10-27

This document is the final record of the eight-step musical-beauty upgrade. It
records what changed, the final renders and measurements, the contrast matrix,
the mastering decision, what is verified, and the listening checks that still
need human ears.

Step 8 produced documentation only. The final renders, A/B candidates and
measurement logs stay under the ignored `out/step8/` directory; no WAV, stem,
soundfont or other generated audio is committed.

## Outcome

- All eight steps are complete: phrase grammar, contemplative style,
  arrangement space, performance shaping, mastering, curated harmony, scoring,
  and final renders.
- The final gates pass: **61/61 unit tests**, **320/320 quality cases**,
  **64/64 silence cases**, and both contrast styles clear their thresholds.
- Ten final renders were produced and measured: the small profile in all four
  styles at seed 1, plus bat, fd and ripgrep in anthem and cinematic at
  variation index 0.
- Final scores range **86.55-95.00** (mean 92.28, standard deviation 2.59). The
  broader 80-composition calibration audit ranges **85.07-95.70** (mean 92.03,
  standard deviation 2.35).
- All ten masters are within **0.3 LU** of their style target, at or below
  **-1.5 dBTP**, with **zero clipped samples** and no measurable DC offset.
- No mastering EQ, bus compression or soundfont switch was adopted without
  listening evidence. The current chain and GeneralUser GS v1.471 remain.

## Completed steps

| Step | Scope | Commit |
|---|---|---|
| 1 | Phrase-grammar melody engine for lead instruments | `c18de00` |
| 2 | `contemplative` slow style | `7dddfb8` |
| 3 | Arrangement space, phrase rests, density budgets | `6f02c82` |
| 4 | Ensemble pocket, phrase dynamics, metric accents | `105212c` |
| 5 | Mastering audit, measured loudness, soundfont decision | `8d5069f` |
| 6 | Curated style-specific progressions and framing deal | `e0598d3` |
| 7 | Deterministic scoring and `--best-of` selection | `0bb6539` |
| 8 | Final renders, measurements, mastering A/B and report | docs only |

Documentation checkpoints: Step 3 `3d2ee30`, Step 4 `a2af6e9`, Step 5
`52615c2`, Step 6 `65ba007`, Step 7 `ebc233b`.

### Step 1 details

- Lead writing moved into a shared, deterministic phrase-grammar engine in
  `symphony/melody.py`. Violin, guitar and piano lead calls now share phrase
  planning instead of each instrument carrying its own contour rules.
- Phrases favour stepwise motion, prepare and recover leaps, anchor strong beats
  with chord tones, plan cadence targets, and leave phrase-level rests. The
  engine still respects each instrument's register lane and the repository hook.
- New coverage lives in `tests/test_melody.py` (step/leap behavior, chord-tone
  anchoring, cadence resolution, phrase density, register bounds and
  determinism).

### Step 2 details

- Added `contemplative` as a fourth style: slow tempo, two-bar vamps, sparse
  high replies, soft ostinato accompaniment and a long ring-out.
- The style was added without weakening the existing three styles. Anthem's
  role count and piano density were left untouched.
- New coverage lives in `tests/test_contemplative.py` (style parameters, form
  pacing, instrument behavior and scale safety).

### Step 3 details

- Spacious styles (`cinematic`, `lofi`, `contemplative`) allow at most **3**
  active parts outside the climax and **4** at the climax. `anthem` keeps
  **4 / 5** so its existing fullness is not damaged.
- Support parts breathe for one bar per four-bar phrase. Bass and drums rest at
  the phrase tail; guitar rests one bar earlier. Final section bars are never
  rested, and intro/outro are exempt so the frame stays intact.
- Piano comping has a per-bar attack budget: cinematic 6, lofi 7,
  contemplative 7, anthem 9. Drum density is capped per style.
- Repository signature gestures are suppressed when their instrument is marked
  `out` for the section, so a gesture cannot silently undo a rest.
- A post-render space pass removes attacks inside `out`/rest windows and clips
  notes that would otherwise ring across the boundary. It runs on the
  four-beat construction grid **before** meter warping; using the warped meter
  there was the cause of the two initial test failures and is now fixed.
- New coverage lives in `tests/test_space.py`.

### Step 4 details

- A deterministic ensemble pass in `symphony/performance.py` runs after all
  instruments are written and **before** the space policy, so a swung or
  accented note that lands in a rest is still removed.
- `lofi` is the only style with a global pocket: its `0.62` swing ratio becomes
  a `0.12`-beat delay on offbeats. The delay is applied to every non-piano part,
  including drums and the lead. Piano is excluded because it already applies
  swing internally; shifting it twice would distort the comping.
- Notes that share an onset (chords, kick-plus-snare, strum spreads) move
  together. A swung note is skipped if it would overtake a separate later
  attack, and its new onset is clamped inside the section.
- Support parts follow a four-bar phrase arc: neutral first bar, lift in the
  second, peak in the third, release in the fourth. The arc is scaled by
  `phrase_dynamic`; a small `metric_accent` lifts the downbeat and, more
  quietly, beat 3. Drum movement is reduced and piano accenting is left to the
  comping engine.
- Per-style values: cinematic `3.5 / 2.5`, lofi `2.5 / 1.5`, anthem
  `2.0 / 2.0`, contemplative `4.0 / 1.5` (`phrase_dynamic / metric_accent`).
- Lead velocity remains owned by the melody engine; only `support` roles
  receive the new dynamics. No random source is used, so MIDI stays
  byte-identical for the same profile, style and variation index.
- New coverage lives in `tests/test_performance.py` (swing placement, phrase
  arc, accents, lead preservation, velocity/timing bounds, byte determinism).

### Step 5 details

- **Soundfont: keep GeneralUser GS v1.471.** The installed bank is 31,281,186
  bytes, SHA-256 `f45b6b4a...b839a`, and the setup helper verifies the release
  archive before extraction. MuseScore_General (MIT) and FluidR3_GM (MIT) were
  evaluated as licensed alternatives; neither is clearly better for these five
  parts without an A/B listening test, and switching would change every timbre.
  The full comparison is in `docs/MASTERING.md`.
- **Raw synth clipping fixed.** FluidSynth now writes 32-bit float instead of
  16-bit; the anthem raw render reaches +0.9 dBTP and previously lost six
  clipped samples in the file converter.
- **Loudness overshoot fixed.** ffmpeg's `alimiter` auto-level defaults to on
  and was pushing every old master above its style target. The chain now
  disables auto-level and uses a measured two-pass `loudnorm` with the same
  `midi_end + 3.0 s` trim as the final pass. A 20 Hz high-pass removes
  sub-audible rumble without touching the bass lane's C1 fundamental.
- **Measured result.** The four fixed Step 5 masters hit -16.0 / -15.9 / -14.0
  / -17.4 LUFS (cinematic / lofi / anthem / contemplative), all at -1.5 dBTP
  with zero clipped samples. Loudness range increased by 1.8 / 2.1 / 0 / 0.2 LU,
  confirming the old limiter was flattening the dynamic arc.
- **Deliberately deferred.** Style EQ, bus compression, and the
  MuseScore_General A/B remained audition items until Step 8; they are still not
  adopted without listening.
- New coverage lives in `tests/test_render.py` (filter/target construction,
  measurement parsing, float synth output).

### Step 6 details

- **Style-owned harmony.** Each of the four styles now supplies five curated
  four-bar progressions for all six modes (120 progressions total). IDs are
  style-qualified (`{style}_{mode}_p{n}`), so a plan states exactly which
  harmony it uses instead of referencing a shared generic pool.
- **Identity per style.** Cinematic uses wide I-V-vi-IV arcs and plagal
  returns; lofi uses ii-V-I and descending-fifths turnarounds; anthem uses
  direct, singable cadences; contemplative holds two-bar vamps built from
  tonic-compatible cells. The pools differ in emphasis rather than sharing one
  generic set.
- **Frame-first deal.** Intro and outro share one framing progression chosen
  from the mode's frame set. Theme, development, climax and resolution deal the
  remaining entries in seeded order before reuse, so every five-entry pool is
  heard exactly once across the six sections.
- **Validation.** Sampling rejects pools shorter than four entries, duplicate
  loops, progressions that are not exactly four chords, and degrees outside
  1-7. Built-in pools are required to hold five entries. Cadence support
  requires at least three of five progressions to keep the tonic available
  under the answer phrase's final bar; for two-bar-chord styles that bar maps
  to the pool's second entry.
- **Contemplative minor framing.** The pool's i-VI and III-VI vamps are kept
  for content sections, but intro/outro draw only from indices 2 and 4
  (i-IV and i-VII). Framing with the vamps made the opening and closing solo
  skip too often; this fixes the regression without weakening the 0.70 melody
  gate or deleting good harmony.
- **Hook collision fixed.** Hook-family selection now uses two fingerprint
  bytes (`digest[9:11]`) instead of one. The old selector gave bat, fd and
  ripgrep the same contour because each selection byte was a multiple of five.
  Hooks remain deterministic, style-invariant and repository-qualified.
- New coverage lives in `tests/test_progressions.py` (pool shape and
  distinctness, diatonic safety, cadence support, frame restriction,
  deterministic style-qualified sampling).

### Step 7 details

- **Six weighted dimensions.** `symphony/score.py` measures phrase grammar
  (0.32), voice leading (0.20), density balance (0.18), rest placement (0.10),
  range shape (0.10) and repetition (0.10). Each dimension is clamped to 0-1;
  the weighted total is reported on a 0-100 scale. The scorer only reads the
  form, variation plan and rendered MIDI, so it adds no random source and does
  not change default composition output.
- **Phrase grammar** reuses `build_lead_line`, `plan_pitches` and
  `melody_quality`, rewarding stepwise motion, degree steps, prepared and
  recovered leaps, strong-beat chord tones and clean phrases.
- **Voice leading** groups simultaneous piano attacks into chords and measures
  rank-to-rank movement plus upper-voice spacing.
- **Density balance** checks that active parts actually sound, keeps the lead at
  a support-relative share, and correlates per-section note density with the
  dramatic intensity arc.
- **Rest placement** verifies cadence bars stay populated, support rests land in
  their intended phrase windows, rest positions vary, and the lead keeps some
  air.
- **Range shape** scores section spans, the global melodic span, and whether the
  highest lead pitch occurs in the climax.
- **Repetition** balances hook recurrence against progression, rhythm and
  adjacent-pitch variety rather than rewarding novelty unconditionally.
- **`--best-of N`.** The CLI builds N consecutive variations with no
  batch-diversity retry, scores each, and selects the highest unrounded total.
  Ties keep the lower candidate index. Because candidates use plain consecutive
  seeds, re-running with the winner's seed reproduces its MIDI byte for byte.
  Only the winner is written and rendered. `--best-of` and `--variations` are
  mutually exclusive.
- **Metadata.** The CLI always adds `score` to the timeline; `--best-of` also
  adds `selection` with the candidate count, winning index and winning seed.
  `score.py` can be run standalone with text or `--json` output.
- **Calibration audit.** Across 80 compositions (4 profiles x 4 styles x 5
  seeds), overall scores ranged 85.07-95.70 (mean 92.03, standard deviation
  2.35). Voice leading had the widest component spread (0.424-0.912), followed
  by range shape (0.650-1.000) and rest placement (0.703-0.999). No dimension
  was constant across the catalogue, so the weights were kept as designed.
- New coverage lives in `tests/test_score.py` (component bounds and weights,
  score determinism, distinct variation scores, consecutive candidate seeds,
  tie-breaks, exact winner rebuild, argument exclusivity and timeline metadata).

### Step 8 details

**Render set.** Ten final tracks were rendered through the verified
GeneralUser GS v1.471 + FluidSynth 2.6.1 + ffmpeg 8.1.1 chain. The four
small-profile style demos use fixed seed 1 so all styles share one variation
index. The six repository tracks use variation index 0, whose effective base
seed is derived from the repository fingerprint and style. Rendered MIDI, WAV,
MP3, timeline, profile and measurement files remain under `out/step8/` and are
not committed.

**Final musical identity and scores.**

| Track | Source | Style | Variation | Key / mode | Meter | Tempo | Score |
|---|---|---|---:|---|---|---:|---:|
| bat_anthem | bat | anthem | 0 | B dorian | 7/8 | 122 | 91.96 |
| bat_cinematic | bat | cinematic | 0 | Eb major | 4/4 | 79 | 95.00 |
| fd_anthem | fd | anthem | 0 | Ab major | 7/8 | 108 | 86.55 |
| fd_cinematic | fd | cinematic | 0 | Db mixolydian | 7/8 | 70 | 94.19 |
| ripgrep_anthem | ripgrep | anthem | 0 | B lydian | 4/4 | 121 | 91.12 |
| ripgrep_cinematic | ripgrep | cinematic | 0 | G major | 4/4 | 77 | 94.90 |
| small_anthem | small (`lumen`) | anthem | 1 | F lydian | 7/8 | 117 | 91.24 |
| small_cinematic | small (`lumen`) | cinematic | 1 | B major | 3/4 | 72 | 93.54 |
| small_contemplative | small (`lumen`) | contemplative | 1 | Eb major | 4/4 | 65 | 89.69 |
| small_lofi | small (`lumen`) | lofi | 1 | F major | 4/4 | 80 | 94.59 |

**Final audio measurements.** Targets are shown in parentheses beside each
integrated loudness value. Band shares are relative to total spectral power.

| Track | LUFS (target) | LRA | True peak | Centroid | Side/mid | 20-40 Hz | 2.5-5 kHz | 5-10 kHz | Clipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bat_anthem | -13.9 (-14.0) | 8.0 LU | -1.5 dBTP | 698 Hz | -11.3 dB | -45.3 dB | -16.5 dB | -28.0 dB | 0 |
| bat_cinematic | -16.1 (-16.0) | 17.2 LU | -1.5 dBTP | 432 Hz | -15.0 dB | -40.0 dB | -22.3 dB | -35.4 dB | 0 |
| fd_anthem | -13.8 (-14.0) | 8.2 LU | -1.5 dBTP | 647 Hz | -10.9 dB | -43.4 dB | -19.3 dB | -22.5 dB | 0 |
| fd_cinematic | -16.1 (-16.0) | 13.1 LU | -1.5 dBTP | 488 Hz | -12.2 dB | -41.8 dB | -22.6 dB | -32.9 dB | 0 |
| ripgrep_anthem | -13.8 (-14.0) | 7.8 LU | -1.5 dBTP | 607 Hz | -11.5 dB | -50.9 dB | -20.3 dB | -24.0 dB | 0 |
| ripgrep_cinematic | -15.8 (-16.0) | 17.3 LU | -1.5 dBTP | 469 Hz | -13.8 dB | -50.0 dB | -20.9 dB | -37.8 dB | 0 |
| small_anthem | -13.7 (-14.0) | 8.6 LU | -1.5 dBTP | 623 Hz | -10.7 dB | -40.1 dB | -20.2 dB | -25.5 dB | 0 |
| small_cinematic | -15.9 (-16.0) | 14.9 LU | -1.5 dBTP | 490 Hz | -12.5 dB | -46.1 dB | -22.4 dB | -39.9 dB | 0 |
| small_contemplative | -17.4 (-17.5) | 11.2 LU | -1.7 dBTP | 434 Hz | -13.4 dB | -40.7 dB | -20.4 dB | -35.1 dB | 0 |
| small_lofi | -15.8 (-16.0) | 8.6 LU | -1.5 dBTP | 470 Hz | -12.4 dB | -33.3 dB | -27.8 dB | -46.1 dB | 0 |

All ten tracks have zero clipped samples and DC offset below 1.1 x 10^-6, which
is zero at measurement precision. Durations range from 170.9 to 199.4 seconds
(2:51 to 3:19), inside the 2-4 minute quality target.

**Loudness and headroom.** Every track lands within 0.3 LU of its style target.
The anthems are the loudest by design (-13.7 to -13.9 LUFS against -14.0), the
cinematics and lofi sit around -15.8 to -16.1 against -16.0, and contemplative
is the quietest at -17.4 against -17.5. True peaks are -1.5 dBTP except
contemplative at -1.7 dBTP. The previous raw 16-bit anthem clipping and the
auto-level limiter overshoot are both gone.

**Spectral balance and width.** Anthems are the brightest group (centroids
607-698 Hz, strongest 2.5-5 kHz and 5-10 kHz shares). Cinematics are warmer
(432-490 Hz) with the widest loudness range (13.1-17.3 LU), matching their long
build-and-release shape. Lofi is the darkest and has the strongest low-band
share (470 Hz, -33.3 dB in 20-40 Hz) and the weakest 5-10 kHz share (-46.1 dB).
Contemplative is the warmest
overall (434 Hz) and the most mid-dominant. Side/mid ratios stay between -10.7
and -15.0 dB, so all ten mixes keep a stable stereo image without becoming
over-wide.

**Mastering A/B decision.** Four deferred candidates were rendered from the
final small-profile masters, gain-matched to the base loudness, and measured.
They are kept only under ignored `out/step8/ab/` for optional human audition.

| Style | Candidate filter | Filtered I | Matched gain | Centroid base -> candidate | LRA base -> candidate | Candidate peak | Decision |
|---|---|---:|---:|---|---:|---:|---|
| lofi | low-pass 14 kHz + low shelf +2 dB at 180 Hz | -15.6 LUFS | -0.20 dB | 470 -> 458 Hz | 8.6 -> 8.5 LU | -1.2 dBTP | not adopted |
| cinematic | air shelf +1.5 dB at 8 kHz | -15.9 LUFS | 0.00 dB | 490 -> 489 Hz | 14.9 -> 14.9 LU | -1.5 dBTP | not adopted |
| contemplative | air shelf +1.0 dB at 9 kHz | -17.4 LUFS | 0.00 dB | 434 -> 434 Hz | 11.2 -> 11.3 LU | -1.7 dBTP | not adopted |
| anthem | glue compressor -18 dB, 2:1, 20/250 ms | -17.1 LUFS | +3.40 dB | 623 -> 613 Hz | 8.6 -> 6.4 LU | -0.4 dBTP | not adopted |

The lofi shelf moves the centroid by only 12 Hz and slightly reduces the
loudness range; the cinematic and contemplative shelves are effectively
inaudible in the measurements (1 Hz or less). The anthem compressor costs
2.2 LU of loudness range and pushes the candidate peak to -0.4 dBTP, which is
worse headroom than the current -1.5 dBTP master. No EQ, bus compression or
soundfont change is adopted. MuseScore_General is not installed locally, so
that A/B remains a future human audition; switching banks without listening
evidence would change every timbre and invalidate the committed examples.

**Final contrast matrix.** Default variation, measured by
`python -m symphony.contrast`.

| Pair | Anthem | Cinematic |
|---|---:|---:|
| bat / fd | 7/8 | 8/8 |
| bat / ripgrep | 6/8 | 4/8 |
| fd / ripgrep | 8/8 | 8/8 |

The anthem minimum is **6/8**; the cinematic minimum is **4/8**. The cinematic
bat/ripgrep pair is still the weakest: they share mode, meter, signature and a
two-BPM tempo difference, while key, all six progressions, all six rhythms and
the hook contour differ. It passes, but it is the first pair to re-check after
any future key, tempo or progression change.

**Before/after scorecard.** The new scorer did not exist before this upgrade,
so there is no valid pre-upgrade numeric score to compare. The table below uses
categorical baseline comparisons and final measured evidence instead.

| Area | Before this upgrade | Final state | Evidence |
|---|---|---|---|
| Lead writing | Lead phrasing lived in per-instrument contour rules; no shared phrase grammar | Shared deterministic phrase-grammar engine with prepared/recovered leaps, chord-tone anchors, cadence targets and phrase rests | `tests/test_melody.py`; final phrase-grammar components 0.94-0.99 |
| Style breadth | Three styles; no slow, spacious idiom | Four styles including contemplative at 65 BPM with two-bar vamps and a long ring-out | `tests/test_contemplative.py`; `small_contemplative` scores 89.69 |
| Arrangement space | Density could accumulate; no phrase-level rest policy | Spacious styles cap 3 active parts outside the climax and 4 at it; anthem intentionally keeps 4/5; support rests one bar per phrase | `tests/test_space.py`; silence sweep 64/64, maximum 1.43 beats |
| Performance feel | Humanization was per-note; no phrase arc or global pocket | Four-bar phrase dynamics, metric accents and lofi swing; lead velocity preserved | `tests/test_performance.py`; byte-identical MIDI |
| Mastering | Old masters ran 0.4-2.2 LU hot, peaked at -1.0 dBTP, and the 16-bit anthem clipped six samples | Within 0.3 LU of target, at or below -1.5 dBTP, zero clipped samples, 32-bit float synth | `docs/MASTERING.md`; final measurement table |
| Harmony identity | Generic shared progression pool; five loops could repeat across a section | 120 style-qualified progressions; frame-first deal hears all five; contemplative minor framing fixed | `tests/test_progressions.py`; final contrast matrix |
| Variation selection | No objective score; only batch variations | Six-dimension deterministic score, `--best-of`, reproducible winner, timeline metadata | `tests/test_score.py`; 80-composition audit |
| Repository contrast | Earlier identity gap gave fd and ripgrep the same key and mode, a 3-BPM tempo difference, identical progressions and rhythms, and no repository-level hook | All three pairs clear 4/8 in both styles; hooks and signatures are distinct | Final contrast matrix; `docs/diagnosis.md` for the baseline gap |

Final numeric evidence: the ten final renders score 86.55-95.00 (mean 92.28,
standard deviation 2.59), and the broader 80-composition audit scores
85.07-95.70 (mean 92.03, standard deviation 2.35).

**Strengths and weaknesses.** The strongest results are the style separation
(cinematic mean 94.41 across four tracks), the restored headroom, and the
consistent contrast between repositories. The weakest final score is
`fd_anthem` at 86.55, driven by a voice-leading component of 0.5085; that is a
future improvement target, not a Step 8 regression. The score distribution is
also high and compressed (most tracks are in the low 90s), so the scorer is
useful for choosing among candidates but is not an absolute grade.

## Verification at the final checkpoint

| Check | Command | Result |
|---|---|---|
| Unit suite | `.\.venv\Scripts\python.exe -m unittest discover -s tests -q` | **61 passed** |
| Quality sweep | `.\.venv\Scripts\python.exe tools\validate_quality.py` | **320 / 320 passed**; maximum internal gap **1.45 beats** |
| Silence sweep | `.\.venv\Scripts\python.exe tools\validate_silence.py` | **64 / 64 passed**; maximum internal silence **1.43 beats** |
| Contrast gate | `python -m symphony.contrast <bat> <fd> <ripgrep> --style anthem` | All pairs pass; minimum **6/8** |
| Contrast gate | `python -m symphony.contrast <bat> <fd> <ripgrep> --style cinematic` | All pairs pass; minimum **4/8** |
| Final renders | Ten tracks measured with `ebur128=peak=true`, decoded spectral/stereo analysis | **10 / 10** within 0.3 LU; **-1.5 dBTP** (contemplative -1.7); **0 clipped**; 0 DC |
| Score audit | 80 compositions, 4 profiles x 4 styles x 5 seeds | **85.07-95.70**; mean 92.03; standard deviation 2.35 |
| Final render scores | Ten final tracks | **86.55-95.00**; mean 92.28; standard deviation 2.59 |
| Determinism | Covered by the unit suite | Byte-identical MIDI for the same profile + style + seed; best-of winner rebuilds exactly |
| Repository state | `git status --short` and `git diff --check` before commit | Documentation-only changes; no audio added |

The quality sweep covers scale membership, duration, register lanes and maximum
internal gap. All 320 compositions passed; the largest observed internal gap was
1.45 beats, below the 1.5-beat ceiling. The silence sweep covers internal
coverage for every profile/style pair at seeds 1, 7, 42 and 99, and all 64 cases
passed. Both sweeps were re-run after the Step 6 pool and hook changes, after
Step 7, and again for this final checkpoint.

## Identity and contrast safeguards

- `anthem` is intentionally unchanged in role count and piano density. A test
  asserts its 1 / 4 / 4 / 5 / 4 / 1 active-part shape.
- The same repository + style + variation index still produces identical MIDI.
  Scoring is read-only and adds no random source.
- Existing repository hooks and signature gestures are preserved; only gestures
  owned by an explicitly rested part are skipped. Hook contours remain stable
  across styles and are selected from the repository fingerprint.
- Curated progressions stay inside the repository's mode, so the hook's scale
  and cadence behavior does not change.
- `--best-of` does not use the batch-diversity retry. Every candidate is a plain
  consecutive seed, and the winner's MIDI rebuilds byte for byte with
  `--seed <winner>`. Equal scores keep the lower candidate index.
- Step 8 changed documentation only. The default composition and render paths
  are unchanged from `ebc233b`.

## Known limitations and follow-up

- **Subjective listening is still pending.** The objective gates and
  measurements pass, but they cannot judge pocket, blend, emotional arc or
  whether a specific phrase rest feels premature. The checklist below is the
  remaining human work.
- **MuseScore_General A/B not performed.** The bank is not installed locally.
  Keep GeneralUser GS until a matched-loudness audition shows a clear
  improvement across all five parts.
- **Cinematic bat/ripgrep is exactly at 4/8.** It passes, but future changes to
  keys, tempo mapping or progressions can drop it below the gate.
- **The score is a comparative selector.** Its catalogue mean is high (92.03)
  and most final tracks sit in the low 90s. Use it to choose among candidates,
  not as an absolute beauty grade.
- **`fd_anthem` voice leading is the weakest final component (0.5085).** Its
  86.55 score is the lowest of the final set. This is a candidate for a future
  targeted improvement, not a Step 8 regression.
- **`--best-of N` composes and scores all N candidates before choosing.** It is
  a quality tool, not a speed optimization; keep N modest for routine renders.
- **MIDI time-signature metadata stays 4/4 for 7/8 plans.** Meter is conveyed by
  the existing bar-warping path, and this behavior was intentionally left
  unchanged. Do not "fix" it without a separate musical review.
- **The committed `examples/*.mp3` files are the earlier identity-demo set.**
  They were not replaced. The final beauty-upgrade audio and measurements stay
  under ignored `out/step8/`; only documentation is committed.

## Subjective listening checklist

These are the checks that remain for a human listener. Compare tracks at
matched loudness, not by raw file level.

| Priority | Tracks | Listen for |
|---|---|---|
| 1 | All four anthems | Fullness at the climax, bass weight, piano density, drum punch, and no thinning from the space policy. Confirm the 1 / 4 / 4 / 5 / 4 / 1 active-part shape still feels like an anthem. |
| 2 | `small_contemplative` | Whether development and resolution feel spacious rather than empty; whether the two-bar vamps sustain interest and the long ring-out lands. |
| 3 | 7/8 tracks (`bat_anthem`, `fd_anthem`, `fd_cinematic`, `small_anthem`) | Section seams and bar-warp transitions; whether the space pass leaves any awkward clipped ring. |
| 4 | `small_lofi` | Swing pocket, dark tone, section seams, and whether the support phrase arcs feel detached from the lead. |
| 5 | Cinematics | The long build-and-release arc, guitar bloom, and whether the drum density cap softens the climax too much. |
| 6 | bat vs fd vs ripgrep | Identity at matched loudness: hook contour, signature gesture, key/mode character, and whether each still sounds like its repository. |
| 7 | Optional mastering A/B | Compare `out/step8/ab/*_candidate.wav` with the base masters. The current chain remains the default; adopt a candidate only if it clearly wins by ear. |
| 8 | Optional best-of check | Compare a `--best-of` winner with its runner-up to confirm the score's preference matches musical preference, not just smoother piano voicing. |

## Reproduction

The final render set used the verified local soundfont and native tools. A fresh
checkout must run `python tools/setup.py` and install FluidSynth and ffmpeg
separately. The renderer checks `SYMPHONY_SOUNDFONT` / `SYMPHONY_FLUIDSYNTH`,
local `tools/`, then `PATH`.

```powershell
# Small-profile style demos, fixed seed 1.
python -m symphony.compose --profile profiles/small.json --style anthem        --seed 1 --out out/step8/small_anthem
python -m symphony.compose --profile profiles/small.json --style cinematic     --seed 1 --out out/step8/small_cinematic
python -m symphony.compose --profile profiles/small.json --style lofi          --seed 1 --out out/step8/small_lofi
python -m symphony.compose --profile profiles/small.json --style contemplative --seed 1 --out out/step8/small_contemplative

# Repository tracks, default variation index 0.
python -m symphony.compose --repo out/.repo-cache/bat     --style anthem    --out out/step8/bat_anthem
python -m symphony.compose --repo out/.repo-cache/bat     --style cinematic --out out/step8/bat_cinematic
python -m symphony.compose --repo out/.repo-cache/fd      --style anthem    --out out/step8/fd_anthem
python -m symphony.compose --repo out/.repo-cache/fd      --style cinematic --out out/step8/fd_cinematic
python -m symphony.compose --repo out/.repo-cache/ripgrep --style anthem    --out out/step8/ripgrep_anthem
python -m symphony.compose --repo out/.repo-cache/ripgrep --style cinematic --out out/step8/ripgrep_cinematic
```

The measurement scripts and logs are local artifacts under the ignored `out/`
directory and are not part of the committed repository. The final numbers in
this report come from `out/step8/measurements.json` and
`out/step8/ab/measurements.json`.

## Resume instructions

```powershell
git switch main
git pull --ff-only
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe tools\validate_quality.py
.\.venv\Scripts\python.exe tools\validate_silence.py
python -m symphony.contrast out/.repo-cache/bat out/.repo-cache/fd out/.repo-cache/ripgrep --style anthem
python -m symphony.contrast out/.repo-cache/bat out/.repo-cache/fd out/.repo-cache/ripgrep --style cinematic
```

Step 8 is complete as documentation. Future work should start from the human
listening checklist above; do not re-run the upgrade steps unless a listening
problem identifies a specific regression.
