# Musical beauty upgrade — checkpoint

Status: **Steps 1-7 complete. Step 8 remains.**
Branch: `main`  
HEAD at checkpoint: `0bb6539`  
Last verified: 2026-10-27

This document is the continuation point for the eight-step musical-beauty
upgrade. It records what changed, what is verified, what is deliberately
deferred, and the exact next move.

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
  bytes, SHA-256 `f45b6b4a…b839a`, and the setup helper verifies the release
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
- **Measured result.** The four fixed masters hit -16.0 / -15.9 / -14.0 /
  -17.4 LUFS (cinematic / lofi / anthem / contemplative), all at -1.5 dBTP with
  zero clipped samples. Loudness range increased by 1.8 / 2.1 / 0 / 0.2 LU,
  confirming the old limiter was flattening the dynamic arc.
- **Deliberately deferred.** Style EQ, bus compression, and the
  MuseScore_General A/B are Step 8 audition items; they are not adopted
  without listening.
- New coverage lives in `tests/test_render.py` (filter/target construction,
  measurement parsing, float synth output).

### Step 6 details

- **Style-owned harmony.** Each of the four styles now supplies five curated
  four-bar progressions for all six modes (120 progressions total). IDs are
  style-qualified (`{style}_{mode}_p{n}`), so a plan states exactly which
  harmony it uses instead of referencing a shared generic pool.
- **Identity per style.** Cinematic uses wide I–V–vi–IV arcs and plagal
  returns; lofi uses ii–V–I and descending-fifths turnarounds; anthem uses
  direct, singable cadences; contemplative holds two-bar vamps built from
  tonic-compatible cells. The pools differ in emphasis rather than sharing one
  generic set.
- **Frame-first deal.** Intro and outro share one framing progression chosen
  from the mode's frame set. Theme, development, climax and resolution deal the
  remaining entries in seeded order before reuse, so every five-entry pool is
  heard exactly once across the six sections.
- **Validation.** Sampling rejects pools shorter than four entries, duplicate
  loops, progressions that are not exactly four chords, and degrees outside
  1–7. Built-in pools are required to hold five entries. Cadence support
  requires at least three of five progressions to keep the tonic available
  under the answer phrase's final bar; for two-bar-chord styles that bar maps
  to the pool's second entry.
- **Contemplative minor framing.** The pool's i–VI and III–VI vamps are kept
  for content sections, but intro/outro draw only from indices 2 and 4
  (i–IV and i–VII). Framing with the vamps made the opening and closing solo
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
  range shape (0.10) and repetition (0.10). Each dimension is clamped to 0–1;
  the weighted total is reported on a 0–100 scale. The scorer only reads the
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
- **Calibration audit.** Across 80 compositions (4 profiles × 4 styles × 5
  seeds), overall scores ranged 85.07–95.70 (mean 92.03, standard deviation
  2.35). Voice leading had the widest component spread (0.424–0.912), followed
  by range shape (0.650–1.000) and rest placement (0.703–0.999). No dimension
  was constant across the catalogue, so the weights were kept as designed.
- New coverage lives in `tests/test_score.py` (component bounds and weights,
  score determinism, distinct variation scores, consecutive candidate seeds,
  tie-breaks, exact winner rebuild, argument exclusivity and timeline metadata).

## Verification at this checkpoint

| Check | Command | Result |
|---|---|---|
| Unit suite | `.\.venv\Scripts\python.exe -m unittest discover -s tests -q` | **61 passed** |
| Quality sweep | `.\.venv\Scripts\python.exe tools\validate_quality.py` | **320 / 320 passed** |
| Silence sweep | `.\.venv\Scripts\python.exe tools\validate_silence.py` | **64 / 64 passed** |
| Contrast gate | `python -m symphony.contrast <bat> <fd> <ripgrep> --style anthem` | All pairs pass; minimum **6/8** |
| Contrast gate | `python -m symphony.contrast <bat> <fd> <ripgrep> --style cinematic` | All pairs pass; minimum **4/8** |
| Score audit | 80 compositions, 4 profiles × 4 styles × 5 seeds | **85.07–95.70**; mean 92.03; stdev 2.35 |
| Mastered audio | Four styles rendered at Step 5, `ebur128=peak=true` | Targets hit; **-1.5 dBTP**; 0 clipped samples |
| Determinism | Covered by the unit suite | Byte-identical MIDI for same profile + style + seed; best-of winner rebuilds exactly |

The quality sweep covers scale membership, duration, register lanes and maximum
internal gap. All 320 compositions passed; the largest observed internal gap was
1.45 beats, below the 1.5-beat ceiling. The silence sweep covers internal
coverage for every profile/style pair at seeds 1, 7, 42 and 99, and all 64 cases
passed. Both sweeps were re-run after the Step 6 pool and hook changes and again
after Step 7. Step 7 adds read-only scoring and a selection path; it does not
change the default MIDI output or the render path, so the Step 5 mastering
measurements remain valid.

Contrast-gate distances for the three cached Rust repositories:

