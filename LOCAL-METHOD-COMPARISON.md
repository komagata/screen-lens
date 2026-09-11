# Local translation method comparison

Scope: close the outstanding candidate methods discussed as of 2026-09-11.
No changes to the installed application, credentials, model selection or OS settings.
Images and raw reports stay in private, ignored `.size-check` directories.

## Evaluation boundaries

- Same saved 74-region Wikipedia/terminal OCR corpus and eight authored context fixtures.
- Record unchanged source/fallback, not just JSON validity or latency.
- Negation, quantities, code and short-label disambiguation are manual quality gates.
- Times include model startup/shutdown unless stated otherwise; they exclude OCR,
  capture, rendering, display and initial checksum verification. Not shortcut latency.
- Active desktop GPU memory changes between runs. Offload decisions and logs matter.
- Public model downloads may overlap measurements; OS page cache is not flushed.
  These are development measurements, not controlled hardware benchmark claims.

## Candidate closure checklist

| Method | Status | Evidence / decision |
| --- | --- | --- |
| Qwen3-VL-2B direct image translation | Tested earlier; rejected | Short Open and negation failures; LOCAL-TRANSLATION.md |
| Qwen3.5-0.8B visual labels + Hy body | Tested; rejected | Incorrect label meaning, quantity change in Hy |
| Qwen3.5-2B direct image translation | Tested; rejected | English copies and changed warning meaning |
| Qwen3.5-4B direct, eight-item batches | Existing experimental baseline | About 47 s OCR/translation/render; not general-PC validation |
| One image caption + Hy structured translation | Tested; rejected | About 15.5 s inference, context leakage and quantity change |
| Exact OCR context + Hy, visual short labels | Tested; not promoted | 24.53–25.28 s with 32-label batching; semantic failures remain |
| Qwen4 direct 32-item batching | Tested; viable experiment | 30.95 / 31.11 s, two protected-content fallbacks; some repetitive paragraph wording |
| Qwen4 automatic GPU/CPU fitting | Tested; useful stability candidate | 73.44 / 36.02 s, offload changes with available VRAM; margin test below |
| Route quantities/negation/commands to visual model | Tested; leading hybrid candidate | 27.12 / 27.81 s; 67 visual + 7 text; eight fixtures below |
| TranslateGemma 4B text and image translation | Tested; rejected for this integration | Works after template adaptation; quantity drift, invalid JSON, repetitive incomplete full-screen output |

Models mentioned only as a possible future survey (for example Gemma 4 E4B)
are not silently counted as tested. The bounded method experiments above are
closed; no alternative has been promoted to the installed application.

## Detailed findings from the final round

### Direct Qwen4, 32 items

The same 74 source IDs produced valid maps in both runs. The unquoted `demo`
command and the clipped historical paragraph failed protected-content checks,
so those two regions stayed English. The backup NOT-deleted condition, 30 seconds
and 12.5 MB were retained. A long article paragraph duplicated an assertion;
ID/number validity is not proof of fidelity. Measurements:
`.size-check/qwen4-fixed32-full-20260911/report.json`.

### Automatic memory fitting

The existing app forces 99 GPU layers, which previously failed under low VRAM.
`--gpu-layers auto --fit on --fit-target 1024` could run the full corpus twice.
Its offload decisions changed between runs; 73.44 s and 36.02 s are not evidence
of a repeatable latency. The first log includes CPU model buffers of 1,165 MiB
and GPU model buffers of 1,935.81 MiB. These are buffer allocations, not peak
whole-process RAM/VRAM measurements.

An additional-margin test used `--fit-target 3072`, without allocating dummy GPU
buffers, closing applications or modifying system settings. In the shop case,
the runtime put 4/33 model layers on GPU (701.46 MiB GPU model buffer; 2,399.35 MiB
CPU mapped model buffer). All eight authored fixtures started and completed in
7.52–10.12 s each including their own startup/shutdown. This is not all-CPU or
laptop verification. Reports:
`.size-check/qwen4-auto32-full-20260911/report.json` and
`.size-check/qwen4-fit-margin3072-labels-20260911/report.json`.

### Sensitive-content hybrid

English-only experimental routing sends short strings, digits outside bracketed
references, negation words and command verbs to Qwen4. Other body text goes to
Hy with exact nearby OCR. This heuristic is not a complete safety classifier.
It routed 67/74 regions to Qwen4 and seven to Hy, taking 27.12 / 27.81 s.
Both runs retained the same two protected-content failures (`42`, `121`).

Eight authored fixtures were actually run with this routing, not inferred from
unit tests. Shop Open became `営業中`, file Open `開く`, Save `保存`, the backup
prohibition stayed a prohibition, herbs became `3本` rather than `3種類`, and the
quoted `demo` command/30 seconds survived. The @mention case was rejected and
kept English. These fixtures all routed to Qwen4; they do not demonstrate Hy's
ability to preserve quantities. The real corpus exercises both engines.

Evidence: `.size-check/hybrid-sensitive32-real-20260911/report.json` and
`.size-check/hybrid-sensitive-labels-20260911/report.json`.

### TranslateGemma 4B

Public quantization `mradermacher/translategemma-4b-it-GGUF`, pinned revision
`35a7486e128b19642cdc72d7b91b21ba388aaf42`:

- Q4_K_M model: 2,489,909,760 bytes, SHA-256 `81200d03e843d2ec1ece6eeafe7d13cb6e5211e1fcd336ade55790b683a08330`.
- Q8 projector: 591,377,600 bytes, SHA-256 `482f68be8823dfdfb3561c22cdd1c0f617d0d5e6efe9c323cc6428a4331dba01`.
- Additional weights total 3,081,287,360 bytes; not bundled with the app.

The [model's documented interface](https://huggingface.co/google/translategemma-4b-it)
requires specialized language metadata and a single text or image content item.
The initial b10867 runtime failed at startup while generating a parser for the
embedded template. This was not a model allocation failure. We extracted the
instruction text from the checksum-verified GGUF metadata, retained it in the
request and used llama.cpp's built-in Gemma role template with `--no-jinja`.
The rendered prompts were saved. This adapter, quantization and runtime version
bound the conclusions; they are not claims about every TranslateGemma deployment.

After adaptation, startup took 2.05 s. Short text probes took 0.32–0.49 s each
including the template-inspection request. However, `3 herbs` became `3種類`, and
the JSON probe replaced quotation marks, producing invalid JSON. Small images
translated their contextual headings and buttons (0.72–3.90 s per image), but
returned no source-region IDs. The full saved screen took 28.32 s and reached
the 2,048-token output limit while repeating invented topic headings; it was
not a completed translation. Increasing that limit alone is not justified as
a fix for repetition. These are inference probes, not desktop latencies.

Evidence: `.size-check/translategemma-probe-20260911/` and
`.size-check/translategemma-compatible-20260911/`.

## Decision

The sensitive-content hybrid is the most promising **next implementation
candidate**, not a validated replacement: roughly 27–28 s inference is still
above the desired 5–15 s whole-screen experience. Qwen4 direct batching is
simpler but about 31 s. Auto fit merits an explicit slow-mode/stability option,
not a claim that CPU offload is fast. No small model or dedicated image translator
passed all current checks. Keep the installed experimental backend unchanged.

Before promotion, add new held-out screenshots and phrasing, test a real laptop,
verify snapshot-to-display timing, and test cancellation with partial offload.
The eight author-written fixtures were repeatedly used during development;
their success must not be marketed as general translation-quality certification.
