# Security Verifiers Dataset Quality Report - v1.1

**Date:** 2025-10-22
**Status:** ✅ Complete
**Version:** v1.1 (Quality Improvements Release)

This document consolidates the dataset validation findings, fixes applied, and HuggingFace push results for Security Verifiers E1 and E2 datasets.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Validation Findings](#validation-findings)
3. [Fixes Implemented](#fixes-implemented)
4. [HuggingFace Deployment](#huggingface-deployment)
5. [Quality Improvements](#quality-improvements)
6. [Access Instructions](#access-instructions)
7. [Validation Commands](#validation-commands)

---

## Executive Summary

### ✅ Passed Validations

1. **Schema compliance** - All E1 and E2 datasets conform to expected schemas (100%)
2. **E1 IoT-23 dataset quality** - Perfect deduplication, balanced classes (50/50), transformations verified
3. **E2 K8s dataset quality** - 100% valid K8s manifests after filtering

### ❌ Critical Issues Fixed

1. **E1 OOD datasets** - Severe deduplication failures (CIC-IDS-2017: 59% → 100%, UNSW-NB15: 6.8% → 100%)
2. **E1 CIC-IDS-2017** - Label imbalance (100% benign → 50/50)
3. **E2 Terraform dataset** - Invalid prompts (53.5% → 100% valid)
4. **E1 IoT-23 split distribution** - Imbalance (29/71/0.17 → 70/15/15)
5. **E1 IoT-23 port rendering** - Missing arrow format (fixed)

---

## Validation Findings

### E1 - Network Log Anomaly Detection

#### IoT-23 Primary Dataset

**Dataset:** `iot23-train-dev-test-v1.jsonl`
**Source:** `19kmunz/iot-23-preprocessed` (HuggingFace)

| Metric                | Before (v1.0)                   | After (v1.1)                     | Status   |
| --------------------- | ------------------------------- | -------------------------------- | -------- |
| Total items           | 1800                            | 1800                             | ✅       |
| Schema validation     | 100% valid                      | 100% valid                       | ✅       |
| Label balance         | 50.0% Malicious / 50.0% Benign  | 50.0% Malicious / 50.0% Benign   | ✅       |
| Deduplication         | 1800 unique / 1800 total (100%) | 1800 unique / 1800 total (100%)  | ✅       |
| Split distribution    | train: 523, dev: 1274, test: 3  | train: 1253, dev: 269, test: 278 | ✅ FIXED |
| Protocol verification | 5/5 samples verified            | 5/5 samples verified             | ✅       |
| Port verification     | 0/5 samples verified            | 5/5 samples verified             | ✅ FIXED |

**Issues Fixed:**

- Port formatting: Now uses `sport→dport` arrow format
- Split imbalance: Changed from 29/71/0.17 to 70/15/15

#### CIC-IDS-2017 OOD Dataset

**Dataset:** `cic-ids-2017-ood-v1.jsonl`
**Source:** `bvk/CICIDS-2017` (HuggingFace)

| Metric               | Before (v1.0)                    | After (v1.1)                   | Status   |
| -------------------- | -------------------------------- | ------------------------------ | -------- |
| Total items          | 600                              | 600                            | ✅       |
| Schema validation    | 100% valid                       | 100% valid                     | ✅       |
| Label balance        | 0.0% Malicious / 100.0% Benign   | 50.0% Malicious / 50.0% Benign | ✅ FIXED |
| Deduplication        | 354 unique / 600 total (59%)     | 600 unique / 600 total (100%)  | ✅ FIXED |
| Most duplicated hash | 172 copies of `9920a0569b422179` | 0 duplicates                   | ✅ FIXED |

**Root Causes:**

- Temporal clustering: Attacks appear late in dataset
- 5-tuple deduplication: Many flows share same connection tuple

**Fixes Applied:**

- Content-based deduplication (5-tuple + bytes + duration + state + service)
- Stratified sampling (fetch 10-30x samples to ensure attack diversity)

#### UNSW-NB15 OOD Dataset

**Dataset:** `unsw-nb15-ood-v1.jsonl`
**Source:** `Mireu-Lab/UNSW-NB15` (HuggingFace)

| Metric                | Before (v1.0)                    | After (v1.1)                   | Status   |
| --------------------- | -------------------------------- | ------------------------------ | -------- |
| Total items           | 600                              | 600                            | ✅       |
| Schema validation     | 100% valid                       | 100% valid                     | ✅       |
| Label balance         | 55.7% Malicious / 44.3% Benign   | 55.7% Malicious / 44.3% Benign | ✅       |
| Deduplication         | 41 unique / 600 total (6.8%)     | 600 unique / 600 total (100%)  | ✅ FIXED |
| Most duplicated hash  | 305 copies of `1c3069ed3ea222da` | 0 duplicates                   | ✅ FIXED |
| Protocol verification | 3/5 samples verified             | 5/5 samples verified           | ✅ FIXED |

**Root Causes:**

- Background traffic: Many identical connection patterns
- 5-tuple deduplication: Collapsed to 41 unique patterns

**Fixes Applied:**

- Content-based deduplication (same as CIC-IDS-2017)
- Column name handling for protocol field

### E2 - Config Security Verification

#### K8s Dataset

**Dataset:** `k8s-labeled-v1.jsonl`
**Source:** Local repositories (kubernetes/examples, GoogleCloudPlatform/microservices-demo, etc.)

| Metric                | Before (v1.0)                  | After (v1.1)                   | Status   |
| --------------------- | ------------------------------ | ------------------------------ | -------- |
| Total items           | 462                            | 444                            | ✅       |
| Schema validation     | 100% valid                     | 100% valid                     | ✅       |
| Files with violations | 255 / 462 (55.2%)              | 244 / 444 (55.0%)              | ✅       |
| Total violations      | 1503                           | 1436                           | ✅       |
| Avg violations/item   | 3.25                           | 3.23                           | ✅       |
| Violations by tool    | KubeLinter: 1062, Semgrep: 441 | KubeLinter: 1014, Semgrep: 422 | ✅       |
| Prompt validation     | 445 / 462 (96.3%)              | 444 / 444 (100%)               | ✅ FIXED |

**Issues Fixed:**

- Removed 18 non-manifest files (LICENSE, README, scripts)
- All prompts now have valid K8s YAML markers

#### Terraform Dataset

**Dataset:** `terraform-labeled-v1.jsonl`
**Source:** Local repositories (terraform-aws-modules/vpc, eks, rds)

| Metric                | Before (v1.0)     | After (v1.1)     | Status   |
| --------------------- | ----------------- | ---------------- | -------- |
| Total items           | 260               | 115              | ✅       |
| Schema validation     | 100% valid        | 100% valid       | ✅       |
| Files with violations | 4 / 260 (1.5%)    | 4 / 115 (3.5%)   | ✅       |
| Total violations      | 4                 | 4                | ✅       |
| Avg violations/item   | 0.015             | 0.035            | ✅       |
| Prompt validation     | 139 / 260 (53.5%) | 115 / 115 (100%) | ✅ FIXED |

**Issues Fixed:**

- Removed 145 invalid files (39 empty, 106 non-HCL)
- All prompts now have valid Terraform HCL markers

---

## Fixes Implemented

### E1 Content-Based Deduplication

**File:** [scripts/data/build_e1_ood.py](../scripts/data/build_e1_ood.py)

```python
def content_hash_key(row) -> str:
    """Generate content-based hash for deduplication."""
    src = str(row.get("src_ip") or row.get("srcip") or "?")
    dst = str(row.get("dst_ip") or row.get("dstip") or "?")
    sp = str(row.get("sport") or row.get("src_port") or row.get("Src Port") or "?")
    dp = str(row.get("dport") or row.get("dst_port") or row.get("Dst Port") or "?")
    proto = str(row.get("proto") or row.get("Protocol Type") or row.get("Protocol") or "?")

    # Add content-based fields to reduce false duplicates
    sbytes = str(row.get("sbytes") or row.get("Tot Fwd Pkts") or "?")
    dbytes = str(row.get("dbytes") or row.get("Tot Bwd Pkts") or "?")
    dur = str(row.get("duration") or row.get("flow_duration") or "?")
    state = str(row.get("state") or row.get("conn_state") or "?")
    service = str(row.get("service") or row.get("Service") or "?")

    key = f"{src}|{dst}|{sp}|{dp}|{proto}|{sbytes}|{dbytes}|{dur}|{state}|{service}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
```

### E1 Stratified Sampling (CIC-IDS-2017)

**File:** [scripts/data/build_e1_ood.py](../scripts/data/build_e1_ood.py)

```python
def stratified_sample_cic(dataset, n_target: int, token=None):
    """Sample CIC-IDS-2017 with stratified approach to ensure label diversity."""
    # Fetch 10-30x samples to overcome temporal clustering
    fetch_size = n_target * 10
    sampled = list(dataset.shuffle(seed=42).take(fetch_size))
    items = [to_item(dict(r), "cic-ids-2017") for r in sampled]
    items = dedup_by_hash(items)

    # Separate by label and balance 50/50
    malicious = [x for x in items if x["answer"] == "Malicious"]
    benign = [x for x in items if x["answer"] == "Benign"]

    n_malicious = min(n_target // 2, len(malicious))
    n_benign = n_target - n_malicious

    result = malicious[:n_malicious] + benign[:n_benign]
    random.shuffle(result)
    return result
```

### E1 Port Rendering Fix

**File:** [scripts/data/build_e1_iot23.py](../scripts/data/build_e1_iot23.py)

```python
def get_port(row: Dict[str, Any], port_type: str) -> str:
    """Extract port with fallback for multiple column names."""
    if port_type == "src":
        candidates = ["src_port", "sport", "id.orig_p", "Src Port"]
    else:
        candidates = ["dst_port", "dport", "id.resp_p", "Dst Port"]

    for col in candidates:
        if col in row and row[col] is not None:
            val = row[col]
            if isinstance(val, (int, float)) and val >= 0:
                return str(int(val))
            elif isinstance(val, str) and val.strip() and val != "-":
                return val.strip()
    return "?"
```

### E1 Split Distribution Fix

**File:** [scripts/data/build_e1_iot23.py](../scripts/data/build_e1_iot23.py)

```python
def split_by_scenario(rows: List[Dict[str, Any]], train_p=0.70, dev_p=0.15) -> List[Tuple[Dict[str, Any], str]]:
    """Split dataset into train/dev/test with proper distribution."""
    from collections import defaultdict

    # Group by scenario and label to maintain balance
    by_scn_label = defaultdict(list)
    for r in rows:
        scn = str(r.get("scenario") or r.get("Scenario") or "unknown")
        label = r.get("label") or r.get("binary_label") or "unknown"
        key = f"{scn}:{label}"
        by_scn_label[key].append(r)

    # Split each scenario:label group proportionally
    paired = []
    for group_rows in by_scn_label.values():
        random.shuffle(group_rows)
        n = len(group_rows)
        train_cut = int(n * train_p)
        dev_cut = int(n * (train_p + dev_p))

        for i, r in enumerate(group_rows):
            if i < train_cut:
                split = "train"
            elif i < dev_cut:
                split = "dev"
            else:
                split = "test"
            paired.append((r, split))

    random.shuffle(paired)
    return paired
```

### E2 Content Validation

**File:** [scripts/data/build_e2_k8s_tf.py](../scripts/data/build_e2_k8s_tf.py)

```python
def is_valid_k8s_manifest(path: Path) -> bool:
    """Check if file contains valid K8s manifest."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    if not content.strip():
        return False

    # Check for K8s API markers (need at least 2)
    k8s_markers = ["apiVersion:", "kind:", "metadata:", "spec:"]
    marker_count = sum(1 for marker in k8s_markers if marker in content)
    return marker_count >= 2

def is_valid_hcl(path: Path) -> bool:
    """Check if file contains valid Terraform HCL."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    if not content.strip():
        return False

    # Check for HCL block markers
    hcl_markers = ["resource ", "module ", "data ", "variable ", "output ", "provider ", "terraform "]
    return any(marker in content for marker in hcl_markers)
```

---

## HuggingFace Deployment

### Repositories

**Public Metadata** (Browse-only, no actual data):

- [intertwine-ai/security-verifiers-e1-metadata](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata)
- [intertwine-ai/security-verifiers-e2-metadata](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata)

**Private Canonical** (Gated access, actual datasets):

- [intertwine-ai/security-verifiers-e1](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1)

  - `train`: 1253 samples (69.6%)
  - `dev`: 269 samples (14.9%)
  - `test`: 278 samples (15.4%)
  - `ood`: 1200 samples (CIC-IDS-2017: 600 + UNSW-NB15: 600)
  - **Total:** 3000 samples

- [intertwine-ai/security-verifiers-e2](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2)
  - `train`: 559 samples (K8s: 444 + Terraform: 115)
  - **Total:** 559 samples

### Troubleshooting Issues Encountered

#### Issue 1: Schema Mismatch Errors

**Problem:** HuggingFace repos had old metadata schema from previous push

**Solution:**

1. Deleted old JSONL files from repo root
2. Updated README.md to remove `dataset_info` schema
3. Cleared cached metadata

#### Issue 2: Feature Validation Failures

**Problem:** `push_to_hub()` validates against existing splits

**Solution:**

- Ensured repos were clean before canonical push
- Used consistent schema across all splits

---

## Quality Improvements

### E1 Summary

| Metric                   | Before (v1.0)             | After (v1.1)              | Status   |
| ------------------------ | ------------------------- | ------------------------- | -------- |
| **IoT-23 Splits**        | 29% / 71% / 0.17%         | 70% / 15% / 15%           | ✅ FIXED |
| **CIC-IDS-2017 Dedup**   | 59% unique (354/600)      | 100% unique (600/600)     | ✅ FIXED |
| **CIC-IDS-2017 Balance** | 100% benign, 0% malicious | 50% benign, 50% malicious | ✅ FIXED |
| **UNSW-NB15 Dedup**      | 6.8% unique (41/600)      | 100% unique (600/600)     | ✅ FIXED |
| **Port Rendering**       | Broken (no arrow)         | `sport→dport` format      | ✅ FIXED |

### E2 Summary

| Metric                      | Before (v1.0)          | After (v1.1)   | Status      |
| --------------------------- | ---------------------- | -------------- | ----------- |
| **K8s Valid Prompts**       | 96.3% (445/462)        | 100% (444/444) | ✅ FIXED    |
| **K8s Files**               | 462 (18 non-manifests) | 444 (filtered) | ✅ IMPROVED |
| **Terraform Valid Prompts** | 53.5% (139/260)        | 100% (115/115) | ✅ FIXED    |
| **Terraform Empty Files**   | 39 empty files         | 0 empty files  | ✅ FIXED    |
| **Terraform Files**         | 260 (145 invalid)      | 115 (filtered) | ✅ IMPROVED |

---

## Access Instructions

### For Users (Request Access)

1. Open an access request issue: [Security Verifiers Issues](https://github.com/intertwine/security-verifiers/issues)
2. Use the title: "Dataset Access Request: E1" or "Dataset Access Request: E2"
3. Include:
   - Name and affiliation
   - Research purpose
   - HuggingFace username
   - Commitment to not redistribute or publish the raw data

### For Approved Researchers (Download)

```bash
# Set your HuggingFace token
export HF_TOKEN=your_token_here

# Or login via CLI
huggingface-cli login

# Load datasets in Python
from datasets import load_dataset

# E1 - Network Log Anomaly Detection
ds_e1_train = load_dataset('intertwine-ai/security-verifiers-e1', split='train', token=True)
ds_e1_dev = load_dataset('intertwine-ai/security-verifiers-e1', split='dev', token=True)
ds_e1_test = load_dataset('intertwine-ai/security-verifiers-e1', split='test', token=True)
ds_e1_ood = load_dataset('intertwine-ai/security-verifiers-e1', split='ood', token=True)

# E2 - Config Security Verification
ds_e2_train = load_dataset('intertwine-ai/security-verifiers-e2', split='train', token=True)
```

### For Contributors (Build Locally)

```bash
# Set up environment
cp .env.example .env
# Edit .env with your HF_TOKEN

# Build datasets from scratch
make data-all          # E1 all datasets
make data-e2-local     # E2 from local sources

# Validate before use
make validate-data     # Pydantic validation
uv run python scripts/data/validate_e1_datasets.py --datasets all
uv run python scripts/data/validate_e2_datasets.py --datasets all
```

---

## Validation Commands

### Run E1 Validation

```bash
# Validate all E1 datasets (requires HF_TOKEN)
uv run python scripts/data/validate_e1_datasets.py --datasets all

# Validate specific dataset
uv run python scripts/data/validate_e1_datasets.py --datasets iot23
uv run python scripts/data/validate_e1_datasets.py --datasets ood

# Save report
uv run python scripts/data/validate_e1_datasets.py --datasets all --output outputs/validation-e1-report.json
```

### Run E2 Validation

```bash
# Validate all E2 datasets
uv run python scripts/data/validate_e2_datasets.py --datasets all

# Validate specific dataset
uv run python scripts/data/validate_e2_datasets.py --datasets k8s
uv run python scripts/data/validate_e2_datasets.py --datasets terraform

# With source verification (requires source repos)
uv run python scripts/data/validate_e2_datasets.py \
  --k8s-source-root scripts/data/sources/kubernetes \
  --tf-source-root scripts/data/sources/terraform

# Save report
uv run python scripts/data/validate_e2_datasets.py --datasets all --output outputs/validation-e2-report.json
```

### Verify HuggingFace Datasets

```bash
# Verify datasets are accessible (requires HF_TOKEN with access)
uv run python -c "
from datasets import load_dataset

# E1
ds = load_dataset('intertwine-ai/security-verifiers-e1', split='train', token=True)
print(f'E1 train: {len(ds)} samples')

# E2
ds = load_dataset('intertwine-ai/security-verifiers-e2', split='train', token=True)
print(f'E2 train: {len(ds)} samples')
"

# Run full validation suite
make validate-data
```

---

## Changelog

### v1.1 (2025-10-22) - Quality Improvements Release

**E1 Changes:**

- Fixed IoT-23 split distribution (70/15/15)
- Fixed CIC-IDS-2017 deduplication (100% unique)
- Fixed CIC-IDS-2017 label balance (50/50)
- Fixed UNSW-NB15 deduplication (100% unique)
- Fixed port rendering (arrow format)
- Updated DATA_CARD.md with accurate statistics

**E2 Changes:**

- Added K8s manifest validation (100% valid)
- Added Terraform HCL validation (0 empty files)
- Removed invalid/empty files from datasets
- Updated DATA_CARD.md with violation statistics
- Documented tool versions for reproducibility

**Infrastructure:**

- Created validation scripts (validate_e1_datasets.py, validate_e2_datasets.py)
- Updated HuggingFace README files
- Improved dataset build scripts
- Added comprehensive documentation

---

**Status:** ✅ COMPLETE - All datasets successfully validated, fixed, and pushed to HuggingFace!