| Pair | Anthem | Cinematic |
|---|---:|---:|
| bat / fd | 7/8 | 8/8 |
| bat / ripgrep | 6/8 | 4/8 |
| fd / ripgrep | 8/8 | 8/8 |

The cinematic bat/ripgrep pair sits exactly on the 4/8 threshold. Their shared
dimensions are mode, meter, signature and a two-BPM tempo difference; key,
progressions, rhythms and hook contour all differ. This is the weakest pair.
Step 7 did not change default variation selection and the gate still measures
4/8, but Step 8 should re-check it after any mastering or arrangement change.

No WAV, stem or other generated audio is committed. Heavy output stays under
the ignored `out/` directory.

## Identity and contrast safeguards

- `anthem` is intentionally unchanged in role count and piano density. A test
  asserts its 1 / 4 / 4 / 5 / 4 / 1 active-part shape.
- The same repository + style + variation index still produces identical MIDI.
- Existing repository hooks and signature gestures are preserved; only gestures
  owned by an explicitly rested part are skipped. Hook contours are still chosen
  from the repository fingerprint and remain stable across styles.
- Curated progressions stay inside the repository's mode, so the hook's scale
  and cadence behavior does not change. The contrast gate passes on all three
  cached repositories in both anthem and cinematic.
- Step 7 scoring is read-only and deterministic. The default compose path still
  produces the same MIDI for a given profile, style and variation index; the
  only added output is score metadata.
- `--best-of` does not use the batch-diversity retry. Every candidate is a plain
  consecutive seed, and the winner's MIDI rebuilds byte for byte with
  `--seed <winner>`. Equal scores keep the lower candidate index.
- The Step 7 numeric score is a comparative selector, not the final beauty
  judgment. The final contrast matrix and before/after listening scorecard are
  **not** claimed here; they are Step 8 deliverables and require rendered audio
  plus listening.

## Known risks to audit in Step 8

- The new rests trade density for air. The MIDI validators prove coverage, not
  whether a specific four-bar rest feels premature or exposes a weak harmony.
- Contemplative is the sparsest style and has the highest risk of sounding
  empty in development/resolution.
- Meter-warped pieces need auditioning at section boundaries; the space pass
  now uses the correct pre-warp grid, but only listening confirms the seams.
- Drum density caps may soften the cinematic climax more than intended.
- Step 4's swing and phrase dynamics are objective MIDI changes, not yet
  auditioned. Step 8 must check that the lofi pocket does not smear section
  seams, and that support-only arcs do not make the accompaniment feel
  detached from the lead.
- Step 5's corrected masters are 0.4-2.2 LU quieter than the old files. Compare
  them at matched loudness, not by raw level, so the extra dynamics are not
  mistaken for weakness.
- Style EQ, bus compression, and the MuseScore_General A/B are still unadopted
  because they need a listening decision.
- The curated pools trade generic familiarity for style identity. Step 8 should
  check that five four-bar loops stretched across a section do not feel
  repetitive, especially in contemplative where each chord lasts two bars.
- The cinematic bat/ripgrep contrast pair is exactly at the 4/8 minimum. Any
  later change to keys, tempo mapping or progressions can drop it below the
  gate.
- The Step 7 score is a relative selector. Its catalogue mean is high (92.03)
  and voice leading supplies much of the candidate spread, so Step 8 should
  confirm by ear that `--best-of` winners are actually the stronger versions,
  not just the ones with smoother piano voicings.
- `--best-of N` composes and scores all N candidates before choosing. It is a
  quality tool, not a speed optimization; keep N modest for routine renders.

## Rendering dependencies (Step 8 ready)

FluidSynth 2.6.1, ffmpeg 8.1.1, and GeneralUser GS v1.471 are installed
locally. None of these assets is committed: a fresh checkout must run
`python tools/setup.py` for the verified soundfont and install FluidSynth and
ffmpeg separately. The renderer checks `SYMPHONY_SOUNDFONT` /
`SYMPHONY_FLUIDSYNTH`, local `tools/`, then `PATH`.

Step 8 can render on this machine. Do not commit the soundfont, native tools,
or rendered audio.

## Remaining work

### Step 8 — renders, report, contrast gate (next)

- Render all requested profile/style combinations with the verified soundfont.
- Complete the before/after scorecard, listening notes, strengths/weaknesses,
  and final contrast matrix.
- Audition the deferred mastering items: lofi low-pass/low shelf, cinematic and
  contemplative air shelves, anthem glue compression, and the
  MuseScore_General A/B.
- Update `README.md` for any Step 8 mastering changes; scoring and `--best-of`
  are already documented.
- Re-run the full unit suite plus both validation sweeps.
- Commit the final documentation and previews metadata (never the audio).

## Resume instructions

```powershell
git switch main
git pull --ff-only
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe tools\validate_quality.py
.\.venv\Scripts\python.exe tools\validate_silence.py
```

Then start Step 8 from `0bb6539`. Keep one commit per completed step. If a step
fails three attempts, record the failure here and move on rather than looping.
