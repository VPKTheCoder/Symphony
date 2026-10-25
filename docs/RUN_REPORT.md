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
