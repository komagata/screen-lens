# Local translation with image context — 2026-09-11

Research only. The installed plugin's cloud backend is unchanged. No live
desktop capture, external inference, API credentials or model installation was
required. Saved real-screen images and their reports remain private locally.

## Method

- Qwen3-VL-2B-Instruct Q4_K_M with its image projector, llama.cpp b10867.
- Hy-MT2-1.8B Q4_K_M for the optional second translation stage.
- Core i9-14900K, 64 GB RAM; CPU limited to four threads. GPU condition uses
  NVIDIA RTX 4060 8 GB via Vulkan. This is not a representative-laptop test.
- Eight authored 1000 × 420 fixtures: ambiguous Open/Save, negation, names,
  numbers, permission errors and an RPG instruction. Each baseline condition
  repeated twice, temperature 0, seed 42, prompt caching disabled.
- Input includes exact source text, coordinates and (where applicable) the PNG.
  Expected translations are never supplied to the models. This deliberately
  isolates translation/context quality from OCR errors.
- Compare Qwen text only, Qwen image plus text, and Qwen-generated visual
  explanation followed by Hy translation. The explanation is model-generated,
  not a manually supplied answer.
- Request wall times include local HTTP serialization and inference, but exclude
  model startup, OCR, capture, rendering and display. No result cache is used.
  The OS may already cache model files; startup is not disk-cold boot timing.

## CPU baseline

| Condition | Samples | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Qwen, text only | 16 | 1.175 s | 1.642 s | 2.478 s |
| Qwen, image plus text | 16 | 10.066 s | 10.951 s | 21.189 s |
| Qwen visual explanation → Hy, initial prompt | 16 | 11.902 s | 13.438 s | 22.235 s |

Process startup was 1.72 s for Qwen and 1.40 s for Hy. These were resident during
the benchmark. One image request per target is an intentionally simple baseline,
not a recommended whole-screen architecture. Images should be shared across a
batch of target strings.

### Semantic findings

No general accuracy percentage is claimed: these are eight agent-authored cases,
not an independent corpus or native-speaker evaluation. Substring checks in the
raw report are debugging aids, **not** a translation-quality score.

- The release/backup warning and retry delay retained negation and numbers.
- `Open` under `営業時間` became `営業時間\nOpen` with an image, not `営業中`.
- `Open` under `ファイルを選択` remained English with an image; text-only returned
  the expected `開く`.
- `Save` under `Annual plan: pay 20% less` became `保存する`, missing the discount
  meaning. The visual explanation incorrectly invented a settings-save button.
- Qwen removed the `@` from `@Adobe` in both text-only and image conditions.
- `Bring 3 herbs` became `3つの草を準備` with Qwen and `3種類のハーブ` with Hy:
  plausible Japanese, but quantity/action meaning changed.
- The initial Hy context prompt often translated the explanation itself. A
  follow-up uses the model card's exact **Structured Data 2** background template.
  This improves scope adherence in several cases but does not repair a wrong
  visual explanation. Even this template translated background information in
  the permission case.

The official-template follow-up reuses previously measured visual explanations.
Its `reconstructed_total_seconds` is a sum of separate measurements, **not** a
new end-to-end run. Translation-stage measurements must be reported separately.

## GPU and real-screen results

With the same image-token limit, Qwen image-plus-text requests had a **0.299 s
median** across 16 fixture requests. The first inference took **7.868 s**, while
subsequent requests took **0.235–0.384 s**. Model-process startup added **1.396 s**.
The initial inference overhead is real; it is excluded neither from the range
nor the report. Its internal cause was not isolated. These figures are not
whole-desktop translation times. New fixture images in the first pass were also
fast after the first request; this is not merely replay of identical results.

Semantic failures persisted: store Open, file Open, discount Save, the @Adobe
identifier and the RPG action. GPU speed did not solve interpretation errors.

The saved 1280 × 720 Wikipedia/terminal screenshot was supplied once per request
with **three selected OCR groups**, not all 78 screen groups. Two fresh-generation
requests took **3.033 s and 3.007 s**. The first request processed a new image, after
the fixture warmup. Both had `cache_n = 0`. Input processing took 0.422/0.412 s;
output generation took 2.549/2.558 s (404 tokens). The response unnecessarily
repeated coordinates and wrapped JSON in Markdown, so output-shape enforcement
offers a concrete optimization target.

