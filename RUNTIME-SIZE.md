# Slim runtime measurements

Measured locally on Linux x86_64 with Python 3.12, 2026-09-11. Sizes are allocated
disk usage (`du -sk`), not download size. They exclude the shared Python
interpreter, system Qt/rendering libraries, package caches and screenshot caches.

| Runtime | Size |
| --- | ---: |
| Existing full OpenCV environment | 419.0 MiB |
| Headless environment before routine bytecode generation | 358.6 MiB |
| Installed headless environment after tests and benchmark | 365.2 MiB |

The installed reduction is 53.8 MiB (12.8%). The local rollback environment and
comparison environment were retained; this is a per-runtime saving, not a claim
that the development machine has recovered that much free disk space.

## What changed

`requirements-slim.txt` pins the complete tested dependency set and replaces
`opencv-python` with `opencv-python-headless` at the same 5.0.0.93 version.
The [headless package](https://pypi.org/project/opencv-python-headless/) omits GUI
dependencies; Screen Lens displays through Quickshell, not OpenCV windows.
RapidOCR 3.9.2, ONNX Runtime 1.29.0 CPU, and the existing OCR models are unchanged.
Installation deliberately uses `--no-deps` because RapidOCR declares the full
OpenCV package by name. Run `check_slim_runtime.py` after installation; do not
mix the two providers. This exception must be maintained when dependencies change.

## Local verification

Three synthetic screens cover light/dark backgrounds and small text, including
labels, sentences, a URL, a command and mixed Japanese/English. Across the old
and installed environments, all OCR text, boxes and confidence values were
identical. Pango rendering produced the same shown-region counts (9, 9, 8).
This checks equivalence, not that every original recognition was correct.

| OCR case (three runs, median) | Old | Installed slim |
| --- | ---: | ---: |
| Light | 0.487 s | 0.495 s |
| Dark | 0.459 s | 0.467 s |
| Small text | 0.437 s | 0.438 s |

First initialization was 0.518 s in the existing environment and 2.635 s in the
fresh installed environment; a repeated initialization in the comparison slim
environment was 0.838 s. This change is for size, not a demonstrated speedup.
No cloud translation, live desktop capture or fresh-machine install was tested
in this comparison. Synthetic rendering uses fixed Japanese text, not an LLM.

Reproduce locally (output directory must not exist):

```bash
.venv/bin/python check_slim_runtime.py
.venv/bin/python benchmark_runtime_size.py --output .size-check/my-run
du -sk .venv
```

The benchmark requires the system Noto CJK font and Pango rendering dependencies.
Images and detailed reports stay in the ignored `.size-check/` directory.

## Why not rewrite in Rust or C++ yet?

- [RapidOcrCpp](https://github.com/RapidAI/RapidOcrCpp) still depends on OpenCV
  and ONNX Runtime; changing the application language does not remove those.
- [ocrs](https://github.com/robertknight/ocrs) is a Rust OCR alternative, but
  switching engines/models needs a separate accuracy evaluation. No equivalent
  quality or smaller installed size has been measured here.
- [Reduced ONNX Runtime builds](https://onnxruntime.ai/docs/build/custom.html)
  can omit unnecessary operators, but require model-specific builds and ongoing
  binary maintenance. They are a possible next experiment, not an implemented
  or measured saving.

No container or bundled operating system is introduced. Further large reductions
need work on the OCR engine/runtime, not merely the virtual environment wrapper.

## Under-100-MB experiment: ocrs 0.13.0

Built with `cargo install ocrs-cli --locked` in the ignored comparison directory.
The CLI is 10,924 KiB; its downloaded detection and recognition models are
2,452 and 9,492 KiB respectively: 22.3 MiB total allocated. Dynamic dependencies
are the system C runtime, libm and libgcc, not OpenCV or ONNX Runtime. Build
artifacts are not runtime dependencies. This is OCR-only, not the complete app.

Five separate CLI invocations per existing synthetic image, including process
startup and model loading, gave medians of 0.214 s (light), 0.210 s (dark) and
0.197 s (small). Model downloads were excluded. These simple fixtures do not
establish full-desktop performance or translation quality.

English labels and long prose were mostly retained, but Japanese in the mixed
line was hallucinated as Latin characters in all three cases. Small text also
lost punctuation/spaces and changed `git status --short` to `git status-short`.
The candidate is therefore NOT enabled in the installed application. Another
issue is incorrect image dimensions in CLI JSON (1500 by 3 for a 1500 by 850
image); any adapter must obtain dimensions from the actual image.

The next gate is preserving mixed-language and identifier regions while keeping
the complete runtime below 100,000,000 bytes. Layout/font processing currently
also imports NumPy and sometimes OpenCV, so replacing OCR alone is insufficient.
Evaluate a smaller multilingual inference backend as well as this Latin-only
candidate before choosing a production migration.

## Same-model custom-build experiment

The isolated `.size-check/compact-env` uses NumPy 2.5.3 built with
`pip wheel --no-deps --no-binary=numpy -Csetup-args=-Dblas=none
-Csetup-args=-Dlapack=none -Ccompile-args=-j4 numpy==2.5.3`.
Its installed NumPy directory is 34,748 KiB, without a bundled BLAS library.

OpenCV 5.0.0 source commit `40738fb16ceddb5fb3fea747585f7ce6abb0605b`
was built in Release mode with static libraries and Python bindings, selecting
`core,imgproc,imgcodecs,python3,python_bindings_generator`. Required flann and
geometry modules were included automatically. IPP, OpenCL, ITT, GUI, video,
LAPACK and optional image codecs were disabled; PNG/JPEG/zlib were built in.
Python 3.12 headers and NumPy headers were supplied explicitly. CMake also needed
`PYTHON3_INCLUDE_PATH` explicitly to enable the Python target. The stripped
`cv2.cpython-312-x86_64-linux-gnu.so` is 22,408 KiB and links only standard
system C/C++ libraries. Full build settings remain in the local CMake cache.

The candidate omits `onnxruntime/capi/libonnxruntime.so.1.29.0` (27.2 MiB).
Both dynamic linkage and a live OCR process's loaded-library map confirm that
the Python binding does not use it. The excluded copy remains outside the
candidate for recovery; it is not a runtime dependency. The candidate still
uses the original Python ONNX binding and original v5/v6 OCR models.

After the benchmark, the candidate environment measured **176,828 KiB
(172.7 MiB)**. This is not under 100 MB, does not yet include application files
or an independently supplied Python interpreter, and is not installed as the
default runtime. No dependency has been moved elsewhere and retained through
a lookup path to claim a smaller candidate size.

All OCR text, coordinates and confidence values matched the existing baseline
exactly on the three synthetic cases. Medians were 0.474 / 0.478 / 0.437 s
(light/dark/small), initialization 0.799 s. Japanese rendering counts matched
and all 33 Python regression tests passed. Detailed local results are in
`.size-check/compact-build-test/report.json`. Real-screen and full-launch
verification remain outstanding. This supports pursuing the same-model route
before accepting the accuracy loss of a different OCR engine.

## Runtime-only packaging experiment

`runtime_bundle.py` copies dependencies into a new destination, preserving the
source and licenses while omitting dependency `tests`/`__pycache__` directories,
the unused v6 detector, and the unused standalone ONNX Runtime C library. It
keeps NumPy's `testing` module and RapidOCR's classifier model because imports
and initialization still need them. It is a packaging helper, not an installer.

Pillow 12.3.0 was built from source without TIFF, raqm, lcms, WebP, JPEG2000 or
AVIF. FreeType support is retained. `AR=/usr/bin/ar` is required with the local
bundled Python, whose default archiver points to a nonexistent build-host path.
The new Pillow uses system JPEG/zlib/FreeType and also auto-detected imagequant
and XCB. These shared dependencies must be audited against a clean Omarchy
installation before any final total-size claim; the experiment is not yet a
self-contained distribution.

After running the benchmark, `.size-check/runtime-only` was 142,184 KiB
(138.9 MiB), before additional symbol stripping. Running with `python -S` and
only this directory on `PYTHONPATH` avoids silently falling back to installed
site-packages. All 34 Python tests passed. On the saved original light/dark/small
images, OCR output hashes matched the baseline exactly; medians were
0.478 / 0.463 / 0.439 s. Regenerating fixtures with the newly linked FreeType
produces different source pixels, so regenerated fixture hashes are not used
to claim OCR equivalence.

Stripping non-runtime symbols from the candidate's `.so` files reduced it further
to **131,356 KiB (128.3 MiB; 134.5 MB)**. All 34 tests and all three saved-image
OCR hash comparisons passed again after stripping. Original packages and wheels
remain unchanged for rebuilding and diagnosis.

Rebuilding the same OpenCV source with `-Os -DNDEBUG -ffunction-sections
-fdata-sections` for C/C++, and `-Wl,--gc-sections` for the module linker, reduced
the stripped extension from 22,408 to 13,376 KiB. The runtime-only directory is
now **122,324 KiB (119.5 MiB; 125.3 MB)**. All three saved-image hashes still
match; OCR medians were 0.507 / 0.474 / 0.463 s. All 34 Python tests pass.
The previous extension remains in `.size-check/compact-excluded/cv2-O3.so`.

An ONNX Runtime 1.29.0 reduced-operator Python build is in progress, not yet
validated or installed. Source commit: `2e2543fbe9fae542f921d47a72d21d5a4ef0b710`.
The upstream `create_reduced_build_config.py` generated
`.size-check/ocr-operators.config` from all three required original models and
their locally optimized equivalents. Optimized copies are for operator discovery
only, not replacement distribution models. The build keeps Python bindings,
exceptions, graph optimization and needed contrib operators; it disables ML ops
and uses `--include_ops_by_config`, not the Python-incompatible minimal-build mode.

Build directory: `.size-check/ort-build`, configuration Release, Ninja, four
jobs, build wheel, skip tests and submodule sync. CMake options are
`onnxruntime_BUILD_UNIT_TESTS=OFF` and
`FETCHCONTENT_TRY_FIND_PACKAGE_MODE=NEVER`. The latter avoids accidentally mixing
system RE2/Abseil with the source-pinned dependencies. Test the resulting runtime
against original models before any size or compatibility claim. Build-time
dependencies are isolated in `.size-check/build-env` and are not shipped.

## Clean-Omarchy accounting audit

The installed Omarchy 4.0.2 base manifest is
`/usr/share/omarchy/install/omarchy-base.packages`. It already lists `grim`,
ImageMagick, libsecret, Noto CJK fonts, python-gobject, Quickshell, and
system-config-printer. The last package depends on python-cairo. python-gobject
depends on system Python, which is 3.14.7 on this host. Qt and grim also depend
on FreeType/JPEG/zlib through their normal dependency chains. These are base OS
components, not private Screen Lens dependencies moved outside a size total.

Python **3.12 is not that base interpreter**. The current experimental 3.12
packages cannot constitute the final under-100-MB distribution while excluding
their extra interpreter. Work is underway on 3.14 builds using the standard OS
Python, with all non-base Python modules still included in the app's budget.
Python-version updates will require corresponding native-extension rebuilds.

Zenity is not listed in the base manifest and its installed package is 5.03 MiB
on this host. Budget it as an additional dependency unless a verified alternative
eliminates it; do not silently omit it from the final total. Its GTK dependencies
also need comparison with the base installation. The Pango helper itself imports
GI and Cairo, not Pillow; Screen Lens still needs its private Pillow for image
processing and source-font matching.

The new 3.14 Pillow wheel disables auto-detected imagequant and XCB as well as
the previously omitted codecs. This avoids incidental dependencies from the
development PC. It preserves FreeType, JPEG and PNG support. Wheel build succeeded;
runtime and dynamic-dependency verification are still pending. It is kept under
`.size-check/wheels314`, not installed into the live app.

The 3.14 Pillow wheel has now passed PNG round-trip and Japanese FreeType font
loading checks. Its feature checks confirm imagequant and XCB are disabled.
The no-BLAS NumPy 3.14 wheel also built successfully. OpenCV 3.14 bindings are
being rebuilt against that NumPy; the active app remains on its original runtime.

## Saved real-screen check of the 125.3-MB candidate

Local-only comparison used the saved timeline screen and two saved browser
holdout screens under the original research tree. No image or recognized text
was sent to a cloud API. Each engine ran in its own process with `python -S`
and an explicit dependency path; neither used fallback site-packages.

| Screen | Regions (both) | Exact OCR rows | Baseline OCR | Candidate OCR |
| --- | ---: | --- | ---: | ---: |
| Timeline | 23 | Yes | 1.161 s | 1.221 s |
| Browser 1 | 36 | Yes | 1.145 s | 1.341 s |
| Browser 2 | 36 | Yes | 1.213 s | 1.078 s |

Exact includes text, coordinates and confidence. These are single OCR timings,
not repeated medians or end-to-end translation timings. Concurrent builds may
affect measurements. They validate the current candidate, not the unfinished
reduced-operator ONNX build. Repeat with that build before adopting it.

## Removing the general-purpose geometry runtime

RapidOCR 3.9.2 uses Shapely only to obtain the area and perimeter of the
four-corner box passed to `unclip`. `polygon_measure.py` implements just these
two measurements with ordinary double-precision arithmetic, not a general
Shapely substitute. Five unit tests cover direction, translation, rotation,
degeneracy, invalid inputs and reference rounding. Sequential addition is
intentional: Python's compensated `sum` changes the last bits of the perimeter.
10,000 deterministic random OpenCV boxes matched GEOS area/perimeter exactly.

The candidate `.size-check/runtime-no-geos` applies
`packaging/rapidocr-box-measures.patch` and copies `polygon_measure.py` into
`rapidocr/ch_ppocr_det/`. The original utils.py SHA-256 is
`01d25a0b1bbdcdd4aba70a23ae96714c5408df93b295c43ca194952e279adb9e`.
It omits Shapely and its GEOS libraries, preserving originals outside the
candidate. This is an explicit vendor patch that must be rechecked on a
RapidOCR upgrade; unmodified package metadata still declares Shapely and must
not be mistaken for a stock pip installation or a passing `pip check`.

All six saved images (three synthetic, timeline, two browser holdouts) produced
exactly matching OCR rows with no Shapely module loaded. Single-run OCR times
were 0.75/0.78/0.64/0.96/1.12/0.79 seconds in the candidate versus
0.73/0.67/0.69/0.93/1.04/0.95 seconds in the baseline, under concurrent build
load. All 39 Python tests passed. Before the additional OCR runs, allocated
runtime size was 112,344 KiB (115.0 MB); it remains above the final budget and
does not yet include a complete app installation or extra OS packages.

Python 3.14 OpenCV now builds and imports successfully, and a resize smoke test
passes. Full 3.14 integration and the reduced-operator ONNX build remain pending.

After OCR-generated bytecode, the no-GEOS candidate measures **115,020 KiB
(117.8 MB)**. Use this warmed size rather than the initial copy-only value.

The ONNX build hit GCC 16's `-Werror=maybe-uninitialized` in
`MatMulNBitsFusion::CreateSelectorActionRegistry()` called from the base-class
initializer. The helper uses no instance members. A local two-line source patch
makes its header declaration `static` and removes `const` from its definition.
That translation unit now compiles without disabling warnings, and the
incremental CMake build is continuing. This is another build patch to preserve
and review before distribution; the complete ONNX build is not yet proven.

The under-100-MB objective remains unfulfilled. Application files, any separately
required Python runtime and newly required OS libraries must still be included
in the final accounting, followed by real-screen validation.

## Standard Python 3.14 and reduced native runtime

The first reduced-operator ONNX Runtime build completed. Its stripped Python
3.12 extension is 21,780 KiB, and all three saved synthetic images produced
exactly the baseline OCR rows. The GCC 16 patch is preserved in
`packaging/ort-gcc16-static-registry.patch` (reverse dry-run verified).

The standard-Python candidate `.size-check/runtime314` uses the same OCR model
files and custom OpenCV/Pillow builds for Python 3.14. Its NumPy 2.5.3 build
disables BLAS/LAPACK and uses Meson's `buildtype=minsize`; installed native
extensions are stripped. With stock ONNX Runtime it measured 109,464 KiB.
No private Python interpreter is needed: the installed Omarchy base includes
`python-gobject` and `nautilus-python`.

`runtime_bundle.py` now also omits ONNX model-development directories
`transformers`, `quantization`, and `tools`, retaining inference code and
licenses. This exclusion was tested red/green. The resulting
`.size-check/runtime314-pruned` is 101,412 KiB (103.85 MB). All 40 Python tests
pass with `/usr/bin/python -B -S` and only this private package path. All six
saved images match baseline OCR rows exactly. Single-run baseline/candidate
OCR seconds were 2.308/1.725, 1.388/1.005, 0.631/0.586, 0.836/0.861,
1.100/1.538, 0.972/0.801 under concurrent build load; these are not fair final
speed benchmarks. `-B` avoids regenerating the excluded bytecode.

A second ONNX build targets Python 3.14 with the same reduced operator list,
`--disable_generation_ops`, `--disable_types float4 float8 optional sparsetensor
string`, `--no_telemetry`, and `--enable_lto`. Model weights remain unchanged.
It is still linking; do not use the partial extension until the build exits 0.

Zenity adds 5.03 MiB and must be counted unless already installed independently.
Its GTK4/libadwaita dependencies are already required by base Omarchy's Nautilus
(verified from the installed package metadata and base package manifest).
The native candidate links to standard libc/C++/math and, for Pillow, JPEG,
FreeType and zlib libraries, rather than bundled copies. No OS packages were
installed or removed in this experiment.

The snapshot cache now includes `runtime-manifest.json`, when present, so a
future packaged native-runtime upgrade can invalidate cached translations.
Its new regression test failed before implementation and now passes.
The experimental runtime is not yet integrated into the installed launcher;
the existing `.venv` and desktop shortcut are preserved.

## Completed local compact bundle

The Python 3.14 LTO build exited successfully. The stripped extension SHA-256 is
`a71ad3358bd3728d82d4999d922109eaf441b3c05588de19839d96fcdc2ec59e`.
The reduced private runtime occupies 86,468 KiB. All six saved OCR fixtures
matched baseline rows on three repeated runs each. Median OCR seconds:

| Fixture | Existing runtime | Compact runtime |
| --- | ---: | ---: |
| Light | 0.473 | 0.488 |
| Dark | 0.476 | 0.460 |
| Small | 0.526 | 0.448 |
| Timeline | 0.696 | 0.705 |
| Browser 1 | 0.695 | 0.685 |
| Browser 2 | 0.578 | 0.593 |

These are OCR-only timings with loaded engines, not cloud translation or
shortcut-to-display measurements. The original model weights are unchanged.

The complete local bundle is `outputs/screen-lens-compact-20260911` relative
to the workspace root, outside this repository. It contains app sources,
QML/assets, a `screen-lens` launcher, manifest and private runtime, but no old
venv, build tools or screenshots. After startup/OCR, it occupies 86,920 KiB
(89,006,080 bytes). Zenity's installed package size is 5,271,231 bytes, giving
94,277,311 bytes including that additional dependency, below 100,000,000 bytes.
No compressed-size substitution is used. Existing Omarchy base components and
temporary user data are distinguished in `COMPACT-RUNTIME.md`.

Integration initially exposed a legacy `make_rapid()` default that selected
v5 recognition and downloaded an extra model. The compact bundle now selects
its manifest profile by default and rejects unsupported profiles before model
initialization. A regression test was added first. The downloaded test model
was moved out of the bundle into the retained experimental backups. Ordinary
source checkouts preserve their previous defaults.

The packaged launcher now uses system Python and activates private dependencies
for itself and workers. A Python ABI mismatch fails explicitly. Offline demo
preparation produced three translated regions, and Pango rendered nine of ten
synthetic regions (the URL was preserved). The Japanese rendering PNG was
visually inspected. All 44 Python tests pass; no bytecode directories appeared.
No paid translation request, new desktop capture, second-machine installation,
commit, push or live-shortcut replacement was performed. This completes the
local size/quality/speed goal, not publication or rollout to another PC.
