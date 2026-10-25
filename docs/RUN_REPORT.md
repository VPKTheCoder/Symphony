# Symphony run report

## Step 1 — baseline verification

- Unit tests: **10 passed** on the existing local Python 3.14 environment.
- CI-equivalent no-render compose: **passed** for `profiles/small.json`,
  cinematic, seed 42.
- Asset isolation: `SYMPHONY_SOUNDFONT` and `SYMPHONY_FLUIDSYNTH` were unset;
  the local `.sf2` and `tools/fluidsynth/` directory were temporarily renamed;
  `PATH` contained Python, Git, and Windows system directories only, so neither
  FluidSynth nor ffmpeg was discoverable. Both local asset paths were restored.
- No Step 1 code fixes were needed.

## Step 3 — analyzer signal

- Global complexity now uses a sigmoid of raw branch complexity per function;
  the existing module `complexity` value remains rank/log normalized within a
  repository for local shading.
- Added optional `rust_features` metadata for traits, impls, generic parameters,
  lifetimes, macro definitions/invocations/proc-macro attributes, async
  functions, `?`, unwrap/expect/panic calls, closures, iterator chain length,
  clones, public API, module depth, and dependency-hub concentration. Ratios
  accompany the counts where meaningful.
- Old profile JSON remains accepted with an empty optional feature map.
  Coverage still reports `proxy` unless `--lcov` is supplied.
- Analyzer tests: **6 passed**. One iterator-chain assertion first exposed
  generic-call handling around `collect::<...>()`; the parser traversal was
  fixed and the focused suite then passed.
- On the cached real repositories, calibrated complexity was 0.423854 for fd
  and 0.378811 for ripgrep; their feature profiles differ substantially.

## Step 4 — musical DNA

- Added a SHA-256 repository identity from crate/repo name and sorted module
  structure. The optional profile field is backward compatible; old profiles
  derive the same kind of identity from their name and module data.
- Root choice now covers all twelve pitch classes. Metrics weight all six
  curated modes; DNA selects the stable mode/root/meter, and the calibrated
  absolute complexity plus a DNA nudge selects tempo. Meters supported by the
  current curated style pools are cinematic/lo-fi 4/4, 6/8, 3/4 and anthem 4/4,
  7/8. Meter timing is warped bar-by-bar without changing pitches or registers.
- The effective RNG seed is derived from repo fingerprint, style, and the
  `--seed` variation index (default 0). Profile-derived form and hook identity
  stay pinned across variation indices.
- Added a four-bar diatonic hook derived from repo identity and the top three
  modules. Violin, guitar, piano, bass, and drums state it in intro, theme,
  development, climax, and outro; development inverts it and later phrases
  vary its scale-degree offset. Hook ID and contour are included in timeline
  JSON.
- Full unit suite: **14 passed**. A 48-profile sweep exercised every root in
  cinematic, lo-fi, and anthem; selected meters stayed inside each style's
  curated set.
- Current cached output summary (anthem / cinematic): fd = Ab major, 7/8 /
  Db mixolydian, 4/4; ripgrep = B lydian, 4/4 / G major, 3/4. Their four
  variation plans have different progression and rhythm fingerprints.

## Step 5 — signature features

- Added deterministic, normalized feature-extreme selection for exactly one primary
  signature per profile. The selected motif gesture is rendered in all five parts
  through intro, theme, development, climax, and outro; signature prose is included
  in timeline JSON and the listening guide.
- Added audible gestures for unsafe code (in-scale tritone alternation/tremolo),
  complexity (7/8 where curated, accent hats), Result/error handling (split
  call-and-response), traits/generics (staggered canon), async (offset layers),
  iterator use (scalar runs), TODOs (suspensions/open ending), hub concentration
  (bass pedal), sprawling size (slower gradual build and climax transposition), and
  clean profiles (major-family selection and high tonic cadence).
- Expanded every style's curated meter pool to include 7/8.
- Tests: **14 passed**. One pre-existing DNA meter assertion was updated to include
  the newly supported 7/8 option.

## Step 6 — contrast gate

