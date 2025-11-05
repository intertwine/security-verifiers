# Building and Pushing Datasets to Your Own HuggingFace Repository

This guide shows you how to build Security Verifiers datasets locally and push them to your own HuggingFace repositories for use with the Prime Intellect Environments Hub.

## Why Push to Your Own Repository?

When you deploy Security Verifiers environments to the Prime Intellect Hub, users won't have access to Intertwine's private dataset repositories. By pushing datasets to your own HuggingFace account, you can:

- Control access to your evaluation datasets
- Prevent training contamination
- Share datasets with collaborators
- Deploy fully functional environments to the Hub

## Quick Start (TL;DR)

```bash
# 1. Build datasets locally
make data-e1 data-e1-ood  # E1 datasets
make clone-e2-sources && make data-e2-local  # E2 datasets

# 2. Create HF repositories at https://huggingface.co/new:
#    - your-org/security-verifiers-e1-private
#    - your-org/security-verifiers-e2-private

# 3. Set environment variables
export HF_TOKEN=your_huggingface_token
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private

# 4. Push datasets
uv run python scripts/push_user_datasets.py

# 5. Test loading from your repos
uv run python -c "
import os
os.environ['HF_TOKEN'] = 'your_token'
os.environ['E1_HF_REPO'] = 'your-org/security-verifiers-e1-private'
from sv_env_network_logs import load_environment
env = load_environment(dataset_source='hub', max_examples=10)
print(f'✓ Loaded {len(env.dataset)} examples')
"
```

## Step-by-Step Guide

### Step 1: Build Datasets Locally

#### E1 (Network Logs)

```bash
# Build primary IoT-23 dataset (N=1800)
make data-e1

# Build OOD datasets (CIC-IDS-2017 and UNSW-NB15, N=600 each)
make data-e1-ood

# Verify datasets were created
ls -lh environments/sv-env-network-logs/data/
# Expected files:
# - iot23-train-dev-test-v1.jsonl
# - cic-ids-2017-ood-v1.jsonl
# - unsw-nb15-ood-v1.jsonl
```

**Time required**: ~5-10 minutes (downloads and processes datasets)

#### E2 (Config Verification)

```bash
# Clone source repositories (one-time setup)
make clone-e2-sources
# This clones:
# - kubernetes/kubernetes (for K8s configs)
# - hashicorp/terraform (for Terraform configs)

# Build labeled datasets
make data-e2-local

# Verify datasets were created
ls -lh environments/sv-env-config-verification/data/
# Expected files:
# - k8s-labeled-v1.jsonl (N=444)
# - terraform-labeled-v1.jsonl (N=115)
```

**Time required**: ~2-5 minutes (processes existing configs)

### Step 2: Create HuggingFace Repositories

1. **Go to HuggingFace**: https://huggingface.co/new

2. **Create E1 repository**:
   - Repository name: `security-verifiers-e1-private`
   - Owner: Your organization or username
   - Visibility: **Private** (to prevent training contamination)
   - Click "Create repository"

3. **Create E2 repository**:
   - Repository name: `security-verifiers-e2-private`
   - Owner: Your organization or username (same as above)
   - Visibility: **Private**
   - Click "Create repository"

4. **Note your repository URLs**:
   - E1: `https://huggingface.co/your-org/security-verifiers-e1-private`
   - E2: `https://huggingface.co/your-org/security-verifiers-e2-private`

### Step 3: Get Your HuggingFace Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: `security-verifiers-upload`
4. Type: **Write** (required for pushing datasets)
5. Click "Generate token"
6. Copy your token (starts with `hf_...`)

**Security note**: Never commit this token to git!

### Step 4: Set Environment Variables

Add to your `.env` file:

```bash
# HuggingFace authentication
HF_TOKEN=hf_your_token_here

# Your custom repositories
E1_HF_REPO=your-org/security-verifiers-e1-private
E2_HF_REPO=your-org/security-verifiers-e2-private
```

Load the environment variables:

```bash
set -a && source .env && set +a
```

Or export them directly:

```bash
export HF_TOKEN=hf_your_token_here
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private
```

