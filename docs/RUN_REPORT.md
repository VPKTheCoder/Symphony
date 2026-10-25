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
