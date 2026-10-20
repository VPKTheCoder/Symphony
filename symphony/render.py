"""FluidSynth and ffmpeg rendering with light mastering polish."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pretty_midi

from symphony.styles import Style

REPO_ROOT = Path(__file__).resolve().parents[1]


class RenderError(RuntimeError):
    """Raised when an external renderer is missing or fails."""


@dataclass(frozen=True)
class RenderResult:
    wav_path: Path
    mp3_path: Path
    stem_paths: tuple[Path, ...] = ()


def render_track(
    midi_path: str | Path,
    wav_path: str | Path,
    mp3_path: str | Path,
    *,
    style: Style,
    soundfont: str | Path | None = None,
    fluidsynth: str | Path | None = None,
    stems: bool = False,
) -> RenderResult:
    midi = Path(midi_path)
    wav = Path(wav_path)
    mp3 = Path(mp3_path)
    wav.parent.mkdir(parents=True, exist_ok=True)
    mp3.parent.mkdir(parents=True, exist_ok=True)

    sf2 = _find_soundfont(soundfont)
    synth = _find_fluidsynth(fluidsynth)
    ffmpeg = _find_ffmpeg()
    midi_end = pretty_midi.PrettyMIDI(str(midi)).get_end_time()

    handle, raw_name = tempfile.mkstemp(
        prefix=".symphony-", suffix=".wav", dir=wav.parent
    )
    os.close(handle)
    raw = Path(raw_name)
    raw.unlink(missing_ok=True)

    synth_command = [
        str(synth),
        "-n",
        "-i",
        "-q",
        "-F",
        str(raw),
        "-r",
        "44100",
        "-L",
        "2",
        "-g",
        "0.85",
        "-o",
        "synth.reverb.active=1",
        "-o",
        f"synth.reverb.room-size={style.reverb_room:.3f}",
        "-o",
        f"synth.reverb.damp={style.reverb_damping:.3f}",
        "-o",
        "synth.reverb.width=0.82",
        "-o",
        f"synth.reverb.level={style.reverb_level:.3f}",
        "-o",
        "synth.chorus.active=0",
        "-o",
        "synth.polyphony=256",
        str(sf2),
        str(midi),
    ]
    _run(synth_command, "FluidSynth")

    normalize_filter = (
        f"loudnorm=I={style.target_lufs:.1f}:TP=-1.5:LRA=11,"
        "areverse,afade=t=in:st=0:d=1.2,areverse,"
        "alimiter=limit=0.95"
    )
    wav_command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        f"{midi_end + 3.0:.3f}",
        "-i",
        str(raw),
        "-af",
        normalize_filter,
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_s24le",
        str(wav),
    ]
    _run(wav_command, "ffmpeg (WAV mastering)")

    mp3_command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(mp3),
    ]
    _run(mp3_command, "ffmpeg (MP3 encode)")

    raw.unlink(missing_ok=True)
    stem_paths: list[Path] = []
    if stems:
        source = pretty_midi.PrettyMIDI(str(midi))
        for index, track in enumerate(source.instruments):
            stem_midi = pretty_midi.PrettyMIDI(initial_tempo=source.estimate_tempo())
            stem_midi.time_signature_changes = list(source.time_signature_changes)
            stem_midi.instruments.append(track)
            stem_midi_path = wav.with_name(f"{wav.stem}_{_safe_stem_name(track.name, index)}.mid")
            stem_wav = wav.with_name(f"{wav.stem}_{_safe_stem_name(track.name, index)}.wav")
            stem_mp3 = stem_wav.with_suffix(".mp3")
            stem_midi.write(str(stem_midi_path))
            render_track(
                stem_midi_path, stem_wav, stem_mp3, style=style,
                soundfont=sf2, fluidsynth=synth, stems=False,
            )
            stem_midi_path.unlink(missing_ok=True)
            stem_mp3.unlink(missing_ok=True)
            stem_paths.append(stem_wav)
    return RenderResult(wav_path=wav, mp3_path=mp3, stem_paths=tuple(stem_paths))


def _safe_stem_name(name: str, index: int) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in name)
    slug = "_".join(part for part in slug.split("_") if part)
    return slug or f"instrument_{index + 1}"


def _find_soundfont(explicit: str | Path | None) -> Path:
    environment = os.environ.get("SYMPHONY_SOUNDFONT")
    candidates = [
        Path(explicit) if explicit else None,
        Path(environment) if environment else None,
        REPO_ROOT / "soundfonts" / "GeneralUser-GS.sf2",
        REPO_ROOT / "soundfonts" / "GeneralUser GS v1.471.sf2",
    ]
    candidates.extend(sorted((REPO_ROOT / "soundfonts").glob("*.sf2")))
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    raise RenderError(
        "No .sf2 SoundFont found. Put GeneralUser-GS.sf2 in soundfonts/ or set "
        "SYMPHONY_SOUNDFONT."
    )


def _find_fluidsynth(explicit: str | Path | None) -> str:
    environment = os.environ.get("SYMPHONY_FLUIDSYNTH")
    candidates = [
        str(explicit) if explicit else None,
        environment,
        shutil.which("fluidsynth"),
    ]
    local = sorted(
        (REPO_ROOT / "tools" / "fluidsynth").glob("**/bin/fluidsynth.exe")
    )
    candidates.extend(str(path) for path in local)
    candidates.extend(
        filter(
            None,
            [
                shutil.which("fluidsynth"),
                r"C:\Program Files\FluidSynth\bin\fluidsynth.exe",
            ],
        )
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    raise RenderError(
        "FluidSynth CLI not found. Place it under tools/fluidsynth/ or set "
        "SYMPHONY_FLUIDSYNTH."
    )


def _find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("ffmpeg not found on PATH.")
    return ffmpeg


def _run(command: list[str], label: str) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RenderError(f"{label} failed ({completed.returncode}): {detail}")