### Step 5: Push Datasets to HuggingFace

Create a push script (`scripts/push_user_datasets.py`):

```python
#!/usr/bin/env python3
"""Push Security Verifiers datasets to user's HuggingFace repositories."""

import os
import sys
from pathlib import Path
from datasets import load_dataset

# Verify HF_TOKEN is set
if not os.environ.get("HF_TOKEN"):
    print("❌ Error: HF_TOKEN not set")
    print("Set it in .env file or export HF_TOKEN=your_token_here")
    sys.exit(1)

# Get repository names from environment
E1_REPO = os.environ.get("E1_HF_REPO", "your-org/security-verifiers-e1-private")
E2_REPO = os.environ.get("E2_HF_REPO", "your-org/security-verifiers-e2-private")

print(f"Pushing datasets to:")
print(f"  E1: {E1_REPO}")
print(f"  E2: {E2_REPO}")
print()

# E1 datasets
print("=" * 60)
print("Pushing E1 (Network Logs) datasets...")
print("=" * 60)

e1_data_dir = Path("environments/sv-env-network-logs/data")
e1_datasets = [
    ("iot23-train-dev-test-v1.jsonl", "train", "IoT-23 primary dataset"),
    ("cic-ids-2017-ood-v1.jsonl", "cic_ood", "CIC-IDS-2017 OOD dataset"),
    ("unsw-nb15-ood-v1.jsonl", "unsw_ood", "UNSW-NB15 OOD dataset"),
]

for filename, split_name, description in e1_datasets:
    dataset_path = e1_data_dir / filename
    if not dataset_path.exists():
        print(f"⚠️  Skipping {filename} (not found)")
        continue

    print(f"📤 Pushing {filename} → {E1_REPO} (split: {split_name})")
    print(f"   Description: {description}")

    try:
        dataset = load_dataset("json", data_files=str(dataset_path), split="train")
        dataset.push_to_hub(
            E1_REPO,
            split=split_name,
            token=os.environ["HF_TOKEN"],
            private=True,
        )
        print(f"   ✅ Pushed {len(dataset)} examples")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

    print()

# E2 datasets
print("=" * 60)
print("Pushing E2 (Config Verification) datasets...")
print("=" * 60)

e2_data_dir = Path("environments/sv-env-config-verification/data")
e2_datasets = [
    ("k8s-labeled-v1.jsonl", "k8s", "Kubernetes configs"),
    ("terraform-labeled-v1.jsonl", "terraform", "Terraform configs"),
]

for filename, split_name, description in e2_datasets:
    dataset_path = e2_data_dir / filename
    if not dataset_path.exists():
        print(f"⚠️  Skipping {filename} (not found)")
        continue

    print(f"📤 Pushing {filename} → {E2_REPO} (split: {split_name})")
    print(f"   Description: {description}")

    try:
        dataset = load_dataset("json", data_files=str(dataset_path), split="train")
        dataset.push_to_hub(
            E2_REPO,
            split=split_name,
            token=os.environ["HF_TOKEN"],
            private=True,
        )
        print(f"   ✅ Pushed {len(dataset)} examples")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

    print()

print("=" * 60)
print("✅ Dataset push complete!")
print("=" * 60)
print()
print("Next steps:")
print("1. Verify uploads at:")
print(f"   - https://huggingface.co/datasets/{E1_REPO}")
print(f"   - https://huggingface.co/datasets/{E2_REPO}")
print()
print("2. Test loading from Hub:")
print(f'   export E1_HF_REPO={E1_REPO}')
print(f'   export E2_HF_REPO={E2_REPO}')
print('   uv run python -c "from sv_env_network_logs import load_environment; ')
print('   env = load_environment(dataset_source=\\'hub\\', max_examples=10); ')
print('   print(f\\'Loaded {len(env.dataset)} examples\\')"')
```

Make it executable and run:

```bash
chmod +x scripts/push_user_datasets.py
uv run python scripts/push_user_datasets.py
```

