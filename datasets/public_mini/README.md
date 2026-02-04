# Public Mini Datasets

Small, runnable subsets for baselines and quick checks (50–200 items).

Generated from the full local datasets:
- E1 source: `environments/sv-env-network-logs/data/iot23-train-dev-test-v1.jsonl`
- E2 sources: `environments/sv-env-config-verification/data/k8s-labeled-v1.jsonl` and `terraform-labeled-v1.jsonl`

Regenerate with:
```
uv run python scripts/data/build_public_mini.py
```

Files:
- `e1.jsonl` (balanced benign/malicious)
- `e2.jsonl` (mixed k8s + terraform)
- `sampling-public-mini.json`