- Added `python -m symphony.contrast <repo...> --style anthem|cinematic`. It
  analyzes and composes each repository with variation index 0, then compares
  key, mode, tempo, meter, progression IDs, rhythm IDs, signature, and hook
  contour. Pairs below 4 of 8 differing dimensions fail with exit status 1.
- Tuning iteration 1 (fd/ripgrep): both styles scored 7/8; the shared hook
  contour was the only melodic identity overlap. Iteration 2 derived the full
  anchored eight-note contour from the repository fingerprint: both styles
  scored 8/8, including distinct hook contours. The final threshold remains 4/8.
- Final cached fd/ripgrep runs passed: anthem 8/8; cinematic 8/8.
- The initial Git clone used Windows Schannel and failed with
  `SEC_E_NO_CREDENTIALS`. Retrying with Git's OpenSSL TLS backend succeeded;
  bat was cloned and all requested Rust repositories became analyzable. The
  local Symphony project has no Rust sources and correctly fails analysis as
  non-applicable.
- Step 6 sweep results are finalized below after bat became available.

## Step 7 — tests and validation

- Expanded unit coverage to assert signature prose/moments appear in at least three
  sections. The suite now passes **15/15**, including byte-identical MIDI,
  variation-pinned profile structure, and instrument register lanes.
- Added scale quantization after rendering for any generated notes outside the
  active scale. The sprawling signature's climax is validated in its transposed
  scale, which fixed the earlier false positives in the quality validator.
- `tools/validate_quality.py`: **240/240 compositions passed** (scale, registers,
  max internal silence <=1.5 beats, 2–4 minute duration).
- `tools/validate_silence.py`: **all 24 checked compositions passed**.
- Asset-free run: hid the local SoundFont and tools/fluidsynth directory, unset
  Symphony asset environment variables, and restricted PATH to Git plus Windows
  system tools (no ffmpeg or FluidSynth); **15/15 unit tests passed** and the
  CI-equivalent cinematic `--no-render` composition produced MIDI and timeline.
  The initial PATH experiment also hid Git and failed six analyzer setup hooks;
  restoring Git alone resolved those harness errors.

## Step 8 — renders and documentation

- Rendered all six requested repo/style combinations using GeneralUser GS,
  FluidSynth, and ffmpeg. MP3 encoding is fixed at 160 kbps; output sizes range
  from 3.32 to 3.72 MB. MIDI, WAV, and timeline JSON remain in ignored `out/`.
- Updated README Listen links, DNA/signature explanations, contrast commands,
  listening guidance, metrics, and proxy coverage caveat.
- Final default-variation metadata:

| Repo | Style | Key / mode | Tempo | Meter | Signature |
|---|---|---|---:|---:|---|
| fd | anthem | Ab major | 108 BPM | 7/8 | Grand slow build and climax key change — large/sprawling |
| fd | cinematic | Db mixolydian | 70 BPM | 7/8 | Grand slow build and climax key change — large/sprawling |
| ripgrep | anthem | B lydian | 121 BPM | 4/4 | Heroic resolved cadences and soaring lead — clean/well-tested |
| ripgrep | cinematic | G major | 77 BPM | 4/4 | Heroic resolved cadences and soaring lead — clean/well-tested |
| bat | anthem | B dorian | 122 BPM | 7/8 | Heroic resolved cadences and soaring lead — clean/well-tested |
| bat | cinematic | Eb major | 79 BPM | 4/4 | Heroic resolved cadences and soaring lead — clean/well-tested |

- Final contrast-gate pairwise matrix (distance / 8; minimum 4):

| | fd | ripgrep | bat |
|---|---:|---:|---:|
| fd | — | 8 anthem / 8 cinematic | 7 anthem / 8 cinematic |
| ripgrep | 8 anthem / 8 cinematic | — | 6 anthem / 4 cinematic |
| bat | 7 anthem / 8 cinematic | 6 anthem / 4 cinematic | — |

- All three pairs passed both styles. All six signature motifs have distinct
  interval contours across repositories; hook returns in five sections.
