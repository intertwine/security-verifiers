# Prime Intellect Environments Hub Deployment Guide

This guide provides complete instructions for deploying Security Verifiers environments to Prime Intellect's Environments Hub and working with datasets.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Dataset Management](#dataset-management)
  - [Understanding Dataset Loading](#understanding-dataset-loading)
  - [Building Datasets Locally](#building-datasets-locally)
  - [Pushing Datasets to Your Own HuggingFace Repository](#pushing-datasets-to-your-own-huggingface-repository)
  - [Using Datasets from the Hub](#using-datasets-from-the-hub)
- [Building and Deploying Environments](#building-and-deploying-environments)
- [Using Deployed Environments](#using-deployed-environments)
- [Troubleshooting](#troubleshooting)

## Overview

Security Verifiers environments are fully compatible with Prime Intellect's Environments Hub. This guide covers:

1. **Dataset management**: Building datasets locally and optionally pushing to your own HuggingFace repositories
2. **Environment deployment**: Building and deploying environments to the Hub
3. **Using deployed environments**: Running evaluations with `vf-eval` and loading environments in Python

### Key Features

- **Multi-tiered dataset loading**: Automatic fallback from local → Hub → synthetic
- **User-configurable HF repos**: Push datasets to your own HuggingFace repositories
- **Synthetic fixtures**: Test environments without data dependencies
- **Hub compatibility**: Full integration with `vf-eval` and Prime RL training

## Prerequisites

### Required Tools

1. **Python 3.12+**
   ```bash
   python --version
   ```

2. **uv package manager**
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Verify installation
   uv --version
   ```

3. **Prime CLI** (for Hub deployment)
   ```bash
   # Install Prime CLI
   uv tool install prime

   # Verify installation
   prime --version

   # Login to Prime Intellect
   prime login
   ```

### Optional: API Keys

Depending on your workflow, you may need:

- **HF_TOKEN**: HuggingFace API token (for pushing/pulling datasets)
  - Get yours at: https://huggingface.co/settings/tokens
  - Requires `write` permissions for pushing datasets

- **OPENAI_API_KEY**: For running evaluations with OpenAI models
  - Get yours at: https://platform.openai.com/api-keys

- **OPENROUTER_API_KEY**: For 200+ non-OpenAI models (qwen, llama, claude, etc.)
  - Get yours at: https://openrouter.ai/keys

- **WANDB_API_KEY**: For Weave logging during evaluations
  - Get yours at: https://wandb.ai/authorize

## Dataset Management

### Understanding Dataset Loading

Security Verifiers uses a **multi-tiered dataset loading strategy** that automatically tries different sources:

1. **Local JSONL files** (built with `make data-e1` or `make data-e2-local`)
2. **HuggingFace Hub** (with `HF_TOKEN` authentication)
3. **Synthetic fixtures** (for testing without data dependencies)

This means environments work both locally and when deployed to the Hub.

### Dataset Loading Modes

You can control where datasets are loaded from using the `dataset_source` parameter:

```python
import verifiers as vf

# Auto mode (default): Try local → hub → synthetic
env = vf.load_environment("sv-env-network-logs")

# Local only: Fail if local dataset not found
env = vf.load_environment("sv-env-network-logs", dataset_source="local")

# Hub only: Load from HuggingFace (requires HF_TOKEN)
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")

# Synthetic only: Use test fixtures
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

### Building Datasets Locally

Both E1 and E2 environments require datasets to be built before use.

#### E1 (Network Logs)

```bash
# Build primary dataset (IoT-23, N=1800)
make data-e1

# Build OOD datasets (CIC-IDS-2017 and UNSW-NB15, N=600 each)
make data-e1-ood

# Build all E1 datasets
make data-all

# Build test fixtures (small datasets for CI)
make data-e1-test
```

**Output location**: `environments/sv-env-network-logs/data/`

**Datasets created**:
- `iot23-train-dev-test-v1.jsonl` (primary, N=1800)
- `cic-ids-2017-ood-v1.jsonl` (OOD, N=600)
- `unsw-nb15-ood-v1.jsonl` (OOD, N=600)

#### E2 (Config Verification)

```bash
# Step 1: Clone source repositories (one-time setup)
make clone-e2-sources

# Step 2: Build datasets from cloned sources
make data-e2-local

# Build test fixtures (small datasets for CI)
make data-e2-test

# Or build from custom paths
make data-e2 K8S_ROOT=/path/to/k8s TF_ROOT=/path/to/terraform
```

**Output location**: `environments/sv-env-config-verification/data/`

**Datasets created**:
- `k8s-labeled-v1.jsonl` (Kubernetes configs, N=444)
- `terraform-labeled-v1.jsonl` (Terraform configs, N=115)

### Pushing Datasets to Your Own HuggingFace Repository

If you're deploying to the Hub and want users to access datasets, you can push them to your own HuggingFace repository.

#### Step 1: Create HuggingFace Repositories

1. Go to https://huggingface.co/new
2. Create two **private** repositories:
   - `your-org/security-verifiers-e1-private` (for E1 datasets)
   - `your-org/security-verifiers-e2-private` (for E2 datasets)

**Why private?** To prevent training contamination of evaluation datasets.

#### Step 2: Set Your HuggingFace Token

```bash
# Add to .env file
echo "HF_TOKEN=your_huggingface_token_here" >> .env

# Load environment variables
set -a && source .env && set +a
```

#### Step 3: Push Datasets to Your Repositories

You can use the existing push scripts but customize the repository names:

```bash
# Set your organization name
export HF_ORG=your-org

# Push E1 datasets
make hf-e1p-push-canonical HF_ORG=$HF_ORG

# Push E2 datasets
make hf-e2p-push-canonical HF_ORG=$HF_ORG
```

**Or create a custom push script**:

```python
# scripts/push_my_datasets.py
import os
from pathlib import Path
from datasets import load_dataset, Dataset

# Your HuggingFace repositories
E1_REPO = "your-org/security-verifiers-e1-private"
E2_REPO = "your-org/security-verifiers-e2-private"

# Push E1 datasets
e1_data_dir = Path("environments/sv-env-network-logs/data")
for dataset_file, split_name in [
    ("iot23-train-dev-test-v1.jsonl", "train"),
    ("cic-ids-2017-ood-v1.jsonl", "cic_ood"),
    ("unsw-nb15-ood-v1.jsonl", "unsw_ood"),
]:
    dataset_path = e1_data_dir / dataset_file
    if dataset_path.exists():
        dataset = load_dataset("json", data_files=str(dataset_path), split="train")
        dataset.push_to_hub(
            E1_REPO,
            split=split_name,
            token=os.environ["HF_TOKEN"],
            private=True,
        )
        print(f"✓ Pushed {dataset_file} to {E1_REPO} (split: {split_name})")

# Push E2 datasets
e2_data_dir = Path("environments/sv-env-config-verification/data")
for dataset_file, split_name in [
    ("k8s-labeled-v1.jsonl", "k8s"),
    ("terraform-labeled-v1.jsonl", "terraform"),
]:
    dataset_path = e2_data_dir / dataset_file
    if dataset_path.exists():
        dataset = load_dataset("json", data_files=str(dataset_path), split="train")
        dataset.push_to_hub(
            E2_REPO,
            split=split_name,
            token=os.environ["HF_TOKEN"],
            private=True,
        )
        print(f"✓ Pushed {dataset_file} to {E2_REPO} (split: {split_name})")
```

Run the script:

```bash
uv run python scripts/push_my_datasets.py
```

#### Step 4: Configure Environments to Use Your Repositories

Set environment variables to point to your HuggingFace repositories:

```bash
# Add to .env file
echo "E1_HF_REPO=your-org/security-verifiers-e1-private" >> .env
echo "E2_HF_REPO=your-org/security-verifiers-e2-private" >> .env

# Or export directly
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private
```

Now when users load environments with `dataset_source="hub"`, they'll use your repositories!

### Using Datasets from the Hub

Once datasets are pushed to HuggingFace:

```python
import os
import verifiers as vf

# Set HF_TOKEN and custom repo
os.environ["HF_TOKEN"] = "your_token_here"
os.environ["E1_HF_REPO"] = "your-org/security-verifiers-e1-private"

# Load from Hub
env = vf.load_environment(
    "sv-env-network-logs",
    dataset_source="hub",
    max_examples=100
)
```

## Building and Deploying Environments

### Step 1: Build Environment Wheels

```bash
# Build a specific environment
make build-env E=network-logs

# Or build all environments
make build
```

This creates wheel files in `environments/sv-env-{name}/dist/`.

### Step 2: Validate Environment Locally

Before deploying, validate the environment works correctly:

```bash
# Run tests
make test-env E=network-logs

# Lint and format
make lint
make format

# Build and test locally
make build-env E=network-logs
```

### Step 3: Deploy to Prime Intellect Hub

```bash
# Login to Prime Intellect (one-time setup)
prime login

# Deploy environment
make deploy E=network-logs

# Or use hub-deploy target (includes validation)
make hub-deploy E=network-logs
```

The `deploy` target runs:
```bash
cd environments/sv-env-network-logs
prime env push -v PUBLIC
```

### Step 4: Verify Deployment

Check that your environment appears in the Hub:

```bash
# List your deployed environments
prime env list

# Or visit the Hub dashboard
# https://app.primeintellect.ai/dashboard/environments
```

## Using Deployed Environments

### Option 1: Using vf-eval (Recommended for Hub)

```bash
# Set API keys
export OPENAI_API_KEY=your-key-here
export HF_TOKEN=your-hf-token-here  # If using Hub datasets

# Run evaluation with deployed environment
vf-eval your-org/sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 10

# Use synthetic dataset (no HF_TOKEN needed)
vf-eval your-org/sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 3 \
  --dataset synthetic
```

### Option 2: Loading in Python

```python
import os
import verifiers as vf

# Set API keys
os.environ["OPENAI_API_KEY"] = "your-key-here"
os.environ["HF_TOKEN"] = "your-hf-token-here"

# Load deployed environment
env = vf.load_environment(
    "your-org/sv-env-network-logs",
    dataset_source="hub",  # Use Hub datasets
    max_examples=100
)

# Or use synthetic data for testing
env = vf.load_environment(
    "your-org/sv-env-network-logs",
    dataset_source="synthetic",
    max_examples=10
)

# Run a sample
from verifiers.llms import get_llm
llm = get_llm("openai/gpt-5-mini")

result = env.sample(llm)
print(f"Reward: {result.reward}")
```

### Option 3: Custom Evaluation Scripts

The repository includes advanced evaluation scripts with features like:
- Multi-model support (OpenAI + OpenRouter)
- Early stopping on consecutive errors
- Structured artifact logging

```bash
# Use custom evaluation scripts (for research)
make eval-e1 MODELS="gpt-5-mini,qwen-2.5-7b" N=100

# Use vf-eval for Hub compatibility
vf-eval your-org/sv-env-network-logs --model gpt-5-mini --num-examples 100
```

See [Custom Scripts vs vf-eval](#custom-scripts-vs-vf-eval) for comparison.

## Troubleshooting

### Dataset Not Found

**Error**: `Dataset 'iot23-train-dev-test-v1.jsonl' not found`

**Solutions**:
1. Build datasets locally: `make data-e1`
2. Set `HF_TOKEN` to use Hub datasets
3. Use synthetic dataset: `dataset_source="synthetic"`

### HuggingFace Authentication Failed

**Error**: `HF_TOKEN not found in environment`

**Solutions**:
1. Set `HF_TOKEN` in `.env` file
2. Export as environment variable: `export HF_TOKEN=your_token_here`
3. Verify token has `write` permissions (for pushing datasets)

### Environment Not Found on Hub

**Error**: `Environment 'sv-env-network-logs' not found`

**Solutions**:
1. Verify deployment: `prime env list`
2. Use fully qualified name: `your-org/sv-env-network-logs`
3. Check Prime CLI is authenticated: `prime login`

### Dataset Loading from Hub Fails

**Error**: `Failed to load dataset from HuggingFace Hub`

**Solutions**:
1. Verify `HF_TOKEN` is set and valid
2. Check repository name: `echo $E1_HF_REPO`
3. Verify access to the repository (private repos require token)
4. Try loading locally first: `dataset_source="local"`

### Build Failures

**Error**: `ModuleNotFoundError: No module named 'sv_shared'`

**Solutions**:
1. Install in development mode: `uv pip install -e sv_shared`
2. Run from repository root: `cd /path/to/security-verifiers`
3. Verify virtual environment: `source .venv/bin/activate`

### vf-eval Command Not Found

**Error**: `vf-eval: command not found`

**Solutions**:
1. Install verifiers: `uv pip install verifiers`
2. Or use full path: `uv run vf-eval ...`
3. Verify environment: `which vf-eval`

## Custom Scripts vs vf-eval

The repository provides two evaluation workflows:

### Custom Scripts (`scripts/eval_*.py`)

**Advantages**:
- Multi-model routing (OpenAI + OpenRouter)
- Fuzzy model name matching
- Early stopping on errors
- Rich artifact logging
- Git provenance tracking

**Use cases**:
- Research evaluations
- Benchmarking multiple models
- Cost-sensitive experiments

**Example**:
```bash
make eval-e1 MODELS="gpt-5-mini,qwen-2.5-7b" N=100
```

### vf-eval Command

**Advantages**:
- Standard Prime Intellect interface
- Works with Hub-deployed environments
- Simpler command line
- RL training integration

**Use cases**:
- Hub-based evaluations
- Quick environment testing
- Standard benchmarks

**Example**:
```bash
vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 10
```

**Recommendation**: Use custom scripts for research, vf-eval for Hub compatibility.

## Additional Resources

- [Prime Intellect Verifiers Library](https://github.com/PrimeIntellect-ai/verifiers)
- [Prime Intellect Documentation](https://docs.primeintellect.ai/)
- [Environments Hub Dashboard](https://app.primeintellect.ai/dashboard/environments)
- [HuggingFace Datasets Documentation](https://huggingface.co/docs/datasets)
- [Security Verifiers README](../README.md)
- [Security Verifiers PRD](../PRD.md)

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review environment-specific READMEs
3. File an issue: https://github.com/intertwine/security-verifiers/issues
4. Contact Prime Intellect support

## Summary

You now have everything needed to:

✅ Build datasets locally
✅ Push datasets to your own HuggingFace repositories
✅ Deploy environments to Prime Intellect Hub
✅ Run evaluations with `vf-eval`
✅ Load environments in Python
✅ Configure custom dataset sources

Happy deploying! 🚀
