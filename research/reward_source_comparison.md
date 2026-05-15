# Reward Source Comparison Template

Use this template after real hosted or fallback-hosted run manifests exist.

```bash
uv run svbench_compare_rewards \
  --env e1 \
  --executable results/runs/<exec-id>/run_manifest.json \
  --judge results/runs/<judge-id>/run_manifest.json \
  --hybrid results/runs/<hybrid-id>/run_manifest.json \
  --out results/ablations/reward_source/e1_comparison.md
```

The comparator refuses unmatched budgets by default. Use `--allow-unmatched` only for explicitly exploratory analysis.

Report sections:

- matched-budget validation table
- metric delta table
- confidence intervals when multiple seeds are available
- calibration and risk-coverage deltas for E1
- patch and tool-economy deltas for E2
- representative trace links
- failure-mode notes
