# Screen Lens

**Translate a snapshot of your Omarchy desktop into your language.**

Screen Lens is an experimental, one-shot screen translator for Omarchy / Hyprland.
It works from pixels, so it can translate content in browsers, terminals, chat apps,
and other applications without modifying them.

**Bar button or shortcut → translation indicator → translated snapshot → dismiss.**

The destination defaults to your locale (`LC_ALL`, then `LC_MESSAGES`, then `LANG`),
unless you have already saved a choice. C/POSIX and unsupported locales fall back
to English; Traditional Chinese is not silently mapped to Simplified Chinese.
The source defaults to English. Japanese, English, Simplified Chinese, Spanish and
French can be selected on either side of the bar panel. Input recognition remains primarily
tested on English screens; see the limitations below.

This is a demo prototype, not a finished accessibility tool or a replacement for
application localization. Only the focused monitor is captured, not all monitors.
The translation is a frozen image, not an interactive translated application.

## Add the Omarchy plugin

```sh
omarchy plugin add https://github.com/komagata/screen-lens --enable
```

This installs and enables the bar panel. **It does not install the OCR runtime or
system packages.** Complete the runtime setup below before translating. Plugin
loading never downloads models, installs packages, or changes shortcuts.
Open the bar's translation icon to choose **From / To**, configure **API key
settings**, and translate with GPT-5.6 Luna. An OpenAI API key and API billing are
required; local translation is not offered in the panel.

## Runtime requirements

- Omarchy with Hyprland and Quickshell (`hyprctl`, `qs`, and `grim`).
- Python **3.12** for the OCR virtual environment; `uv` is one way to obtain it.
- System Python with PyGObject, Cairo and Pillow for Japanese text rendering.
- Noto CJK fonts, ImageMagick, and internet access for initial OCR model downloads.
- For cloud translation: an OpenAI API key with access to `gpt-5.6-luna` and billing.
  A ChatGPT subscription alone is not API authentication.
- For experimental local translation: separately installed llama.cpp and about
  3.4 GB of model files. See [local setup](LOCAL-TRANSLATION.md). No API key is used.

CPU OCR is the portable default. Cloud translation does **not require a GPU**.
The current image-aware local model is recommended only for a compatible GPU;
CPU-only inference was too slow in our short-label test.
Developed with Qt 6.11.2 on Omarchy 4.0.2; other versions and a fresh laptop install
have not yet been verified. Do not assume the development PC's timings transfer.

## Install on another Omarchy PC

A local [compact runtime candidate](COMPACT-RUNTIME.md) uses Omarchy's system
Python and approximately 85.6 MB with standard Omarchy packages shared. It is
not yet published as a release. The source/venv installation below is the older,
larger route; it does **not** meet the 100 MB target.

Review the commands before running them. Nothing installs a compositor plugin,
changes system libraries, or automatically edits your keyboard bindings.

```bash
sudo pacman -S --needed git uv grim imagemagick noto-fonts-cjk python-gobject python-cairo libsecret
git clone https://github.com/komagata/screen-lens.git
cd screen-lens
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --no-deps -r requirements-slim.txt
.venv/bin/python check_slim_runtime.py
```

Confirm `qs --version` and `hyprctl version` work inside your desktop session.
Quickshell should already be available on the intended Omarchy installation.
If Python 3.12 is already installed, `python3.12 -m venv .venv` followed by
`.venv/bin/python -m pip install --no-deps --no-compile -r requirements-slim.txt`
is an alternative to the uv steps.

The slim runtime uses headless OpenCV: OCR does not need OpenCV's own GUI.
Use a fresh environment and the complete pinned dependency list above. Do not
install `requirements-ocr.txt` into it or install both OpenCV distributions.
RapidOCR's metadata names `opencv-python`, so ordinary `pip check` reports that
name as missing. `check_slim_runtime.py` validates dependencies with only this
explicit headless-provider substitution allowed, and checks that GUI support is
absent. See [runtime size measurements](RUNTIME-SIZE.md) for scope and tradeoffs.

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

Install the Omarchy Shell bar widget and API key panel. From a clean source checkout:

```sh
panel_dir="$HOME/.config/omarchy/plugins/komagata.screen-lens"
mkdir "$panel_dir"
cp manifest.json CredentialPanel.qml CredentialForm.qml credential_store.py "$panel_dir/"
cp plugin_launch.py translation_settings.py "$panel_dir/"
cp -r panel assets "$panel_dir/"
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/screen-lens" "$HOME/.local/bin/screen-lens"
omarchy plugin validate "$panel_dir"
omarchy-shell shell rescanPlugins
omarchy plugin enable komagata.screen-lens
```

