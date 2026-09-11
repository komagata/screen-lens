# Local translation experiment — 2026-09-11

The outstanding method comparison is recorded in
[LOCAL-METHOD-COMPARISON.md](LOCAL-METHOD-COMPARISON.md). All methods in that
bounded comparison have been tried; no candidate has replaced the installed backend.

## Current integration: experimental image-aware backend

The panel now has an explicit Local/Cloud selector. Cloud remains the default.
Local uses **Qwen3.5-4B Q4_K_M + F16 vision projector** via an owned llama.cpp
process, private Unix socket, offline mode, and no API key or cloud fallback.
Each bounded batch includes a screen image, source strings, coordinates, and
nearby OCR text. JSON IDs are constrained; malformed output, changed numbers,
URLs, mentions, quoted code and recognized command tokens retain their source.
These checks cannot detect every semantic error. The server exits after the
request and is killed if its parent worker is killed during cancellation.

Weights are separate from the compact app: **3,413,361,504 bytes**, plus llama.cpp
and working memory. The <100 MB app goal does not include local models.

Obtain a trusted llama.cpp build supporting Qwen3.5 vision (tested b10867) and
these pinned files from
[unsloth/Qwen3.5-4B-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/tree/e87f176479d0855a907a41277aca2f8ee7a09523):

- `Qwen3.5-4B-Q4_K_M.gguf`, SHA-256 `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4`
- `mmproj-F16.gguf`, SHA-256 `cd88edcf8d031894960bb0c9c5b9b7e1fea6ebee02b9f7ce925a00d12891f864`

Create `~/.config/screen-lens/local-model.json` (directory mode 700, file mode 600):

```json
{
  "model_id": "qwen3.5-4b",
  "server": "/absolute/path/to/llama-server",
  "model": "/absolute/path/to/Qwen3.5-4B-Q4_K_M.gguf",
  "projector": "/absolute/path/to/mmproj-F16.gguf",
  "device": "none"
}
```

Use `none` for CPU or `Vulkan0` for a compatible GPU. Files are verified before
inference. There is no automatic download, package installation, or listening
TCP port. Choose Local in the panel, or run `screen-lens --lt --lt-fast --provider local`.

On this RTX 4060 desktop, eight authored cases repeated twice distinguished shop
Open (`営業中`) from file Open (`開く`), preserved a backup prohibition and the
quoted demo command. An @mention was corrupted and rejected. This is a small
development test, not general translation-quality certification.
A saved 4K Wikipedia/terminal screen (resized to 2560px) took **46.57 seconds**
through OCR/translation/render, including **2.93 s OCR / 41.89 s translation**;
61 of 74 detected target regions were displayed. This is not live shortcut latency.
Unquoted command corruption was found in this run and the guard was subsequently
extended to retain that source. Dense screens and CPU-only machines remain slow;
do not present local mode as faster than cloud or as cloud-quality parity.
A fresh non-cache repeat after the command guard took **47.23 s** and displayed
60/74 regions; the unquoted `demo` instruction was correctly retained unchanged.
The four-thread CPU-only image-context probe did not finish even one short-label
request within its 45-second timeout (startup was 2.29 s). CPU-only suitability
is not established; a compatible GPU is recommended for this experimental model.

Reproduce the inference-only comparison with `benchmark_local_candidates.py`.
Reports and screen images remain local and private; do not commit `.size-check`.

## Split-model experiment: image context once, specialized translation

`benchmark_split_translation.py` replays the same saved OCR report (74 regions).
Qwen3.5-4B summarizes visible screen regions once, then unloads; Hy-MT2-1.8B
translates ten batches of up to eight strings using that background and preserved
JSON IDs. Both stages use the GPU in the first comparison. No result cache is
used. Model startup is included, but initial checksum verification, OCR, capture,
rendering and display are excluded. This is not shortcut-to-display latency.

Two runs took **15.53 / 15.47 s**, including **4.18 / 4.24 s** image-context
generation and its model lifecycle, **10.25 / 10.13 s** translation inference,
and about one second of translator startup. The previous integrated backend's
translation stage took about 42 s, but its measurement also includes checksum
verification. Do not describe these as exactly equivalent end-to-end timings.

All 74 IDs returned parseable JSON. Three regions were rejected in both runs:
the unquoted `demo` command changed, article references disappeared, and a
long passage changed protected numeric content. Those regions retain English.
The backup warning retained NOT-deleted, 30 seconds and 12.5 MB. A generic screen
summary also loses detailed spatial context, so successful parsing does not
establish translation fidelity or short-label disambiguation.

Using four CPU threads for **the translator only** took **84.25 / 83.72 s**;
the image model still used the GPU. This is not an all-CPU benchmark.
The experimental scripts are not wired into the plugin or installed runtime.
The local selection remains the original Qwen3.5-4B backend pending quality gates.
Raw measurements are private under `.size-check/split-gpu-20260911/` and
`.size-check/split-cpu-text-20260911/`.

