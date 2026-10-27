# Third-party notices

Symphony's Python source code is licensed under Apache-2.0 (see `LICENSE`).
The components below retain their own terms. License copies are distributed
where noted; upstream license files are linked for the native tools, which are
installed separately rather than included in this repository.

## GeneralUser GS v1.471

Created by S. Christian Collins. The package's included `LICENSE.txt` is kept
beside the SoundFont as `soundfonts/LICENSE-GeneralUser-GS.txt` when installed.
License v2.0 permits use for private or commercial music creation and software
projects, modification, and redistribution with its license and attribution.
The license also notes uncertainty about the provenance of some contained
samples. Read the accompanying license before redistributing the bank. The
installed bank is 31,281,186 bytes and is not committed; `tools/setup.py`
verifies the release archive SHA-256 before extracting it. See
`docs/MASTERING.md` for the installed hash and the soundfont evaluation.

## FluidSynth

FluidSynth 2.6.1, by Peter Hanappe and contributors. GNU Lesser General Public
License version 2.1 or later. The actual license is the `LICENSE` file in the
FluidSynth source distribution: <https://github.com/FluidSynth/fluidsynth/blob/v2.6.1/LICENSE>.
FluidSynth is installed separately and is not bundled by Symphony.

## FFmpeg

FFmpeg is installed separately and is not bundled by Symphony. The upstream
project states that the default configuration is LGPL v2.1 or later, with
optional GPL components that change the applicable terms when enabled. Consult
the `COPYING.LGPLv2.1`, `COPYING.GPLv2`, and other license files shipped with
the specific FFmpeg build you install. No FFmpeg executable or license files
were present in this checkout, so no particular build's configuration could be
inspected:
<https://ffmpeg.org/legal.html>.

## Python dependencies

The following license notices are transcribed from the actual license files in
the installed package distributions. The installed versions inspected were
pretty_midi 0.2.11.post0, tree-sitter 0.25.2, and tree-sitter-rust 0.23.3;
`requirements.txt` allows compatible versions within its declared ranges.

### pretty_midi — MIT

Copyright (c) 2014 Colin Raffel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### tree-sitter — MIT

Copyright (c) 2019 Max Brunsfeld, GitHub

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### tree-sitter-rust — MIT

Copyright (c) 2017 Maxim Sokolov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
