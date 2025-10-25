# Evaluation Results

This directory contains evaluation results for the security-verifiers environments.

## Directory Structure

```bash
outputs/evals/
├── report-network-logs-YYYYMMDD-HHMMSS.json  # Generated metrics reports
├── archived/                            # Archived test runs (< 600 results)
│   ├── sv-env-network-logs--gpt-5-mini/
│   └── sv-env-network-logs--qwen3-14b/
├── sv-env-network-logs--gpt-5-mini/    # Active baseline runs
│   ├── 96cbb8ec/                        # CIC-IDS-2017 (600 samples)
│   │   ├── metadata.json                # Run configuration
│   │   ├── results.jsonl                # Per-example results
│   │   └── summary.json                 # Aggregated metrics (auto-generated)
│   ├── cb97305e/                        # UNSW-NB15 (600 samples)
│   └── d4e7f897/                        # IoT-23 (600 samples)
└── sv-env-network-logs--qwen3-14b/     # Active baseline runs
    ├── 09a5e9cf/                        # IoT-23 (600 samples)
    ├── 4d3700d7/                        # UNSW-NB15 (600 samples)
    └── 8a31c3a2/                        # CIC-IDS-2017 (600 samples)
```

## Generating Reports

Generate E1 (network-logs) metrics report (Acc, ECE, FN%, FP%, Abstain%) from evaluation runs:

```bash
# Analyze all non-archived runs (auto-timestamped filename)
make report-network-logs

# Analyze specific run IDs
make report-network-logs RUN_IDS="d4e7f897 09a5e9cf"

# Custom output path
make report-network-logs OUTPUT="custom-report.json"
```

Report files are named `report-network-logs-YYYYMMDD-HHMMSS.json` by default.

**Per-Run Summaries**: Each evaluation run directory automatically contains a `summary.json` file with that run's metrics. This makes it easy to quickly check individual run results without regenerating the full report.

## Report Fields

Each report entry contains:

- **Split**: Dataset type (e.g., "ID (IoT-23)", "OOD (CIC-IDS-2017)")
- **Model**: Model name (e.g., "gpt-5-mini", "qwen3-14b")
- **Acc**: Accuracy (0-1, higher is better)
- **ECE**: Expected Calibration Error (0-1, lower is better)
- **FN%**: False Negative percentage (0-100, lower is better for security)
- **FP%**: False Positive percentage (0-100, balance with FN%)
- **Abstain%**: Abstention rate (0-100)
- **N**: Total number of samples evaluated
- **run_datetime**: Timestamp of evaluation run
- **run_id**: Unique identifier for the run

## Understanding the Metrics

### Accuracy (Acc)

- Binary classification accuracy on non-abstained predictions
- Calculated as: (TP + TN) / (TP + TN + FP + FN)

### Expected Calibration Error (ECE)

- Measures how well predicted confidence scores match actual accuracy
- Lower is better (0 = perfect calibration)
- Uses 10 bins by default

### False Negative Rate (FN%)

- Percentage of malicious samples incorrectly classified as benign
- Critical for security applications (missing threats)

### False Positive Rate (FP%)

- Percentage of benign samples incorrectly classified as malicious
- Important for operational overhead

### Abstention Rate (Abstain%)

- Percentage of samples where model chose not to make a prediction
- High abstention may indicate model uncertainty or distribution shift

## Dataset Information

### ID (In-Distribution): IoT-23

- Primary training/evaluation dataset
- IoT network traffic from smart home devices
- Balanced malicious/benign samples

### OOD (Out-of-Distribution): CIC-IDS-2017

- Network intrusion detection dataset
- Enterprise network traffic
- Tests generalization to different network environments

### OOD (Out-of-Distribution): UNSW-NB15

- Modern network traffic dataset
- Includes contemporary attack vectors
- Tests robustness to newer attack patterns

## Baseline Results Summary

Run `make report-network-logs` to generate a timestamped report with metrics across all datasets and models.
