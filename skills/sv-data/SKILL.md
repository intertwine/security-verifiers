---
name: sv-data
description: Build and manage Security Verifiers datasets. Use when asked to build E1 or E2 datasets, create test fixtures, validate data, or manage dataset files for network-logs or config-verification environments.
metadata:
  author: security-verifiers
  version: "1.0"
---

# Security Verifiers Data Management

Build, validate, and manage datasets for E1 (network-logs) and E2 (config-verification) environments.

## Dataset Types

| Type | Purpose | Location | Committed |
|------|---------|----------|-----------|
| Production | Full training/eval data | `environments/sv-env-*/data/` | No (private) |
| Test fixtures | CI/unit tests | `environments/sv-env-*/data/` | Yes (small) |
| HuggingFace | Remote dataset access | HF Hub | Private repos |

## E1: Network Logs Datasets

### Build Production Dataset (IoT-23)

```bash
# Full dataset (1800 examples, 60/20/20 split)
make data-e1

# Custom limit
make data-e1 LIMIT=3000
```

Outputs: `environments/sv-env-network-logs/data/iot23-train-dev-test-v1.jsonl`

### Build OOD (Out-of-Distribution) Datasets

```bash
# CIC-IDS-2017 and UNSW-NB15 (600 examples each)
make data-e1-ood

# Custom count
make data-e1-ood N=1000
```

Outputs:
- `cic-ids-2017-ood-v1.jsonl`
- `unsw-nb15-ood-v1.jsonl`

### Build Test Fixtures

```bash
# Small datasets for CI (20-30 examples)
make data-e1-test
```

## E2: Config Verification Datasets

### Clone Source Repositories

E2 datasets are built from real Kubernetes and Terraform configs:

```bash
# Clone recommended repos
make clone-e2-sources
```

Clones to `scripts/data/sources/`:
- `kubernetes/` - K8s YAML manifests
- `terraform/` - Terraform HCL configs

### Build Production Dataset

```bash
# Using cloned sources
make data-e2-local

# Using custom paths
make data-e2 K8S_ROOT=/path/to/k8s TF_ROOT=/path/to/terraform
```

Outputs:
- `environments/sv-env-config-verification/data/k8s-labeled-v1.jsonl`
- `environments/sv-env-config-verification/data/terraform-labeled-v1.jsonl`

### Build Test Fixtures

```bash
# Requires clone-e2-sources first
make clone-e2-sources
make data-e2-test
```

## Build All Datasets

```bash
# All E1 production datasets
make data-all

# All test fixtures (for CI)
make data-test-all
```

## Data Validation

Validate datasets with Pydantic before HuggingFace push:

```bash
# Validate E1 splits
make validate-e1-data

# Validate E2 splits
make validate-e2-data

# Validate all
make validate-data
```

## Dataset Schema

### E1 Schema (network-logs)

```json
{
  "id": "unique-id",
  "log_entry": "192.168.1.1 - GET /api/users ...",
  "label": "malicious",
  "attack_type": "botnet",
  "source": "iot23",
  "split": "train"
}
```

### E2 Schema (config-verification)

```json
{
  "id": "unique-id",
  "config_content": "apiVersion: v1\nkind: Pod...",
  "config_type": "kubernetes",
  "violations": [
    {
      "rule_id": "no-latest-tag",
      "severity": "high",
      "message": "Image uses :latest tag"
    }
  ],
  "split": "train"
}
```

## Dataset Locations

| Environment | Data Directory |
|-------------|----------------|
| E1 network-logs | `environments/sv-env-network-logs/data/` |
| E2 config-verification | `environments/sv-env-config-verification/data/` |

## Loading Datasets

Environments support multi-tier loading:
1. **Local**: JSONL files in `data/` directory
2. **Hub**: HuggingFace (requires HF_TOKEN)
3. **Synthetic**: Built-in test fixtures (fallback)

```python
import verifiers as vf

# Auto mode (tries local → hub → synthetic)
env = vf.load_environment("sv-env-network-logs")

# Explicit source
env = vf.load_environment("sv-env-network-logs", dataset_source="local")
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

## Troubleshooting

**HF_TOKEN required**: Set in `.env` for gated dataset access.
**Missing sources**: Run `make clone-e2-sources` before E2 data builds.
**Validation fails**: Check schema matches expected Pydantic models in `scripts/data/validate_splits_*.py`.
