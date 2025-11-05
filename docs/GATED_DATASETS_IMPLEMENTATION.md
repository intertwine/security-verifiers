# Gated Datasets Implementation Summary

This document summarizes the implementation of gated HuggingFace dataset support for Security Verifiers environments.

## Overview

Implemented comprehensive support for **gated (manually-approved) datasets** on HuggingFace Hub to maintain benchmark integrity and prevent training contamination.

## What Was Implemented

### 1. Core Infrastructure

#### Updated `sv_shared/dataset_loader.py`

- Added `GatedRepoError` and `RepositoryNotFoundError` exception handling
- Provides clear, actionable error messages when users lack access
- Guides users to request access and set HF_TOKEN
- Falls back to local/synthetic datasets when Hub access fails

**Key features:**

- Detects gated repository access errors
- Shows direct links to dataset pages for access requests
- Explains HF_TOKEN setup process
- Suggests alternatives (local build, synthetic fixtures)

### 2. Testing Infrastructure

#### Created `scripts/hf/smoke_hub_loading.py`

- Smoke test script for verifying gated dataset access
- Tests both E1 and E2 dataset loading from Hub
- Shows clear success/failure messages
- Integrated with `make hub-test-datasets` target

**Usage:**

```bash
export HF_TOKEN=your_token_here
make hub-test-datasets
```

### 3. Configuration

#### Updated `.env.example`

- Added `E1_HF_REPO` and `E2_HF_REPO` environment variables
- Defaults to `intertwine-ai/security-verifiers-e1` and `intertwine-ai/security-verifiers-e2`
- Users can override to use their own repositories
- Clear documentation of gated access requirements

### 4. Makefile Integration

#### Updated `hub-test-datasets` target

- Now uses the new smoke test script
- Better error handling for gated datasets
- Clearer success/failure messaging

### 5. Evaluation-Only License

#### Created `DATASET_EVAL_ONLY_LICENSE.md`

- Formal license restricting dataset use to evaluation only
- Explicitly prohibits training, fine-tuning, and redistribution
- Permits aggregate metrics reporting and research publications
- Referenced in dataset card templates

**Key restrictions:**

- ✅ Evaluation of pre-trained models
- ✅ Reporting aggregate metrics
- ❌ Training or fine-tuning
- ❌ Including in pre-training data
- ❌ Redistribution

### 6. Dataset Card Templates

#### Created gated dataset card templates

- `scripts/hf/templates/e1_readme_gated.md` (E1 Network Logs)
- `scripts/hf/templates/e2_readme_gated.md` (E2 Config Verification)

**Template features:**

- Complete gating YAML front-matter
- Custom access request form
- Evaluation-only license reference
- Dataset documentation
- Usage examples with HF_TOKEN
- Clear access instructions

**Gating YAML includes:**

```yaml
gated: true
license: other
license_name: Security Verifiers Dataset Evaluation License (EVAL-ONLY)
extra_gated_heading: "Request access (evaluation only)"
extra_gated_prompt: "You agree to use this dataset for evaluation only..."
extra_gated_fields:
  Affiliation: text
  Intended use:
    type: select
    options: ["Evaluation-only", "Other (explain in Notes)"]
  Contact email: text
  HF username: text
  Brief description of research: text
  I agree to EVAL-ONLY license: checkbox
```

### 7. Documentation Updates

#### Updated `docs/hub-deployment.md`

Added comprehensive section on **"Enabling Gated Access"**:

- What is gated access and why use it
- Step-by-step instructions to enable gating on HF
- How to add dataset card with gating YAML
- Testing gated dataset loading
- Managing access requests
- Expected error messages for users without access

#### Updated `docs/user-dataset-guide.md`

Added **Step 7: Enable Gated Access (Recommended)**:

- Why use gated access (contamination prevention)
- Detailed instructions to enable gating
- How to clone HF repos and add gated README
- Managing access requests
- What users see without access (with example error message)

#### Updated `README.md`

- Clarified that datasets have **"manual gated access"**
- Emphasized evaluation-only use requirement

## User Experience

### For Dataset Owners

1. **Push datasets to HuggingFace** (existing workflow)
2. **Enable gating** in HF Settings → Gated access → Manual approval
3. **Add gated README** using provided templates
4. **Manage access requests** via HF Settings → Access requests

### For Dataset Users (Without Access)

When attempting to load gated datasets:

```text
Hugging Face gated dataset 'intertwine-ai/security-verifiers-e1' requires approved access.

To fix this:
1. Visit the dataset page: https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1
2. Click 'Request access' and wait for manual approval
3. Once approved, ensure HF_TOKEN is set:
   - Add to .env file: HF_TOKEN=hf_your_token_here
   - Or export it: export HF_TOKEN=hf_your_token_here
4. Retry your command

Alternative: Build datasets locally with 'make data-e1' or 'make data-e2-local'
```

### For Dataset Users (With Access)

Works transparently with existing workflows:

