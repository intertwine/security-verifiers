# E1 — Network Log Anomaly (IoT-23 baseline + OOD)

**Owner:** intertwine • **Env:** `sv-env-network-logs` • **Version:** v1

## Sources

- **Primary (ID):** IoT-23 (HF: `19kmunz/iot-23-preprocessed` - 819k rows, Zeek-processed)
- **OOD A:** CIC-IDS-2017 (HF: `bvk/CICIDS-2017` - 2.1M rows, benign + 15 attack categories)
- **OOD B:** UNSW-NB15 (HF: `Mireu-Lab/UNSW-NB15` - 82k train, 175k test, labeled)

Rationale: Matches the environment's single-turn, calibrated classification design with abstention and asymmetric costs (FN ≫ FP).

## Construction

- **Script:** `scripts/data/build_e1_iot23.py` (scenario-aware split, dedup by 5-tuple hash)
- **Prompt format:** concise natural-language summary of key flow features (proto/ports/bytes/duration/flags + device)
- **Label:** `Malicious` or `Benign` (gold); model may output `Abstain` which is scored by the environment's calibration/abstention reward
- **Splits:** `train/dev/test` from IoT-23 (70/15/15 by scenario), `ood` from CIC/UNSW slices
- **Sampling seed:** 42; `sampling-iot23-v1.json` records counts and seed

## Quality & Leakage Controls

- **Scenario-aware splitting** to reduce train/test leakage
- **Deduplication:** SHA-256 of `(src,dst,sport,dport,proto)` per row
- **Balance:** ±5% class balance per split to stabilize ECE/FN rate
- **Borderline tags:** ambiguous low-traffic/partial scans retained to probe abstention

## Licensing & Ethics

Cite original dataset licenses. Remove PII; devices are generic. Use only for research on safer detection systems.

## Intended Use

Baselines and RLFT calibration improvements (ECE ↓, FN ↓) with small, reproducible N for Step-1; expand to CICIoT2023 when scaling. :contentReference[oaicite:13]{index=13}

## Dataset Access

### ⚠️ Important: Training Contamination Prevention

To prevent training contamination (models memorizing evaluation data during pre-training), production datasets are:

- **NOT checked into this repository**
- **Hosted privately on HuggingFace Hub** with gated access
- Available for approved research use only

### Public Metadata

**Browse dataset information and composition:**

- <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata>

The public metadata repo includes:

- Sampling metadata showing how datasets were constructed
- Model cards explaining the privacy rationale and dataset composition
- Instructions for requesting access to full datasets

### For Users: Request Access to Full Datasets

**To access the full private datasets:**

1. Open an access request issue: [Security Verifiers Issues](https://github.com/intertwine/security-verifiers/issues)
2. Use the title: "Dataset Access Request: E1"
3. Include: name, affiliation, research purpose, HuggingFace username
4. Commitment to not redistribute or publish the raw data

**Approval criteria:**

- Legitimate research or educational use
- Understanding of contamination concerns
- Agreement to usage terms

We typically respond within 2-3 business days.

### For Approved Researchers: Download Private Datasets

If you have been granted access:

```bash
# Set your HuggingFace token
export HF_TOKEN=your_token_here

# Download datasets from HuggingFace (requires approval)
# Instructions will be provided after access is granted
```

### For Contributors: Build Datasets Locally

If you need to rebuild datasets from scratch:

**Prerequisites:**

- HuggingFace token (HF_TOKEN) in `.env` for source data access
- Python 3.12+ with uv package manager

**Build Production Datasets** (not committed):

```bash
# Build all E1 datasets
make data-all

# Or build individually:
make data-e1            # IoT-23 primary (1800 samples)
make data-e1-ood        # CIC-IDS-2017 + UNSW-NB15 OOD (600 samples each)
```

**Custom Parameters** (Advanced):

```bash
# Custom sample limits
make data-e1 LIMIT=2000
make data-e1-ood N=1000

# Custom HuggingFace dataset IDs
make data-e1 HF_ID=19kmunz/iot-23-preprocessed
make data-e1-ood CIC_ID=bvk/CICIDS-2017 UNSW_ID=Mireu-Lab/UNSW-NB15
```

**Build Test Fixtures** (checked in for CI):

```bash
# Small synthetic datasets for CI testing
make data-e1-test       # Builds *-test.jsonl files (20-30 samples each)
```

### Data Sources

The build scripts automatically download from these HuggingFace datasets:

**Primary Dataset:**

- **IoT-23**: `19kmunz/iot-23-preprocessed` (819k rows, Zeek-processed network traffic)
  - Captures from 20 malware IoT devices + benign traffic
  - Stratified by scenario to reduce train/test leakage

**Out-of-Distribution Datasets:**

- **CIC-IDS-2017**: `bvk/CICIDS-2017` (2.1M rows, benign + 15 attack categories)
  - Includes DDoS, PortScan, Brute Force, XSS, SQL Injection, Infiltration, Botnet
  - Note: Temporal clustering may cause label imbalance in random samples

- **UNSW-NB15**: `Mireu-Lab/UNSW-NB15` (82k train, 175k test, labeled network flows)
  - Modern attack categories: Fuzzers, Analysis, Backdoors, DoS, Exploits, Generic, Reconnaissance, Shellcode, Worms

### Data Structure

The build scripts generate the following files in `environments/sv-env-network-logs/data/`:

**Primary Datasets:**

- `iot23-train-dev-test-v1.jsonl` — IoT-23 with train/dev/test splits (70/15/15)
- `cic-ids-2017-ood-v1.jsonl` — CIC-IDS-2017 out-of-distribution samples
- `unsw-nb15-ood-v1.jsonl` — UNSW-NB15 out-of-distribution samples

**Metadata Files:**

- `sampling-iot23-v1.json` — Build reproducibility metadata (seed, splits, label counts)
- `sampling-e1-ood-v1.json` — OOD dataset sampling metadata (sources, distributions)

### Evaluation

After building datasets, run evaluations:

```bash
# Evaluate on E1 with multiple models
make eval-e1 MODELS="gpt-4o-mini,gpt-4.1-mini" N=300
```

**Artifacts:**

- Data → `environments/sv-env-network-logs/data/*.jsonl`
- Metadata → `environments/sv-env-network-logs/data/sampling-*.json`
- Evals → `outputs/evals/sv-env-network-logs--{model}/{run_id}/{metadata.json,results.jsonl}`

## Dataset Statistics

| Dataset | Samples | Malicious | Benign | Split |
|---------|---------|-----------|--------|-------|
| IoT-23 | 1800 | ~900 | ~900 | train/dev/test (523/1274/3) |
| CIC-IDS-2017 (OOD) | 600 | varies* | varies* | ood |
| UNSW-NB15 (OOD) | 600 | 334 | 266 | ood |

\* CIC-IDS-2017: Random sampling may produce imbalanced subsets due to temporal clustering of attacks in the original dataset
