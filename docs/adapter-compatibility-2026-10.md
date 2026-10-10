# Preserved adapter compatibility — October 10, 2026

All ten preserved adapters pass an offline structural check against immutable official Qwen configuration snapshots. No base weights were downloaded and no inference, deployment or paid compute was performed. Successful shape checks do not prove loading, generation quality or Prime's historical internal base weight identity.

## Candidate bases and evidence

| Preserved cohort | Official candidate base revision | Architecture and checked shape |
|---|---|---|
| May E1 executable/judge/hybrid, three adapters | `Qwen/Qwen3.5-2B` at `15852e8c16360a2fea060d615a32b45270f8a8fc` | `Qwen3_5ForConditionalGeneration`; text hidden 2048, intermediate 6144, 24 layers; 192 LoRA tensors. |
| May E2 executable/judge/hybrid, three adapters | `Qwen/Qwen3.5-9B` at `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | `Qwen3_5ForConditionalGeneration`; text hidden 4096, intermediate 12288, 32 layers; 256 LoRA tensors. |
| Older E1 executable/executable/judge and E2 executable, four adapters | `Qwen/Qwen3-4B-Instruct-2507` at `cdbee75f17c01a7cc42f958dc650907174af0554` | `Qwen3ForCausalLM`; hidden 2560, intermediate 9728, 36 layers; 504 LoRA tensors. |

Every adapter uses rank 16, alpha 32 and the same seven named attention/MLP targets. Qwen3.5's actual tensors include three MLP projection pairs on every layer and four attention projection pairs only on full-attention layers. Its gated query projection has twice the attention output width; a generic Qwen3 shape assumption would incorrectly reject it. There are no LoRA tensors on linear-attention projections in these archives. Every expected pair, prefix, layer, input/output dimension, encoding byte count and nonoverlapping contiguous data span matches. ZIP CRCs pass again.

Official source snapshots:

- [Qwen3.5-2B configuration](https://huggingface.co/Qwen/Qwen3.5-2B/raw/15852e8c16360a2fea060d615a32b45270f8a8fc/config.json), [commit history](https://huggingface.co/Qwen/Qwen3.5-2B/commits/main).
- [Qwen3.5-9B configuration](https://huggingface.co/Qwen/Qwen3.5-9B/raw/c202236235762e1c871ad0ccb60c8ee5ba337b9a/config.json), [commit history](https://huggingface.co/Qwen/Qwen3.5-9B/commits/main).
- [Qwen3-4B-Instruct-2507 configuration](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75f17c01a7cc42f958dc650907174af0554/config.json), [commit history](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/commits/main).

The official API's histories were captured on October 10. Their latest commits are March 2, 2026 for both Qwen3.5 bases and September 17, 2025 for Qwen3-4B-Instruct-2507. These snapshot revisions therefore predate the corresponding preserved May or February/March training runs. This is a defensible base candidate for a newly pinned evaluation; it is stronger than simply selecting an unexamined current branch. It still does not establish that Prime's historical service loaded those exact weights, tokenizer/template, conversion or numerical precision. Neither the ten adapter configs nor their archived training metadata record an immutable base revision; the ZIP `STABLE` marker is not such a revision.

## Reproduction

Capture official config snapshots into private JSON reference files containing `repository`, `observed_revision`, `config` and optionally `commits`. Then run:

```bash
python3 scripts/check_preserved_adapters.py \
  --adapters /path/to/preserved-adapters \
  --references outputs/completion_20261010/adapter_reference \
  --output outputs/completion_20261010/adapter_compatibility.json
make review-check \
  REVIEW_PATHS="scripts/check_preserved_adapters.py scripts/check_preserved_adapters_test.py" \
  REVIEW_TESTS="scripts/check_preserved_adapters_test.py"
```

The reference snapshots and per-run report remain private ignored artifacts. The source checker has seven focused regression tests, including gated-query/hybrid coverage, missing/unpaired tensors, wrong-base rejection and overlapping payloads. It deliberately emits `historical_base_revision_proven: false` and `runtime_load_verified: false` even when all structural checks succeed.

## Execution consequence

The three May E1 adapters form the smallest compatible candidate serving group with one base; the original environment-version mismatch still prevents treating their training as a controlled reward-source experiment. The May E2 group is structurally compatible but only trained for one step. The older E2 adapter provides a longer-run investigation candidate, with zero recorded training reward and missing historical scanner provenance; compatibility does not cure these limitations.

Before generating reportable outputs, pin the serving base revision and tokenizer/chat-template artifacts, record the adapter ZIP and safetensors digests, verify supported PEFT/engine versions and successful load, then run a schema/tool smoke test. If Prime cannot disclose or pin its base identity, its API can support exploratory results only under that limitation; use a pinned alternate runtime for the controlled comparison. Historical base identity remains an explicit provenance gap even if newly pinned serving succeeds. Do not convert these candidate revisions into a claim that the original research's immutable historical model requirement has been recovered.