The backup negation, `30`, and `12.5 MB` survived. However, `Type demo` became
`型をデモと入力` (wrong sense of Type and corrupted command), and `did not accept`
became `受信できませんでした` (acceptance shifted to reception). These are genuine
quality failures despite fast generation. This is not evidence of production
readiness or a successful full-screen display.

The successful GPU retry is `.size-check/visual-context-gpu-v2-20260911/report.json`.
Its Hy-only official-template rechecks took **0.491–2.075 s** (median 1.176 s), with
the earlier CPU visual descriptions reused. Do not label that hybrid as GPU-fast.

Qwen weights plus projector occupy **1,552,463,168 bytes (1.55 GB)**; adding Hy
brings model files alone to **2,685,543,616 bytes (2.69 GB)**. Runtime, RAM and GPU
memory are additional; peak RAM/VRAM have not been measured. This cannot meet a
100 MB all-inclusive local installation target.

### Increased image detail

The runtime warns that grounding tasks should use at least 1024 image tokens.
We therefore reran the GPU condition with `--image-min-tokens 1024` as well as
the existing maximum. The fixture prompt lengths increased from approximately
550 to 1200 tokens, confirming that the image-input budget actually changed.
Across 16 requests: minimum **0.517 s**, median **0.622 s**, maximum **0.771 s**.
The first request was 0.618 s in this later process; do not assume the earlier
7.9 s initial cost has permanently disappeared (system/driver caches were not
cleared). Three-region real-screen batches took **3.571 s and 3.391 s**.

This did **not** resolve Open/Save, command preservation or @Adobe failures.
The Wikipedia warning also changed into `誤解されがちです`, weakening the source
instruction not to confuse the terms. More image detail alone is not a fix.
Output: `.size-check/visual-context-gpu-1024-20260911/report.json`.

## Decision and next experiment

Local image-context inference is technically feasible and, with this discrete
GPU, fast enough to investigate further. **Do not replace the cloud backend
with this 2B model yet**: it is fast but not reliable on the tested ambiguities.
CPU-only visual interpretation is still expensive. A text-only translator's
sub-second timing cannot be presented as the speed of an image-aware pipeline.

The next justified comparison is a stronger image-capable model on the same
held-out tasks, using one image per batch and an enforced compact output schema.
Also compare visual *transcription* of nearby labels plus coordinates against
free-form visual explanations: the latter invented meanings here. Preserve
identifiers with deterministic validation and retain original text on failure;
these guards cannot by themselves detect subtle wrong meanings such as Save.

Before shipping, measure all screen regions with capture/OCR/render included,
perform more than two repeats on diverse unseen screenshots, test all chosen
language pairs with reviewers, measure peak RAM/VRAM and test a GPU-less laptop.
Cloud parity, laptop suitability, all-language accuracy and end-to-end desktop
latency remain unverified.

## Reproduction and artifacts

`benchmark_visual_context.py` verifies all three model SHA-256 hashes, then runs
the CPU baseline. `benchmark_visual_followup.py` uses those verified files for
the official-template retry, optional GPU fixture comparison and a saved real
Wikipedia/terminal screenshot with three OCR text groups batched in one request.
Pass explicit absolute input paths and a new `--output` directory; both scripts
show required arguments with `--help`. Neither downloads models automatically.
Servers are owned subprocesses, exposed only over private Unix sockets and
terminated in `finally` blocks. Keep real-screen reports out of Git.

Baseline local output: `.size-check/visual-context-cpu-20260911/report.json`.
The first follow-up `.size-check/visual-context-gpu-20260911` contains only Hy
results: the visual server failed to bind a reused Unix socket. It must not be
counted as a GPU benchmark. The retry uses a distinct socket for each server.

Qwen model SHA-256:
`089d75c52f4b7ffc56ba998ffc50aae89fcafc755f9e7208aacca281dca6c2ae`.
Projector SHA-256:
`f9a68fabba69c3b81e153367b2c7521030b0fa8bb0de400c9599c8e6725f9c82`.
Hy model details and its checksum are in [LOCAL-TRANSLATION.md](LOCAL-TRANSLATION.md).

## Sources

- [Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
- [Hy-MT2-1.8B and its background-information prompt](https://huggingface.co/tencent/Hy-MT2-1.8B)
- [TranslateGemma 4B](https://huggingface.co/google/translategemma-4b-it): a further
  candidate, not included in this new image benchmark. Its documented input
  template takes text **or** an image with source/target language codes; it is
  not a drop-in replacement for our general image-plus-selected-text request.
