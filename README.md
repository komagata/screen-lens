# Screen Lens

**Take a snapshot of your Omarchy desktop and read its English text in Japanese.**

Screen Lens is an experimental, one-shot screen translator for Omarchy / Hyprland.
It works from pixels, so it can translate content in browsers, terminals, chat apps,
and other applications without modifying them.

**Shortcut → translation indicator → Japanese snapshot → dismiss to return to work.**

This is a demo prototype, not a finished accessibility tool or a replacement for
application localization. Only the focused monitor is captured, not all monitors.
The translation is a frozen image, not an interactive translated application.

## Requirements

- Omarchy with Hyprland and Quickshell (`hyprctl`, `qs`, and `grim`).
- Python **3.12** for the OCR virtual environment; `uv` is one way to obtain it.
- System Python with PyGObject, Cairo and Pillow for Japanese text rendering.
- Noto CJK fonts, ImageMagick, and internet access for initial OCR model downloads.
- For real translation: an OpenAI API key with access to `gpt-5.6-luna` and billing.
  A ChatGPT subscription alone is not API authentication.

CPU OCR is the portable default. An NVIDIA GPU is **not required**.
Developed with Qt 6.11.2 on Omarchy 4.0.2; other versions and a fresh laptop install
have not yet been verified. Do not assume the development PC's timings transfer.

## Install on another Omarchy PC

Review the commands before running them. Nothing installs a compositor plugin,
changes system libraries, or automatically edits your keyboard bindings.

```bash
sudo pacman -S --needed git uv grim imagemagick noto-fonts-cjk python-gobject python-cairo python-pillow
git clone https://github.com/komagata/screen-lens.git
cd screen-lens
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-ocr.txt
```

Confirm `qs --version` and `hyprctl version` work inside your desktop session.
Quickshell should already be available on the intended Omarchy installation.
If Python 3.12 is already installed, `python3.12 -m venv .venv` followed by
`.venv/bin/pip install -r requirements-ocr.txt` is an alternative to the uv steps.

### 1. Try the display without an API key

```bash
.venv/bin/python lens.py --demo --ocr tesseract
```

This shows a **synthetic screen with fixed translations**, not a real AI result.
It requires Tesseract (`sudo pacman -S --needed tesseract tesseract-data-eng`).
Press Esc to return. This is a useful rehearsal for startup and dismissal only.

### 2. Warm up local OCR

```bash
.venv/bin/python -c 'from ocr_backends import make_rapid, DEFAULT_UI_PROFILE; make_rapid(DEFAULT_UI_PROFILE)'
```

Initial model downloads can take time. Run this before the talk while online.
Do not copy a virtual environment or the development machine's model paths.

### 3. Configure API authentication

The simplest option for a terminal rehearsal is a session environment variable.
This prompt does not echo the key or put it in shell history:

```bash
read -rsp 'OpenAI API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
.venv/bin/python lens.py --lt --lt-fast
unset OPENAI_API_KEY
```

Alternatively, if you already use `gopass`, save the key at
`personal/openai/api-key` with `gopass insert personal/openai/api-key`.
The program uses `OPENAI_API_KEY` first, then this gopass item. For a desktop
shortcut, a variable exported only in a terminal is not inherited by Hyprland;
use an accessible gopass item or your existing secure desktop secret launcher.
Check that authentication works without an unexpected password prompt before LT.
Never put an API key in a Git repository, shortcut command, or bug report.

## Controls

| Action | Result |
| --- | --- |
| Run `lens.py --lt --lt-fast` | Capture once and translate |
| Run the same command again | Close the current snapshot |
| Esc | Close |
| Space | Compare the captured original and translation |
| Round translation icon | Close / cancel; rotates while processing, red background on failure |
| Click, mouse wheel, navigation or typing key | Dismiss; the first action is consumed, not replayed into the underlying app |
| Window/workspace change notification | Request dismissal |

Default safety timeout: 120 seconds (`--timeout SECONDS` to change it).
Wheel dismissal and desktop-event handling have automated component tests;
their full behavior on another actual desktop still needs rehearsal.
Video frames and automatic page updates are **not** detected. Dismiss before
interacting with an app. Switching to the original shows the captured original,
not a live view of the desktop.

## Optional shortcut

First test from a terminal. Then bind an **unused** key combination in your own
Omarchy keyboard configuration to this command, using the absolute clone path:

```text
/ABSOLUTE/PATH/screen-lens/.venv/bin/python /ABSOLUTE/PATH/screen-lens/lens.py --lt --lt-fast
```

Use Omarchy's normal shortcut configuration for your installed version (Lua and
older Hyprland configuration formats differ). Screen Lens does not reserve a key.
Inspect existing bindings with `hyprctl binds -j` before choosing one. Invoking
the same binding closes an existing snapshot rather than starting another one.

## Privacy and cost — read before using

**`--lt --lt-fast` sends screenshot-derived images and recognized text to OpenAI.**
This can include messages, documents, passwords, access tokens and personal data.
There is no reliable automatic secret-redaction feature. Use only a prepared,
non-sensitive desktop for a public demo. API usage costs money.

