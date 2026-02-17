# Prime Lab Integration (WP2.5)

This document defines the hosted-first integration path for SV-Bench E1/E2.

## 1) Compatibility gate

Run:

```bash
make lab-check
```

Gate policy:

- If `prime lab` is available and auth succeeds, use hosted training/eval (`lab-*` targets).
- If `prime lab` is not available, use fallback hosted-style eval (`env-eval-*` targets) until Lab access is active.

## 2) Dependencies

Install with Lab extras:

```bash
make setup
source .venv/bin/activate
uv sync --extra lab
```

Lab extras include `prime-cli` and `prime-rl` for hosted orchestration readiness.

## 3) Hosted training templates

- `configs/rl/e1.toml`
- `configs/rl/e2.toml`

Launch commands:

```bash
make lab-run-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine
make lab-run-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine
```

## 4) Hosted eval templates

- `configs/eval/e1.toml`
- `configs/eval/e2.toml`

Launch commands:

```bash
make lab-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine
make lab-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine
```

## 5) Fallback hosted-style eval parity

Use `prime env eval` wrappers:

```bash
make env-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=100
make env-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=50
```

## 6) Metadata normalization for report pipeline

Normalize hosted metadata into SV-Bench schema:

```bash
python scripts/normalize_hosted_eval.py \
  --input hosted/metadata.json \
  --output outputs/evals/<run-id>/metadata.json \
  --environment sv-env-network-logs \
  --dataset public-mini-e1
```

Expected normalized fields include `run_id`, model/revision, dataset revision, platform metadata, and git SHA.
