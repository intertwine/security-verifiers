---
name: sv-hf
description: Manage HuggingFace datasets for Security Verifiers. Use when asked to push datasets to HuggingFace, manage metadata, configure gated access, or set up user HF repositories for E1/E2 datasets.
metadata:
  author: security-verifiers
  version: "1.0"
---

# Security Verifiers HuggingFace Management

Push, validate, and manage datasets on HuggingFace Hub for E1 (network-logs) and E2 (config-verification) environments.

## Repository Structure

| Repo Type | E1 Repo | E2 Repo | Access |
|-----------|---------|---------|--------|
| Public metadata | `{org}/security-verifiers-e1-metadata` | `{org}/security-verifiers-e2-metadata` | Public |
| Private canonical | `{org}/security-verifiers-e1` | `{org}/security-verifiers-e2` | Gated |

## Prerequisites

Set environment variables in `.env`:

```bash
HF_TOKEN=hf_your_token_here
E1_HF_REPO=your-org/security-verifiers-e1
E2_HF_REPO=your-org/security-verifiers-e2
```

## Quick Reference

```bash
# Build metadata locally
make hf-e1-meta
make hf-e2-meta

# Push to PUBLIC repos (metadata only)
make hf-e1-push HF_ORG=your-org
make hf-e2-push HF_ORG=your-org

# Push to PRIVATE repos (canonical splits with Features)
make hf-e1p-push-canonical HF_ORG=your-org
make hf-e2p-push-canonical HF_ORG=your-org

# Validate before push
make validate-data

# Push all metadata
make hf-push-all HF_ORG=your-org
```

## Metadata Push (Public Repos)

Metadata repos provide Dataset Viewer compatibility without exposing sensitive data.

### Build Metadata Locally

```bash
make hf-e1-meta  # → build/hf/e1/meta.jsonl
make hf-e2-meta  # → build/hf/e2/meta.jsonl
```

### Push to Public Repos

```bash
# Default org: intertwine-ai
make hf-e1-push
make hf-e2-push

# Custom org
make hf-e1-push HF_ORG=your-org
make hf-e2-push HF_ORG=your-org
```

## Canonical Push (Private Repos)

Canonical repos contain full datasets with explicit HuggingFace Features schema.

### Validate First

```bash
make validate-e1-data
make validate-e2-data
# or
make validate-data  # both
```

### Push Canonical Splits

```bash
# E1 canonical (train/dev/test splits)
make hf-e1p-push-canonical HF_ORG=your-org

# E2 canonical
make hf-e2p-push-canonical HF_ORG=your-org
```

**Warning**: Canonical push uses `--force` which deletes and recreates the repo. Use only when schema changes are needed.

### Dry Run

```bash
make hf-e1p-push-canonical-dry HF_ORG=your-org
make hf-e2p-push-canonical-dry HF_ORG=your-org
```

## User Dataset Setup

For users deploying their own Security Verifiers instances:

### 1. Build Datasets Locally

```bash
make data-e1 data-e1-ood
make clone-e2-sources && make data-e2-local
```

### 2. Configure HF Repos

```bash
export HF_TOKEN=hf_your_token
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private
```

### 3. Push Datasets

```bash
make hub-push-datasets
```

### 4. Test Loading

```bash
make hub-test-datasets
```

## Gated Access

Private repos use manual gated access to prevent training contamination:

1. Go to repo Settings → Access
2. Enable "Gated repository"
3. Set to "Manual approval"
4. Users must request access and set `HF_TOKEN`

Template READMEs for gated repos are in `scripts/hf/templates/`.

## Dataset Loading in Code

```python
import os
from datasets import load_dataset

# Set token
os.environ["HF_TOKEN"] = "hf_your_token"

# Load from private repo
dataset = load_dataset(
    "your-org/security-verifiers-e1",
    split="train",
    token=os.environ["HF_TOKEN"]
)
```

## Environment Loading Modes

Environments automatically handle dataset loading:

```python
import verifiers as vf

# Auto: tries local → hub → synthetic
env = vf.load_environment("sv-env-network-logs")

# Explicit hub loading
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")

# Synthetic fallback (for testing)
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

## Troubleshooting

**401 Unauthorized**: Check `HF_TOKEN` is set and has write access.
**Gated access denied**: Request access on HF repo page, then set `HF_TOKEN`.
**Schema mismatch**: Run `make validate-data` before push.
**Force push warning**: Canonical push recreates repos; use only for schema updates.

## File Locations

| Purpose | Location |
|---------|----------|
| HF push scripts | `scripts/hf/` |
| Metadata export | `scripts/hf/export_metadata_flat.py` |
| Canonical push | `scripts/hf/push_canonical_with_features.py` |
| Validation scripts | `scripts/data/validate_splits_e1.py`, `validate_splits_e2.py` |
| Gated README templates | `scripts/hf/templates/` |
