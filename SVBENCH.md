# SV-Bench

SV-Bench is the benchmark release track for Security Verifiers. Version 0.1 measures whether executable security rewards produce reproducible, useful signals on two production environments:

- E1 `sv-env-network-logs`
- E2 `sv-env-config-verification`

E3-E6 belong to the broader Security Verifiers Suite roadmap and are not part of SV-Bench v0.1.

## Quick Commands

```bash
make setup && source .venv/bin/activate
make baseline-e1 MODEL=gpt-5-mini N=10
make baseline-e2 MODEL=gpt-5-mini INCLUDE_TOOLS=true N=10
uv run svbench_manifest validate bench/fixtures/e1_run_manifest.json bench/fixtures/e2_run_manifest.json
make svbench-v0.1-check
```

## Artifacts

| Artifact | Purpose |
|---|---|
| `SVBENCH_STATUS.md` | Canonical current-state map. |
| `bench/schemas/run_manifest.schema.json` | Reproducibility contract for run cards. |
| `bench/scoreboards/` | Public mini-set scoreboard artifacts. |
| `results/v0.1_baselines.md` | Baseline result summary. |
| `results/v0.1_training.md` | Hosted-training result placeholder and artifact index. |
| `reports/SVBENCH_v0.1_technical_report.md` | Narrow technical report template. |

## Public and Gated Data

Public mini sets exist for reproducible smoke tests and examples. Full benchmark splits are gated or held out where needed to reduce contamination. Red-team public data must remain sanitized and non-operational.

## Reward-Source Claim

The v0.1 research claim is only valid when executable, LLM-judge, and hybrid manifests match on budget fields. `svbench_compare_rewards` refuses unmatched budgets unless `--allow-unmatched` is explicitly passed for exploratory analysis.
