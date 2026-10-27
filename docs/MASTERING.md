# Mastering and SoundFont research

Status: **Step 5 complete; Step 8 A/B measured, 2026-10-27**

This note records the soundfont decision and the mastering audit performed after
the Step 4 performance pass. It is the reference for the Step 8 rendered
comparison and final decision.

## SoundFont decision

**Keep GeneralUser GS v1.471.** It is the bank already used by every example,
its license permits private and commercial music creation, modification, and
redistribution with the license, and the setup helper verifies the release
archive before extraction.

Installed asset (ignored by Git, not committed):

| Item | Value |
|---|---|
| File | `soundfonts/GeneralUser-GS.sf2` |
| Size | 31,281,186 bytes |
| SHA-256 | `f45b6b4a68b6bf3d792fcbb6d7de24dc701a0f89c5900a21ef3aaaece993b839a` |
| License | `soundfonts/LICENSE-GeneralUser-GS.txt`, License v2.0 |
| Archive check | `tools/setup.py` verifies SHA-256 `4203835164766f428c4926c097c9ea58dae431c7fb8f9dbe277b92d80da45ec2` |

The license is permissive for music and software use, but it openly notes that
some samples came from third-party free banks whose provenance cannot be fully
traced. That uncertainty is acceptable for this project's use, but it is
recorded in `THIRD_PARTY_NOTICES.md` rather than hidden.

### Alternatives considered

| Bank | License | Size | Why it was not adopted |
|---|---|---|---|
| **MuseScore_General** | MIT; based on FluidR3Mono, with a published sample-source CSV | 206 MB SF2 / 38 MB SF3 | The strongest licensed fallback and cleaner provenance, but adopting it would change every timbre and require a larger setup download. No A/B listening evidence yet that it is clearly better for these five parts. |
| **FluidR3_GM** | MIT (Fedora package metadata; original release by Frank Wen) | Large GM bank | Older than MuseScore_General, which is itself derived from it; no quality or size advantage for this project. |
| **Timbres of Heaven / Arachno / other free GM banks** | Often non-commercial or unverifiable | Varies | Rejected on licensing grounds; not safe to make part of a redistributable setup. |
| **pretty_midi fallback `TimGm6mb.sf2`** | Bundled fallback | Very small | Clearly lower quality; only suitable as a last-resort preview, not as the reference sound. |

The decision is intentionally conservative: the repository identity and every
committed preview were voiced with GeneralUser GS. A future A/B that
demonstrates a clear improvement can revisit this, but it must update the
setup download, notices, render references, and all examples together.

## Mastering audit

FluidSynth 2.6.1 and ffmpeg 8.1.1 are installed locally under `tools/` and
`PATH`, so the chain was measured on real renders rather than estimated.

### Findings before the change

1. **The synth file stage clipped.** FluidSynth's default 16-bit raw file cut
   six samples in the anthem render. Rendering float samples instead preserves
   the waveform; the raw anthem true peak is **+0.9 dBFS**, which must be
   handled by the master chain rather than by the synth's file converter.
2. **The limiter was raising the master.** ffmpeg's `alimiter` has
   `level=true` (auto-level) as its default. After `loudnorm` had hit the
   target, the limiter boosted the output back toward the ceiling. Every old
   master came out above its style target, by 0.4-2.2 LU in this sample.
3. **Single-pass `loudnorm` was not exact.** With the limiter fixed, the anthem
   hit -14.0 LUFS, but lofi landed at -15.0 instead of -16.0. The one-pass
   approximation is not reliable enough for a fixed reference.
4. **There was no rumble filter.** DC offsets were tiny, but a standard
   sub-audible high-pass adds margin without touching the bass lane's lowest
   fundamental (C1, 32.7 Hz).

### Adopted chain

1. FluidSynth renders **32-bit float** (`audio.file.format=float`) at 44.1 kHz,
   stereo, with the style's reverb and a fixed 0.85 synth gain.
2. A measurement pass runs `highpass=f=20` and `loudnorm` with the style target,
   emitting the JSON summary. Measurement and mastering use the same
   `midi_end + 3.0 s` trim.
3. The mastering pass runs `highpass=f=20`, two-pass `loudnorm` with the
   measured values and `linear=true`, the existing 1.2-second reverse fade, and
   `alimiter=limit=0.95:level=false` as a safety net only.
4. MP3 remains 160 kbps CBR; WAV remains 24-bit PCM.

