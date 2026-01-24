---
name: sv-eval
description: Run and analyze Security Verifiers evaluations. Use when asked to evaluate models on E1 (network-logs) or E2 (config-verification), generate metrics reports, compare model performance, or analyze eval results.
metadata:
  author: security-verifiers
  version: "1.0"
---

# Security Verifiers Evaluation

Run reproducible evaluations on E1 (network-logs) and E2 (config-verification) environments, generate metrics reports, and analyze results.

## Prerequisites

Ensure environment variables are set (check `.env` file):
- `OPENAI_API_KEY` - For OpenAI models (gpt-*)
- `OPENROUTER_API_KEY` - For non-OpenAI models via OpenRouter
- `WANDB_API_KEY` - For Weave logging (optional)

## Running Evaluations

### E1: Network Logs (Classification)

Single-turn anomaly detection with calibration and asymmetric costs.

```bash
# Basic eval (10 examples)
make eval-e1 MODELS="gpt-5-mini" N=10

# Multiple models
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini,qwen3-14b" N=100

# Full production dataset
make eval-e1 MODELS="gpt-5-mini" N=1800 DATASET="iot23-train-dev-test-v1.jsonl"

# OOD datasets
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="cic-ids-2017-ood-v1.jsonl"
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="unsw-nb15-ood-v1.jsonl"
```

### E2: Config Verification (Tool-Use)

Multi-turn tool-grounded auditing with KubeLinter, Semgrep, and OPA.

```bash
# Basic eval with tools (2 examples)
make eval-e2 MODELS="gpt-5-mini" N=2 INCLUDE_TOOLS=true

# Without tools (single-turn)
make eval-e2 MODELS="gpt-5-mini" N=10 INCLUDE_TOOLS=false

# Dataset options
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="k8s-labeled-v1.jsonl"
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="terraform-labeled-v1.jsonl"
make eval-e2 MODELS="gpt-5-mini" N=100 DATASET="combined"  # default
```

### Error Handling

Early stopping prevents wasted API costs:
```bash
# Stop after 5 consecutive errors (default: 3)
make eval-e1 MODELS="gpt-5-mini" N=100 MAX_CONSECUTIVE_ERRORS=5

# Disable early stopping
make eval-e1 MODELS="gpt-5-mini" N=100 MAX_CONSECUTIVE_ERRORS=0
```

## Generating Reports

Reports aggregate results from `outputs/evals/` into summary metrics.

### E1 Report (Accuracy, ECE, FN%, FP%, Abstain%)

```bash
# All non-archived runs
make report-network-logs

# Specific runs
make report-network-logs RUN_IDS="run_abc123 run_def456"

# Custom output path
make report-network-logs OUTPUT="reports/e1-comparison.json"
```

### E2 Report (MeanReward, FormatSuccess%, AvgTools, AvgTurns)

```bash
make report-config-verification
make report-config-verification RUN_IDS="run_abc123"
```

## Understanding Results

### Output Structure

```
outputs/evals/sv-env-{name}--{model}/{run_id}/
├── metadata.json    # Run config, versions, git SHA
└── results.jsonl    # Per-example results
```

### Key E1 Metrics (network-logs)

| Metric | Description | Target |
|--------|-------------|--------|
| Accuracy | Overall classification accuracy | Higher is better |
| ECE | Expected Calibration Error | Lower is better |
| FN% | False negative rate (missed threats) | Minimize |
| FP% | False positive rate | Minimize |
| Abstain% | Abstention rate | Context-dependent |

### Key E2 Metrics (config-verification)

| Metric | Description | Target |
|--------|-------------|--------|
| MeanReward | Average episode reward | Higher is better |
| FormatSuccess% | Valid JSON output rate | 100% |
| AvgTools | Tool calls per episode | Lower is efficient |
| AvgTurns | Turns per episode | Lower is efficient |

## Model Routing

Model names are auto-resolved via `scripts/model_router.py`:
- OpenAI models: `gpt-5-mini`, `gpt-4.1-mini`, `o1-mini`
- OpenRouter models: `qwen3-14b` → `qwen/qwen3-14b`, `llama-3.1-8b` → `meta-llama/llama-3.1-8b-instruct`

## Comparing Models

1. Run evals with same parameters:
```bash
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini,qwen3-14b" N=500
```

2. Generate report:
```bash
make report-network-logs
```

3. Review summary.json in each run directory for per-model metrics.

## Troubleshooting

**Rate limits**: Reduce N or use MAX_CONSECUTIVE_ERRORS.
**Missing API key**: Check `.env` has correct key for model provider.
**Model not found**: Use full OpenRouter path (e.g., `openai/gpt-5-mini`).
