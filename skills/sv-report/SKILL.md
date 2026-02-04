---
name: sv-report
description: Generate SV-Bench metrics reports (summary.json + report.md) for E1/E2 runs, validate metrics contracts, and produce comparison-friendly artifacts from outputs/evals/.
metadata:
  author: security-verifiers
  version: "1.0"
---

# SV-Bench Reporting (E1/E2)

Generate the **WP1** report artifacts for evaluation runs:
- `summary.json` (schema: `bench/schemas/summary.schema.json`)
- `report.md` (human-readable)

This skill is for **report generation/validation**, not running new evals (use `sv-eval` for that).

## Prereqs

- Use the repo venv (`.venv/`) or your preferred runner.
- If you want to avoid any network calls during report generation, set:
  - `WEAVE_DISABLED=true`

## Per-run report (single directory)

```bash
WEAVE_DISABLED=true .venv/bin/svbench_report --env e1 --input outputs/evals/sv-env-network-logs--gpt-5-mini/<run_id> --strict
WEAVE_DISABLED=true .venv/bin/svbench_report --env e2 --input outputs/evals/sv-env-config-verification--gpt-5-mini/<run_id> --strict
```

Outputs are written into the same run directory:
- `outputs/evals/.../<run_id>/summary.json`
- `outputs/evals/.../<run_id>/report.md`

## Batch-generate reports for many runs

Generate reports for all non-archived runs under `outputs/evals/`:

```bash
.venv/bin/python scripts/generate_svbench_reports.py
```

Only E1:
```bash
.venv/bin/python scripts/generate_svbench_reports.py --env e1 --strict
```

Only E2:
```bash
.venv/bin/python scripts/generate_svbench_reports.py --env e2 --strict
```

Specific run ids:
```bash
.venv/bin/python scripts/generate_svbench_reports.py --run-ids d4e7f897 cb97305e
```

## Comparison reports (across runs)

The Make targets produce comparison-friendly JSON across runs:

```bash
make report-network-logs
make report-config-verification
```

These are intended for quick comparisons / dashboards. The contract-grade per-run artifacts are generated via `bench.report` / `svbench_report`.