```bash
# Set HF_TOKEN (one-time)
export HF_TOKEN=hf_your_token_here

# Load from Hub (auto-detects gated access)
make eval-e1 MODELS="gpt-5-mini" N=100

# Or in Python
import verifiers as vf
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")
```

## Implementation Principles

### Minimal Changes

- Reused existing infrastructure (`dataset_loader.py`, `push_user_datasets.py`)
- No new dependencies added
- Leveraged existing HuggingFace Hub gating features
- No changes to environment core logic

### Clear Error Messages

- Actionable guidance for users
- Direct links to dataset pages
- Step-by-step remediation instructions
- Alternative fallback options (local/synthetic)

### Flexible Configuration

- Default to intertwine repositories
- Easy override via environment variables
- Works with any HuggingFace repository
- Supports both public and private repos

### Documentation-First

- Complete guides for owners and users
- Ready-to-use templates
- Clear examples and workflows
- Integrated with existing docs structure

## Testing

### Quick Tests

```bash
# Test imports
uv run python -c "from sv_shared.dataset_loader import _load_from_hub; print('✓ OK')"

# Test HF exception imports
uv run python -c "from huggingface_hub.utils import GatedRepoError; print('✓ OK')"

# Test smoke test script
uv run python scripts/hf/smoke_hub_loading.py
```

### Integration Tests

```bash
# With access (requires HF_TOKEN and approval)
export HF_TOKEN=your_token_here
make hub-test-datasets

# Without access (should show clear error)
unset HF_TOKEN
uv run python -c "
from sv_shared.dataset_loader import load_dataset_with_fallback
from pathlib import Path
try:
    load_dataset_with_fallback('iot23-train-dev-test-v1.jsonl', Path('.'), 'hub', 10)
except ValueError as e:
    print(f'Expected error: {e}')
"
```

## Files Created

- `sv_shared/hf_datasets.py` → **NOT CREATED** (reused existing `dataset_loader.py`)
- `scripts/hf/smoke_hub_loading.py` → ✅ Created
- `scripts/hf/push_dataset.py` → **NOT CREATED** (reused `scripts/push_user_datasets.py`)
- `DATASET_EVAL_ONLY_LICENSE.md` → ✅ Created
- `scripts/hf/templates/e1_readme_gated.md` → ✅ Created
- `scripts/hf/templates/e2_readme_gated.md` → ✅ Created

## Files Modified

- `sv_shared/dataset_loader.py` → Added gated error handling
- `.env.example` → Added E1_HF_REPO and E2_HF_REPO
- `Makefile` → Updated hub-test-datasets target
- `docs/hub-deployment.md` → Added gating section
- `docs/user-dataset-guide.md` → Added Step 7 (gating)
- `README.md` → Clarified manual gated access

## Next Steps (For Repository Maintainers)

### 1. Enable Gating on Existing Repositories

```bash
# 1. Go to HuggingFace repositories
#    - https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1
#    - https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2

# 2. Enable gating: Settings → Gated access → Manual approval

# 3. Add gated README files
git clone https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1
cp scripts/hf/templates/e1_readme_gated.md security-verifiers-e1/README.md
cd security-verifiers-e1
git add README.md
git commit -m "Enable gated access with eval-only license"
git push

# Repeat for E2
git clone https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2
cp scripts/hf/templates/e2_readme_gated.md security-verifiers-e2/README.md
cd security-verifiers-e2
git add README.md
git commit -m "Enable gated access with eval-only license"
git push
```

### 2. Test Gated Access

```bash
# Test with valid token (should succeed)
export HF_TOKEN=your_token_with_access
make hub-test-datasets

# Test without token (should show clear error)
unset HF_TOKEN
make hub-test-datasets  # Should fail with actionable message
```

### 3. Manage Access Requests

- Monitor email notifications for new requests
- Review at: HF Settings → Access requests
- Approve based on evaluation-only criteria
- Users must agree to EVAL-ONLY license terms

## Benefits

✅ **Prevents training contamination** - Manual approval ensures evaluation-only use
✅ **Maintains benchmark integrity** - Track who accesses datasets
✅ **Clear user guidance** - Actionable error messages with direct links
✅ **Flexible deployment** - Works for both intertwine and user repos
✅ **Minimal disruption** - Reuses existing infrastructure
✅ **Well-documented** - Complete guides for owners and users
✅ **Template-based** - Ready-to-use dataset cards with proper licensing

## License Compliance

All gated datasets use the **Security Verifiers Dataset Evaluation License (EVAL-ONLY)**:

- Permits: Evaluation, metrics reporting, research publications
- Prohibits: Training, fine-tuning, redistribution
- Enforcement: Manual approval workflow + license agreement checkbox
- Reference: [DATASET_EVAL_ONLY_LICENSE.md](./DATASET_EVAL_ONLY_LICENSE.md)

---

**Implementation Date:** 2025-11-04
**Branch:** `feat-gated-datasets`
**Status:** ✅ Complete and ready for review
