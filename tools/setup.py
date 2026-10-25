"""Download the project SoundFont and print native-tool setup guidance."""

from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOUNDFONTS = ROOT / "soundfonts"
ARCHIVE = SOUNDFONTS / "GeneralUser_GS_1.471.zip"
SOUNDFONT = SOUNDFONTS / "GeneralUser-GS.sf2"
LICENSE = SOUNDFONTS / "LICENSE-GeneralUser-GS.txt"
URL = "https://www.dropbox.com/s/4x27l49kxcwamp5/GeneralUser_GS_1.471.zip?dl=1"
ARCHIVE_SHA256 = "4203835164766f428c4926c097c9ea58dae431c7fb8f9dbe277b92d80da45ec2"


def install_soundfont() -> None:
    SOUNDFONTS.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists():
        print(f"Downloading GeneralUser GS v1.471 from the author's release: {URL}")
        urllib.request.urlretrieve(URL, ARCHIVE)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest.lower() != ARCHIVE_SHA256:
        ARCHIVE.unlink(missing_ok=True)
        raise SystemExit(f"SoundFont archive checksum mismatch: {digest}")
    with zipfile.ZipFile(ARCHIVE) as package:
        sf2_members = [name for name in package.namelist() if name.lower().endswith(".sf2")]
        license_members = [
            name for name in package.namelist()
            if Path(name).name.lower() in {"license.txt", "license"}
        ]
        if not sf2_members or not license_members:
            raise SystemExit("The verified archive does not contain both an SF2 and its license.")
        SOUNDFONT.write_bytes(package.read(sf2_members[0]))
        LICENSE.write_bytes(package.read(license_members[0]))
    if SOUNDFONT.stat().st_size < 1_000_000:
        SOUNDFONT.unlink(missing_ok=True)
        raise SystemExit("Downloaded SoundFont is unexpectedly small.")
    ARCHIVE.unlink(missing_ok=True)
    print(f"Installed {SOUNDFONT} ({SOUNDFONT.stat().st_size:,} bytes)")
    print(f"License copied to {LICENSE}")


def print_native_install_help() -> None:
    system = platform.system()
    print("\nNative renderer dependencies (FluidSynth CLI and ffmpeg):")
    print("  Windows: install FluidSynth (https://github.com/FluidSynth/fluidsynth/releases) and ffmpeg (https://ffmpeg.org/download.html).")
    print("           Extract FluidSynth under tools/fluidsynth/ or add it to PATH.")
    print("  macOS:   brew install fluidsynth ffmpeg")
    print("  Ubuntu:  sudo apt install fluidsynth ffmpeg")
    print("  Fedora:  sudo dnf install fluidsynth ffmpeg")
    if system == "Windows":
        print("\nWindows executable lookup checks tools/fluidsynth/ before PATH.")
    else:
        print(f"\nDetected platform: {system or sys.platform}")
    if not shutil.which("ffmpeg"):
        print("ffmpeg is not currently available on PATH.")
    if not shutil.which("fluidsynth"):
        print("FluidSynth is not currently available on PATH (a local tools/ copy also works).")


if __name__ == "__main__":
    install_soundfont()
    print_native_install_help()
