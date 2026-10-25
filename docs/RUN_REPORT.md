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
