# Compact Omarchy runtime (local candidate)

This bundle targets **Omarchy 4.0.2, x86-64, system Python 3.14**. It is a
locally verified build, not a published GitHub release. A clean installation
on a second PC has not yet been tested.

Run from the extracted bundle directory:

```sh
./screen-lens --lt --lt-fast
```

Use Esc or the same command to dismiss the snapshot. Existing desktop shortcuts
are not changed automatically. Do not launch this bundle with the old Python
3.12 virtual environment. No `pip`, `uv`, separate interpreter, or model download
is needed for its supported OCR profile. API key setup uses the
`komagata.screen-lens` Omarchy Shell panel and shared QML controls; see the
README for panel installation. No standalone GTK or Zenity dialog is used.
Requests, YAML and packaging
libraries are shared with Omarchy's standard packages.
OpenAI authentication and the existing cloud-translation privacy warning still
apply. Screen contents may be sent to OpenAI; do not test on confidential screens.

## Size scope

The local application directory, native libraries and three OCR model files
occupy approximately **85.6 MB** after OCR and rendering. No additional dialog
package is required. See `SHARED-PACKAGES.md` for smaller application bundles
which deliberately move more storage to system packages.
These are uncompressed installed sizes, not download sizes. Python, Quickshell,
GTK/Pango/Cairo, JPEG/FreeType/zlib and Noto CJK fonts are shared components
already required by the checked Omarchy base installation. Temporary screenshots
and the bounded translation cache are user data and are additional to the
installation; old virtual environments and build workspaces are not deleted.

## What is different

- Same v5 mobile detector / v6 small recognizer model weights as the LT default.
- CPU-only ONNX Runtime 1.29.0 built for those operators with LTO and unused
  tensor types disabled. It is not a general-purpose ONNX installation.
- Minimal OpenCV image-processing build; NumPy without BLAS; Pillow uses base
  system image/font libraries. No OpenCV GUI, CUDA or private Python interpreter.
- The four-corner area/perimeter calculation replaces RapidOCR's sole Shapely
  use. Patch and regression tests are retained in the source repository.
- Only the `v5-v6` OCR profile is supported. Other model profiles fail before
  loading/downloading models. Bytecode generation is disabled to avoid growth.

The native modules are tied to Python 3.14. After a system Python minor-version
upgrade, rebuild the bundle; the launcher reports a version mismatch instead of
silently mixing dependencies. This maintenance cost is the main tradeoff.

## Verification boundaries

The saved six-image OCR comparison includes light/dark/small text, a timeline
and two browser screenshots; recognized text and coordinates match the baseline.
Local app startup, offline demo recognition and Pango Japanese rendering were
tested without the old venv. This packaging work did not make paid API requests,
capture a new private desktop, or replace the currently installed shortcut.
See `RUNTIME-SIZE.md` in the source checkout for build experiments and timings.
