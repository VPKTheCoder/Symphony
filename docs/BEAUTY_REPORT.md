# Musical beauty upgrade — checkpoint

Status: **Steps 1-4 complete. Steps 5-8 remain.**
Branch: `main`  
HEAD at checkpoint: `105212c`  
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

## Verification at this checkpoint

| Check | Command | Result |
|---|---|---|
| Unit suite | `.\.venv\Scripts\python.exe -m unittest discover -s tests -q` | **39 passed** |
| Quality sweep | `.\.venv\Scripts\python.exe tools\validate_quality.py` | **320 / 320 passed** |
| Silence sweep | `.\.venv\Scripts\python.exe tools\validate_silence.py` | **64 / 64 passed** |
| Determinism | Covered by the unit suite | Byte-identical MIDI for same profile + style + seed |

The quality sweep covers scale membership, duration, register lanes and maximum
internal gap. All 320 compositions passed; the largest observed internal gap was
1.45 beats, below the 1.5-beat ceiling. The silence sweep covers internal
coverage for every profile/style pair at seeds 1, 7, 42 and 99, and all 64 cases
passed after the performance pass.

No WAV, stem or other generated audio is committed. Heavy output stays under
the ignored `out/` directory.

## Identity and contrast safeguards

- `anthem` is intentionally unchanged in role count and piano density. A test
  asserts its 1 / 4 / 4 / 5 / 4 / 1 active-part shape.
- The same repository + style + variation index still produces identical MIDI.
- Existing repository hooks and signature gestures are preserved; only gestures
  owned by an explicitly rested part are skipped.
- The final contrast matrix and before/after beauty scores are **not** claimed
  here. They are Step 8 deliverables and require rendered audio plus listening.

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

## Rendering dependency (Step 8 blocker)

`fluidsynth.exe` is not installed and there is no local GeneralUser GS SF2.
Only `pretty_midi`'s fallback `TimGm6mb.sf2` is available, which is not the
intended preview sound.

To unblock Step 8:

1. Install FluidSynth 2.3+ and expose it through `SYMPHONY_FLUIDSYNTH` or
   `PATH`.
2. Provide a verified redistributable GeneralUser GS SF2 and point
   `SYMPHONY_SOUNDFONT` at it.
3. Render the six preview combinations, then complete the listening pass.
4. Record the soundfont provenance and license in `THIRD_PARTY_NOTICES.md`.

Do not commit the soundfont or rendered audio.

## Remaining work

### Step 5 — soundfont and mastering research (next)

- Evaluate verified redistributable soundfont options; keep GeneralUser GS
  unless a clearly better, licensed option is found.
- Audit the mastering chain (EQ, compression, reverb, loudness) against the
  four style identities.
- Document any adopted asset or chain change, including licensing.

### Step 6 — curated progressions

- Replace or extend generic progression pools with curated, style-specific
  progressions that preserve each style's identity.
- Verify that progressions still support the phrase grammar and the repository
  hook.
- Keep the contrast gate and mode/root DNA behavior intact.

### Step 7 — scoring and best-of selection

- Add `score.py` with objective musical-quality metrics (phrase grammar, voice
  leading, density balance, rest placement, range, repetition).
- Add CLI `--best-of N` to render/compose N deterministic variations and select
  the highest score.
- Ensure the selected variation is reproducible and the score is emitted in the
  timeline/metadata.

### Step 8 — renders, report, contrast gate

- Render all requested profile/style combinations with the verified soundfont.
- Complete the before/after scorecard, listening notes, strengths/weaknesses,
  and final contrast matrix.
- Update `README.md` for `contemplative`, the Step 3 space policy, the Step 4
  performance pass, scoring, and `--best-of`.
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

Then start Step 5 from `105212c`. Keep one commit per completed step. If a step
fails three attempts, record the failure here and move on rather than looping.
