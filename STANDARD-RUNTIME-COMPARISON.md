# Omarchy standard-component OCR comparison

Local experiment, 2026-09-11. The installed compact runtime and shortcuts were
not changed. No screenshot was captured or sent to a cloud service in this test.

## Candidates and measurement

- Current compact RapidOCR, unchanged v5/v6 models; one loaded engine.
- Omarchy's Tesseract 5.5.3, English data, sparse-text mode (PSM 11).
- Same with ImageMagick 2x scaling, including scaling time.
- Tesseract automatic-page mode (PSM 3).

Each image/mode was measured three times; tables show median local OCR seconds.
Tesseract time includes process startup; RapidOCR uses a loaded engine. These
are not end-to-end translation timings or a cold-start comparison. OpenMP was
limited to four threads for Tesseract, matching the RapidOCR thread setting.

The first six fixtures are **synthetic**, including the timeline and the two
browser-rendered layout samples. They must not be described as real X feeds or
real application content. Two separately saved desktop preflight screenshots
were subsequently tested without publishing their contents.

| Synthetic fixture | RapidOCR | Tesseract 11 | Tesseract 11, 2x | Tesseract 3 |
| --- | ---: | ---: | ---: | ---: |
| Light | 0.480 | 0.414 | 0.714 | 0.391 |
| Dark | 0.465 | 0.554 | 1.002 | 0.538 |
| Small text | 0.444 | 0.298 | 0.583 | 0.302 |
| Timeline | 0.602 | 0.985 | 1.449 | 0.865 |
| Browser layout 1 | 0.682 | 0.801 | 1.650 | 0.695 |
| Browser layout 2 | 0.585 | 0.602 | 1.254 | 0.509 |

| Saved desktop | RapidOCR | Tesseract 11 | Tesseract 11, 2x | Tesseract 3 |
| --- | ---: | ---: | ---: | ---: |
| Desktop 1 | 2.732 | 1.385 | 6.150 | 1.462 |
| Desktop 2 | 4.464 | 3.576 | 9.744 | 3.504 |

These two desktop runs confirm a speed benefit in some real layouts. They do
not establish equal recognition quality: neither desktop has a fully reviewed
ground-truth transcription in this experiment.

For light/dark/small fixtures, normalized whole-text character error rates were
0.34%/0.67%/0.67% for RapidOCR and 1.34%/2.35%/2.68% for Tesseract 11.
Normalization applies NFKC and collapses whitespace, without lowercasing.
The known reference includes one mixed English/Japanese line, so these are
**not English-only accuracy scores**. No confidence filtering was applied.

The small-text fixture demonstrates a safety-relevant error: `git status --short`
becomes `gitstatus —short` in Tesseract 11, and `gitstatus--short` even with 2x
scaling. English-only data also converts Japanese glyphs into unrelated text.
The browser layout samples show fragmented/misrecognized small text. Region
counts alone are not accuracy measurements, because engines group differently.

## Size implications

Omarchy's installed base manifest includes Tesseract + English data,
ImageMagick, Quickshell, Python GObject and Noto CJK fonts. These can be shared.
The current compact runtime already shares the interpreter and rendering stack.

The private RapidOCR and ONNX Runtime directories occupy 42,827,776 allocated
bytes combined. Removing them could bring the approximately 94.3 MB installation
to approximately **51.4 MB**, before adapter changes and any other removals.
This is a dependency-subtraction estimate, **not a built, working 51 MB app**.
The LT pipeline still constructs RapidOCR and would need a Tesseract adapter.

NumPy is also used for font sizing, contrast and whitespace allocation. OpenCV
is used for horizontal separator detection. They cannot simply be deleted after
switching OCR. Stock system packages on this host are larger: NumPy 49.24 MiB,
OpenCV 112.81 MiB and Python OpenCV 11.33 MiB, excluding additional dependencies.
They are not guaranteed by the checked base manifest; moving dependencies to
pacman would not establish a smaller total clean-install footprint.

## Decision

Keep RapidOCR as the installed default. Tesseract is a plausible optional
small-footprint mode, but it is not a quality-preserving replacement based on
these tests. Before shipping such a mode, implement the LT adapter, test mixed
language preservation and code/URL safeguards, evaluate real-desktop regions
against human-reviewed references, and measure an actual complete installation.
Replacing the remaining image-analysis code with Qt/ImageMagick would be a
separate rewrite, not a free packaging change.

Local private results are under `.size-check/system-ocr-comparison/report.json`
and `.size-check/system-ocr-real-comparison/report.json`. The experimental runner
is `.size-check/compare_system_ocr.py`; it records only aggregate timing/error
statistics to stdout and keeps recognized text in the local reports. These
artifacts are ignored by Git and must not be published as screenshot datasets.