Requests specify `store: false`; this is not a promise of zero provider retention.
Runtime screenshots and results live in a private temporary directory under
`XDG_RUNTIME_DIR` and are removed on normal exit. Abrupt termination may leave
files until cleanup/logout. Do not publish those directories. Manual use of
`static_pipeline.py --output ...` retains outputs at your chosen location.

Up to eight successful LT translations are cached in
`$XDG_RUNTIME_DIR/screen-lens-snapshot-cache/` (directory 0700, archives 0600).
These archives contain translated screenshots and can contain private content.
Entries expire after 15 minutes and are removed on the next cache access; the
cache is not intended to survive logout. Returning to a previously translated
screen can reuse its result even after translating another screen.
Only exact full-resolution pixel matches with matching fast-mode and runtime
source-code fingerprints reuse a result. Tests and documentation do not affect
the fingerprint. OCR and API requests are skipped on a hit. Small changes such
as a clock still cause a miss. Capturing and displaying still take time.
Failed translations are not cached; corrupt matching entries are regenerated.
The overlay status says `キャッシュから表示` on a hit. `last-access.json` in that
folder records only the last hit/miss, reason and time, without screen content.

This repository contains source and synthetic fixtures only—no real desktop
screenshots, API credentials, model weights, virtual environments, or personal logs.

## Rehearse before the lightning talk

1. Install dependencies, download OCR models, and check API access on the laptop.
2. Open a prepared English web page or terminal with no sensitive information.
3. Run the real command at least three times; measure from launch to visible result.
4. Test Esc, the same shortcut, wheel dismissal, and timeout recovery.
5. Test the projector's resolution/scaling and the exact recording setup.

There is **no 5–10 second guarantee**. CPU speed, screen resolution, text density,
network and API latency matter. Initial startup/download is slower. The LT profile
reduces large images to at most 2560 pixels on the longest side for processing,
which can miss small text. Translation has a 60-second processing deadline.

If it gets stuck, try Esc or run the same command again. To request closure directly:

```bash
qs ipc -p "$PWD" call lens close
```

Run that from the clone directory. Do not kill every Quickshell process: Omarchy
may use other Quickshell processes for its own UI. The safety timeout also closes
the snapshot. If authentication or rendering fails, inspect the terminal error
without posting private screenshot data.

## Scope and limitations

- English → Japanese is currently the target, not arbitrary language selection.
- OCR and translation can misread text, miss regions, alter meaning or produce
  small text. Confirm important numbers, negation, commands and URLs in the source.
- Uneven backgrounds and dense layouts remain difficult.
- `--live` and related options remain experimental and **are not recommended for
  the demo**: their hide/capture/restore cycle can flicker. Use the one-shot command.
- The compositor capture experiment is deliberately not distributed or installed.
- Local Ollama support exists in the older text-only path; it is not a validated
  drop-in replacement for the image-context LT pipeline.

## Development and tests

```bash
.venv/bin/python -m unittest test_lens test_lt_input test_packaged_layout test_snapshot_cache
QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qmltestrunner -input qml-tests
```

`qmltestrunner` comes from Qt's development/test tooling. These tests do not call
the translation API or certify end-to-end laptop behavior. Tests were written
before the new dismissal behavior; physical desktop verification remains separate.
The publication copy passed 12 Python tests, 23 QML test cases, CLI help startup,
and CPU OCR initialization in a newly created Python 3.12 environment on the
development machine. This is not a fresh-OS or projector test.

Architecture: `lens.py` captures and coordinates; `static_pipeline.py` performs
OCR, context-aware translation and layout; `snapshot.py` / `pango_patch.py` render
Japanese; `shell.qml` displays the snapshot with Quickshell.

The translation icon is Lucide's `languages`, distributed under the ISC license.
See `assets/LICENSE-lucide.txt`; its stroke color is adapted for a dark background.

Bug reports are welcome. Include versions, resolution, scaling, timings and a
synthetic reproduction. Please do not attach private screen captures or keys.

### Local source-size matching

The LT launcher now uses `--match-source-font-size`: Japanese text is sized
from the median visible glyph height measured in the original OCR lines in each
region, before display space expansion. Uniform light and dark backgrounds are
supported; uncertain backgrounds fall back to OCR line height. Small labels and
large headings therefore receive different font sizes even with padded OCR boxes. This replaces the fixed 18px ceiling in LT mode. The renderer
uses compact Japanese line spacing and prefers the largest fitting size in the
available space. Source-sized regions can use up to 640px of blank space on the
right and up to three font heights vertically (capped at 256px), bounded by
background changes and neighboring OCR regions. It can shrink by about 25% only when necessary; if the translation still cannot fit inside the safe
available space, it leaves the original region visible. OCR line height is an
estimate of visible text size, not the application's exact font metric.

Run the local regression coverage with `.venv/bin/python -m unittest test_source_font`.