The change is deterministic: the same MIDI and soundfont produce the same
measurement and the same master. It costs one extra ffmpeg analysis pass,
roughly ten seconds for a three-minute track on this machine.

### Before / after (small profile, seed 1)

| Style | Target | Old I | Old LRA | Old peak | New I | New LRA | New peak |
|---|---:|---:|---:|---:|---:|---:|---:|
| cinematic | -16.0 | -14.3 | 8.6 | -1.0 | **-16.0** | 10.4 | -1.5 |
| lofi | -16.0 | -14.5 | 8.5 | -1.0 | **-15.9** | 10.6 | -1.5 |
| anthem | -14.0 | -13.6 | 6.9 | -1.0 | **-14.0** | 6.9 | -1.5 |
| contemplative | -17.5 | -15.3 | 10.5 | -1.1 | **-17.4** | 10.7 | -1.5 |

All four fixed masters have no clipped samples, zero DC offset, and -1.5 dBTP.
The extra loudness range confirms that the old auto-level limiter was flattening
the quiet-to-loud arc, especially in cinematic and lofi.

### Spectral balance (fixed masters)

| Style | Centroid | LRA | Side/mid | 20-40 Hz | 2.5-5 kHz | 5-10 kHz |
|---|---:|---:|---:|---:|---:|---:|
| cinematic | 477 Hz | 10.4 LU | -12.9 dB | -48.0 dB | -22.6 dB | -35.4 dB |
| lofi | 492 Hz | 10.6 LU | -12.0 dB | -31.3 dB | -26.6 dB | -44.3 dB |
| anthem | 610 Hz | 6.9 LU | -11.8 dB | -39.3 dB | -19.5 dB | -23.4 dB |
| contemplative | 458 Hz | 10.7 LU | -12.4 dB | -39.2 dB | -19.3 dB | -33.7 dB |

Band values are share of total spectral power in dB. The balances follow the
arrangements: anthem is the brightest and most present, lofi is the darkest,
and contemplative is warm and wide. No tonal equalizer is applied yet.

## Step 8 audition result

The four candidates were rendered from the final small-profile masters at seed
1, gain-matched to the base loudness, and measured with the same chain.

| Style | Candidate | Centroid base -> candidate | LRA base -> candidate | Candidate peak | Decision |
|---|---|---:|---:|---:|---|
| lofi | low-pass 14 kHz + low shelf +2 dB at 180 Hz | 470 -> 458 Hz | 8.6 -> 8.5 LU | -1.2 dBTP | not adopted |
| cinematic | air shelf +1.5 dB at 8 kHz | 490 -> 489 Hz | 14.9 -> 14.9 LU | -1.5 dBTP | not adopted |
| contemplative | air shelf +1.0 dB at 9 kHz | 434 -> 434 Hz | 11.2 -> 11.3 LU | -1.7 dBTP | not adopted |
| anthem | glue compressor -18 dB, 2:1, 20/250 ms | 623 -> 613 Hz | 8.6 -> 6.4 LU | -0.4 dBTP | not adopted |

None is adopted. The lofi shelf changes the centroid by only 12 Hz and slightly
reduces the loudness range; the cinematic and contemplative shelves move the
centroid by 1 Hz or less. The anthem compressor spends 2.2 LU of loudness range
and pushes the candidate peak to -0.4 dBTP, worse than the current -1.5 dBTP
master. The candidate WAVs remain under ignored `out/step8/ab/` for optional
human audition only.

**MuseScore_General.** The bank is not installed locally, so the A/B was not
performed. Keep GeneralUser GS v1.471 until a matched-loudness audition across
all five parts shows a clear improvement. Switching without that evidence would
change every timbre and invalidate the committed identity demos.

**Subjective listening.** The measurements above are objective. The final
judgment about pocket, blend, and musicality still needs ears on the rendered
previews; the checklist is in `docs/BEAUTY_REPORT.md`.

## Reproduction

```powershell
# Render one track per style through the fixed chain.
foreach ($style in @('cinematic','lofi','anthem','contemplative')) {
  python -m symphony.compose --profile profiles/small.json --style $style `
    --seed 1 --out "out/step5/fixed/small_$style"
}

# Measure integrated loudness, range and true peak.
ffmpeg -hide_banner -nostats -i out/step5/fixed/small_anthem.wav `
  -filter_complex ebur128=peak=true -f null -
```