The prompt uses the background and structured-data patterns in the
[official Hy-MT2 model card](https://huggingface.co/tencent/Hy-MT2-1.8B).
The source and reference checks cannot catch omitted instructions or every
semantic change. A future backend must retain the actual nearby OCR/coordinates,
not claim that a global caption is equivalent to direct image context.

### Short-label transfer gate: not passed

`benchmark_split_labels.py` tests eight authored images, deriving the explanation
from the image and target location (no gold translation supplied). With the
official background-only prompt, shop Open became `開店中`, but Save leaked the
entire explanation and its coordinates into the translation. With a JSON-only
translation prompt, Save became `保存` and file Open became `開く`, but shop Open
was left untranslated. Both prompts changed `3 herbs` to `3種類のハーブ` and added
`village` from context to the target sentence. Numeric equality alone cannot
detect these semantic changes. These are development checks, not native-reviewed
quality scores; eight fixtures are insufficient to establish broad accuracy.

Decision: keep this fast split architecture experimental. Merely handing off a
free-form image caption is not a reliable substitute for direct visual context.
Next comparison should route ambiguous labels to the visual translator and
provide exact neighboring OCR plus bounded region metadata to the specialized
translator, with regression gates for context leakage and quantity semantics.
Do not use another LLM's approval as proof of correctness. Private outputs:
`.size-check/split-labels-structured-20260911/report.json`.

## Hybrid routing follow-up

`benchmark_hybrid.py` routes English strings of six words or fewer to direct
image-aware translation and longer strings to Hy-MT2 with exact nearby OCR.
This is a deliberately simple experimental heuristic, not semantic UI detection
or a language-independent routing policy. Tests cover routing, batching, source
versus reference separation and rejecting unverified candidate weights.

On the same 74-region screen, 63 regions went to Qwen3.5-4B and 11 to Hy-MT2.
Putting source and references in the same JSON made Hy translate both; both
body batches were rejected. After separating reference information from the
source JSON, all batches returned the expected structure. The `demo` command
and a clipped historical passage still failed protected-content checks and
retained their original text. The two total inference/lifecycle times were
**33.72 / 51.65 seconds**, excluding checksum/OCR/render/display. Visual work
took 27.34 / 28.98 s; text work took 6.38 / 22.67 s. Token counts were identical
but generation speed varied; the cause of that timing variation is unconfirmed.

A proposed 32-label visual batch could not be timed with the 4B model: startup
failed. A separate startup reproduction confirmed Vulkan `ErrorOutOfDeviceMemory`
while this active desktop had about 2,969 MiB free VRAM. No user applications
were closed and no GPU/system settings were changed. This is a practical risk
for a screen translator sharing an 8 GB GPU with normal applications.

### Smaller visual candidate: Qwen3.5-0.8B

Downloaded and checksum-verified for isolated tests, not installed as the app's
model. The [official model card](https://huggingface.co/Qwen/Qwen3.5-0.8B)
positions this size for prototyping and task-specific development.
Quantization source: `unsloth/Qwen3.5-0.8B-GGUF`, revision
`6ab461498e2023f6e3c1baea90a8f0fe38ab64d0`.

- Q4_K_M: 532,517,120 bytes; SHA-256 `bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517`.
- F16 projector: 204,987,232 bytes; SHA-256 `56e4c6cfe73b0c82e3e82bc518d7591997e61d81f723fc41a586f4fa69ea2453`.
- Total additional weights: 737,504,352 bytes, not part of the compact app.

It started under the observed memory pressure. Five short authored labels took
1.88–1.96 seconds each including startup/shutdown, not whole-screen latency.
Save and discount were plausible, but file Open became `選択してください` and
shop Open became `開店`, losing the intended action/state distinction. The three
longer fixture messages were handled by **Hy**, not the small visual model;
Hy still changed `3 herbs` into `3種類のハーブ` despite exact rather than generated
context. This hybrid does not pass the quantity-semantics quality gate.

Private evidence: `.size-check/hybrid-real-20260911`,
`.size-check/hybrid-boundary-real-20260911`,
`.size-check/hybrid-small-labels-20260911`. The installed app and provider
configuration remain unchanged.

### Intermediate candidate: Qwen3.5-2B

Also downloaded and verified, rather than limiting evaluation to existing models.
Source: `unsloth/Qwen3.5-2B-GGUF` revision
`f6d5376be1edb4d416d56da11e5397a961aca8ae`.

- Q4_K_M: 1,280,835,840 bytes; SHA-256 `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`.
- F16 projector: 668,227,264 bytes; SHA-256 `7035e9cb8d7c6a9681d07eef9a364783e86ea4cd73faab2eabb4f43a101830c7`.
- Total: 1,949,063,104 bytes of additional weights.

All eight fixtures used direct image-aware translation, without Hy. Each completed
in 2.49–2.70 s including its own startup/shutdown. Shop and file Open both stayed
English, as did Reply to @Adobe and the terminal instruction. The backup prohibition
became an inability (`抜くことはできません`), and the herb instruction added a
return/carry-back nuance. Save and discount translated plausibly. These failures
prevent recommending this candidate; per-fixture speed is not whole-screen speed.
See `.size-check/qwen35-2b-direct-labels-20260911/report.json`.
GPU memory availability increased during this test session; successful startup
is not proof the 2B model fits the earlier 2,969 MiB-free state.

### Retried larger visual batches after GPU memory became available

The unchanged 4B model could start again after external desktop memory usage
decreased. Retrying 32-label batches (same 63 visual / 11 text targets) produced
**25.28 / 24.53 s** total inference/lifecycle time. Visual work was 18.77 / 18.34 s;
text work was 6.51 / 6.19 s. All 74 IDs were returned; the same two protected-content
failures (`42`, `121`) retained English. Result caching remained disabled.
This does not include OCR/render/display or establish 15-second shortcut latency.

Manual comparison against eight-label batches found changed wording, including
`free encyclopedia` shifting from `自由百科事典` to `無料百科事典`; the larger batch
also preserved the separate Small and Standard labels better. Speed is improved
but semantic quality is not uniformly improved. Together with the herb quantity
regression in Hy and 4B memory failures, this prevents promoting the hybrid as
the default local backend. Exact measurements and translations are private in
`.size-check/hybrid-batch32-retry-20260911/report.json`.

Future stability work can evaluate llama.cpp's documented `--gpu-layers auto`
and `--fit on` (already supported by the local binary), rather than forcing 99
GPU layers. Partial CPU offload may avoid startup failure but its latency must
be measured; it has not been enabled in the installed app.

## Earlier text-only experiment (historical)


Status at the time: promising translation-only experiment, **not a production backend**.
For the subsequent measured image-context CPU/GPU comparison, see
[VISUAL-LOCAL-BENCHMARK.md](VISUAL-LOCAL-BENCHMARK.md).
The plugin still explicitly uses OpenAI. It never automatically switches between
local and cloud translation.

## Candidate

[Tencent Hy-MT2-1.8B](https://huggingface.co/tencent/Hy-MT2-1.8B), Apache-2.0,
using the official [Q4_K_M GGUF](https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF).
This is text-only: it cannot consume our screen-image context directly. The
existing OpenAI image-plus-text path is retained while this alternative is evaluated.

- Repository revision: `a0c709d9fac510f2c807aa3af52872340dc37a4a`
- File: `Hy-MT2-1.8B-Q4_K_M.gguf`
- Bytes: `1133080448` (1.13 GB decimal), additional to the app and llama.cpp runtime
- SHA-256: `dc5f44fcf1fa496ee7ad725982c0c8c553a4de00259b53af84c4b89fb0c06699`
- Runtime tested: existing llama.cpp b10867, CPU-only, four threads, 2,048-token context
- Host: Core i9-14900K, 64 GB RAM. This is **not** representative-laptop validation.

The benchmark verifies the model checksum, starts an owned server on a private
Unix socket (no TCP listener), uses authored non-private text and stops the
server after the test. No API key or desktop capture is used. The tool does not
install packages, register a service or change the production provider.

## Measurements

One run, three authored English samples per destination (15 requests), no
translation-result cache; prompt caching disabled. Server startup: **0.75 s**.

| Destination | Minimum / maximum per sample |
| --- | --- |
| Japanese | 0.52 / 1.04 s |
| English | 0.42 / 0.58 s |
| Simplified Chinese | 0.44 / 0.82 s |
| Spanish | 0.55 / 1.31 s |
| French | 0.61 / 1.29 s |

These timings exclude OCR, image context, capture, rendering and display. They
must not be presented as whole-screen latency or a comparison against a full
cloud run. Weight files may already be in the OS page cache. Repeated cold
starts, peak memory and laptop performance remain unmeasured.

Examples: `Save changes` became `変更を保存する`; the offline/no-upload sentence
kept its negation in Japanese. The English destination paraphrased `Retry` as
`Try again`, demonstrating that same-language preservation needs an explicit
guard. Other target languages have not received native-speaker review. Three
samples do not establish general translation quality.

## Reproduce

Obtain the pinned weights above and a trusted llama.cpp server separately, then:

```sh
/usr/bin/python -B benchmark_local_translation.py \
  --server /absolute/path/to/llama-server \
  --model /absolute/path/to/Hy-MT2-1.8B-Q4_K_M.gguf \
  --output /absolute/path/to/new-results-directory
```

Outputs: `report.json` (public inputs, translations, timings) and `server.log`.
Use a new output directory for each run. No model is downloaded automatically
when the plugin loads.

## Before integration

1. Compare saved real-screen OCR corpora, not just short labels, with the current
   cloud result. Measure total time, coverage, numbers, negation and clipped text.
2. Test surrounding OCR text/coordinates as context. Keep the lack of image
   understanding visible to the user instead of claiming equivalence.
3. Bound every request and generation; preserve the original region on failure.
4. Add a separate model-install action with the total download/disk cost and
   checksum verification, plus local/cloud selection with no silent fallback.
5. Measure on a 16 GB laptop without a discrete GPU before recommending it as
   a default for typical recent PCs.