Expected output:
```
Pushing datasets to:
  E1: your-org/security-verifiers-e1-private
  E2: your-org/security-verifiers-e2-private

============================================================
Pushing E1 (Network Logs) datasets...
============================================================
📤 Pushing iot23-train-dev-test-v1.jsonl → your-org/security-verifiers-e1-private (split: train)
   Description: IoT-23 primary dataset
   ✅ Pushed 1800 examples

📤 Pushing cic-ids-2017-ood-v1.jsonl → your-org/security-verifiers-e1-private (split: cic_ood)
   Description: CIC-IDS-2017 OOD dataset
   ✅ Pushed 600 examples

...
```

### Step 6: Verify Datasets on HuggingFace

1. **Visit your E1 repository**:
   - URL: `https://huggingface.co/datasets/your-org/security-verifiers-e1-private`
   - Check that splits appear: `train`, `cic_ood`, `unsw_ood`

2. **Visit your E2 repository**:
   - URL: `https://huggingface.co/datasets/your-org/security-verifiers-e2-private`
   - Check that splits appear: `k8s`, `terraform`

3. **Preview data** in the Dataset Viewer (may take a few minutes to load)

### Step 7: Enable Gated Access (Recommended)

To maintain benchmark integrity and prevent training contamination, enable **gated access** on your HuggingFace repositories.

#### Why Use Gated Access?

- ✅ **Prevents training contamination**: Ensures datasets are evaluation-only
- ✅ **Track access**: Know who is using your datasets
- ✅ **Enforce terms**: Require users to agree to evaluation-only license
- ✅ **Manual approval**: Review each access request

#### How to Enable Gating

1. **Go to your E1 repository settings**:
   - Visit `https://huggingface.co/datasets/your-org/security-verifiers-e1-private`
   - Click **Settings** → **Gated access**
   - Enable **"Require users to request access"**
   - Choose **"Manual approval"** mode
   - Save settings

2. **Repeat for E2 repository**:
   - Visit `https://huggingface.co/datasets/your-org/security-verifiers-e2-private`
   - Follow same steps

3. **Add gated dataset card** (pre-made templates available):
   ```bash
   # Clone your HF repo locally (if not already cloned)
   git clone https://huggingface.co/datasets/your-org/security-verifiers-e1-private

   # Copy gated README template
   cp scripts/hf/templates/e1_readme_gated.md security-verifiers-e1-private/README.md

   # Commit and push
   cd security-verifiers-e1-private
   git add README.md
   git commit -m "Add gated access configuration and eval-only license"
   git push

   # Repeat for E2
   git clone https://huggingface.co/datasets/your-org/security-verifiers-e2-private
   cp scripts/hf/templates/e2_readme_gated.md security-verifiers-e2-private/README.md
   cd security-verifiers-e2-private
   git add README.md
   git commit -m "Add gated access configuration and eval-only license"
   git push
   ```

4. **Dataset card includes**:
   - Gating YAML configuration (request form)
   - Evaluation-only license terms
   - Access instructions for users
   - Dataset documentation

5. **Managing access requests**:
   - You'll receive email notifications for new requests
   - Review requests at **Settings** → **Access requests**
   - Approve/deny based on evaluation-only usage
   - Users will see clear error messages if not approved

#### What Users See Without Access

When users try to load your gated dataset without approval, they'll see:

```
Hugging Face gated dataset 'your-org/security-verifiers-e1' requires approved access.

To fix this:
1. Visit the dataset page: https://huggingface.co/datasets/your-org/security-verifiers-e1
2. Click 'Request access' and wait for manual approval
3. Once approved, ensure HF_TOKEN is set:
   - Add to .env file: HF_TOKEN=hf_your_token_here
   - Or export it: export HF_TOKEN=hf_your_token_here
4. Retry your command

Alternative: Build datasets locally with 'make data-e1' or 'make data-e2-local'
```

This provides clear guidance for requesting access while maintaining control over who uses your datasets.

### Step 8: Test Loading from HuggingFace

Create a test script:

```python
# test_hub_loading.py
import os

# Set your repositories
os.environ["HF_TOKEN"] = "hf_your_token_here"
os.environ["E1_HF_REPO"] = "your-org/security-verifiers-e1-private"
os.environ["E2_HF_REPO"] = "your-org/security-verifiers-e2-private"

# Test E1
print("Testing E1 (Network Logs)...")
from sv_env_network_logs import load_environment as load_e1

env_e1 = load_e1(
    dataset_name="iot23-train-dev-test-v1.jsonl",
    dataset_source="hub",
    max_examples=10
)
print(f"✅ E1: Loaded {len(env_e1.dataset)} examples")
print(f"   First example keys: {list(env_e1.dataset[0].keys())}")

# Test E2
print("\nTesting E2 (Config Verification)...")
from sv_env_config_verification import load_environment as load_e2

env_e2 = load_e2(
    dataset_name="k8s-labeled-v1.jsonl",
    dataset_source="hub",
    max_examples=10
)
print(f"✅ E2: Loaded {len(env_e2.dataset)} examples")
print(f"   First example keys: {list(env_e2.dataset[0].keys())}")

print("\n✅ All tests passed! Your datasets are working correctly.")
```

Run the test:

```bash
uv run python test_hub_loading.py
```

## Using Your Datasets After Deployment

### In Python Code

```python
import os
import verifiers as vf

# Configure to use your repositories
os.environ["HF_TOKEN"] = "hf_your_token_here"
os.environ["E1_HF_REPO"] = "your-org/security-verifiers-e1-private"
os.environ["E2_HF_REPO"] = "your-org/security-verifiers-e2-private"

# Load E1 from Hub
env = vf.load_environment(
    "your-org/sv-env-network-logs",
    dataset_source="hub",
    max_examples=100
)
```

### With vf-eval

```bash
# Set environment variables
export HF_TOKEN=hf_your_token_here
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private

# Run evaluation
vf-eval your-org/sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 10
```

### Sharing with Collaborators

To give others access to your datasets:

1. Go to your HuggingFace dataset repository
2. Click "Settings" → "Permissions"
3. Add collaborators by username
4. Share the `HF_TOKEN` and repository names with them

## Troubleshooting

### Error: HF_TOKEN not found

**Solution**: Set `HF_TOKEN` in `.env` file or export it:
```bash
export HF_TOKEN=hf_your_token_here
```

### Error: Permission denied

**Solution**: Verify your token has **write** permissions:
1. Go to https://huggingface.co/settings/tokens
2. Check token type is "Write"
3. Regenerate token if needed

### Error: Dataset already exists

**Solution**: The push operation will overwrite existing splits. This is expected and safe.

### Warning: Dataset not found locally

**Solution**: Build datasets first:
```bash
make data-e1 data-e1-ood       # For E1
make data-e2-local              # For E2
```

## Best Practices

1. **Keep datasets private**: Prevents training contamination
2. **Version your datasets**: Use split names like `train_v2`, `train_v3`
3. **Document your data**: Add a README to your HuggingFace repos
4. **Test before deploying**: Verify Hub loading works before deploying environments
5. **Backup locally**: Keep local copies of datasets
6. **Monitor access**: Regularly review who has access to your repositories

## Next Steps

After pushing your datasets:

1. ✅ Test loading from Hub (Step 7 above)
2. 📦 Deploy environments to Prime Intellect Hub ([guide](hub-deployment.md))
3. 🧪 Run evaluations with `vf-eval`
4. 📊 Share with collaborators
5. 🔄 Update datasets as needed

## Additional Resources

- [Hub Deployment Guide](hub-deployment.md) - Complete deployment documentation
- [HuggingFace Datasets](https://huggingface.co/docs/datasets) - Official documentation
- [Prime Intellect Docs](https://docs.primeintellect.ai/) - Environments Hub guide
- [Security Verifiers README](../README.md) - Project overview

## Getting Help

Need assistance?

- **Dataset issues**: File an issue at https://github.com/intertwine/security-verifiers/issues
- **HuggingFace help**: https://huggingface.co/docs/hub
- **Prime Intellect support**: Contact via their support channels

---

You're now ready to build and share Security Verifiers datasets! 🚀