The `mkdir` deliberately refuses to overwrite an existing installation. The
panels use Omarchy's shared `qs.Ui` controls and theme, not a separate GTK/Zenity
dialog. The translation runtime still needs the installation steps above. The
symlink command also refuses to replace an existing launcher; if using a compact
runtime, link its `screen-lens` executable instead. No desktop shortcuts are added
or replaced.

Click the translation icon in the bar, choose the source under **Translate from**
and the destination under **Translate to** (**日本語 / English / 简体中文 /
Español / Français**), then click **Translate screen**. Selecting the same language
on both sides disables the button. The popup fully unmaps
before capture starts. Esc or clicking outside dismisses the popup. The selected
pair is stored in the widget's inline `sourceLanguage` and `target` settings in Omarchy's
`shell.json`; the existing one-shot shortcut reads both too. `--source` and
`--target` accept `ja|en|zh-CN|es|fr` and override saved preferences for one invocation.
Cache entries are separated by both source and destination.

Source-script eligibility includes Japanese and Chinese rather than discarding
all CJK text. These options are not a claim of equal OCR quality: five authored
source-language samples passed local OCR eligibility checks, but English screens
have much broader testing. RTL and vertical text are not supported.
The panel uses **GPT-5.6 Luna** with image and nearby text context. There is no
engine selector. Local models remain a CLI-only experiment; see
[local setup and measured limits](LOCAL-TRANSLATION.md).

Click **API key settings** to register or replace
your OpenAI API key from the panel, without starting a translation. Input is
masked; **Save** stores it in the desktop keyring for subsequent launches.
The existing key is never shown in the panel. **Cancel** keeps it unchanged.
An `OPENAI_API_KEY` environment override takes precedence over the saved key.

For the one-shot desktop launcher, you can simply run
`.venv/bin/python lens.py --lt --lt-fast`. If no key is available, a masked input
dialog appears **before capture**. Save once to reuse it on subsequent launches.
Cancel exits without capturing or sending a screen. An existing environment key
or desktop keyring entry is used without showing this dialog.

New keys are saved through Secret Service (`secret-tool`) to your desktop
keyring, with attributes `application=screen-lens`, `service=openai`. This requires
a working persistent Secret Service provider such as GNOME Keyring. Screen Lens
does not create GPG identities, configure your keyring or fall back to a plaintext
file. If secure saving fails, translation does not start. Your keyring may ask
for an unlock password after login. Revoked, deleted or incorrect keys still need
replacement; saving does not validate API access or billing.

The panel passes the key to its fixed storage helper on stdin. Shell IPC carries
only a request ID and completion status, never the key. Closing or pressing Esc
cancels the dialog; a five-minute timeout also closes it. Cancellation during
storage stops the helper, but a key already committed to the keyring can remain.
There is no gopass dependency or fallback to a plaintext key file.

To remove the bar widget and setup panel: `omarchy plugin remove komagata.screen-lens`.
This keeps the translation runtime, `~/.local/bin/screen-lens` launcher symlink,
your existing shortcut, translation caches,
and the Screen Lens keyring entry. Delete the keyring entry separately using
your desktop keyring manager if you no longer want to retain the key.

Local translation research and reproducible CPU measurements are documented in
[LOCAL-TRANSLATION.md](LOCAL-TRANSLATION.md). Model weights are a separate,
optional download, not included in the compact application-size figure.

To replace a key, open **API key settings** in the bar panel and save the new key. Environment
variables take precedence over stored keys. CLI-only pipeline commands do not open
an input dialog; configure the key via the desktop launcher first.

The simplest option for a terminal rehearsal is a session environment variable.
This prompt does not echo the key or put it in shell history:

```bash
read -rsp 'OpenAI API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
.venv/bin/python lens.py --lt --lt-fast
unset OPENAI_API_KEY
```

The program uses `OPENAI_API_KEY` first, then the desktop keyring. For a desktop
shortcut, a variable exported only in a terminal is not inherited by Hyprland;
use the first-run dialog to save the key in the desktop keyring.
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

**`--lt --lt-fast --provider openai` sends screenshot-derived images and recognized text to OpenAI.**
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

- Source and destination each support Japanese, English, Simplified Chinese, Spanish and French; OCR and translation quality vary by language.
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
