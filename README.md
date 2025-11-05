# Open Security Verifiers

[![CI](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml/badge.svg)](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An integrated suite of composable security and alignment RL environments for Prime Intellect's Environments Hub. This project implements verifiable, executable rewards for training and evaluating AI systems on critical security tasks.

## Vision & Approach

Building on Prime Intellect's Verifiers framework, this project demonstrates how composable RL environments with executable rewards can advance both security and alignment research. Our environments share schemas, tools, and evaluation methods so skills transfer across tasks.

See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for the high-level vision and [PRD.md](PRD.md) for detailed specifications.

## Environment Suite

### Production-Ready

- **`sv-env-network-logs`**: Network log anomaly detection with calibration and abstention using shared parsers and reward helpers
- **`sv-env-config-verification`**: Tool-grounded configuration auditing using OPA/Rego, KubeLinter, and Semgrep with patch-aware rewards

### Alpha / Preview Releases

- **`sv-env-phishing-detection`**: Phishing detection with evidence-seeking and calibrated abstention
- **`sv-env-code-vulnerability`**: Vulnerability repair with patch-and-test loops
- **`sv-env-redteam-attack`**: Red-team attack simulator for eliciting unsafe outputs
- **`sv-env-redteam-defense`**: Adversarial alignment defender balancing helpfulness and harmlessness ([docs](docs/sv-env-redteam-defense.md))

## Prime Intellect Environments Hub

Security Verifiers environments are fully compatible with [Prime Intellect's Environments Hub](https://app.primeintellect.ai/dashboard/environments). Deploy and use environments with flexible dataset loading strategies.

### Quick Start (Hub Deployment)

```bash
# Build and deploy environment
make hub-deploy E=network-logs

# Use with vf-eval
vf-eval your-org/sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 10
```

### Dataset Loading Strategies

Environments support **multi-tiered dataset loading** for maximum flexibility:

1. **Local datasets** (built with `make data-e1` or `make data-e2-local`)
2. **HuggingFace Hub** (with `HF_TOKEN` authentication)
3. **Synthetic fixtures** (for testing without data dependencies)

```python
import verifiers as vf

# Auto mode (default): Try local → hub → synthetic
env = vf.load_environment("sv-env-network-logs")

# Explicit modes
env = vf.load_environment("sv-env-network-logs", dataset_source="local")
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

### Using Your Own HuggingFace Datasets

Push datasets to your own HuggingFace repositories for full Hub deployment:

```bash
# 1. Build datasets locally
make data-e1 data-e1-ood
make clone-e2-sources && make data-e2-local

# 2. Set environment variables
export HF_TOKEN=hf_your_token_here
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private

# 3. Push to your repositories
make hub-push-datasets

# 4. Test loading
make hub-test-datasets
```

**See [docs/hub-deployment.md](docs/hub-deployment.md) for complete deployment guide**
**See [docs/user-dataset-guide.md](docs/user-dataset-guide.md) for dataset management**

## Repository Structure

- **`environments/`**: Six RL environment packages (each independently installable)
- **`sv_shared/`**: Shared parsers, reward components, and utilities
- **`docs/`**: Research notes and application materials
- **`EXECUTIVE_SUMMARY.md`**: High-level project overview
- **`PRD.md`**: Detailed product requirements and specifications

## Getting Started

### Dataset Access

#### ⚠️ Important: Training Contamination Prevention

To protect evaluation integrity, production datasets are:

- **NOT included in this repository**
- **Hosted privately on HuggingFace Hub** with **manual gated access**
- Require **access approval** for evaluation-only use (no training/fine-tuning)
- Only **demo fixtures** (5 small samples) are committed for quick testing
- **Test fixtures** are generated on-demand for CI

**Public Metadata (Browse & Request Access):**

View sampling metadata and request access to full datasets:

- **E1 (Network Logs)**: <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata>
- **E2 (Config Verification)**: <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata>

Each repo includes:

- Sampling metadata showing how datasets were built
- Model cards explaining why datasets are private
- Instructions for requesting access via [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)

**Metadata Schema:** All HuggingFace metadata splits use a standardized flat schema for stable dataset viewer rendering. Structured details are JSON-encoded in the `payload_json` field for easy parsing while maintaining a consistent tabular display.

**For Approved Researchers:**

If you have been granted access to the private datasets:

```bash
# Set your HuggingFace token
export HF_TOKEN=your_token_here

# Download datasets from HuggingFace
# (Instructions provided after access approval)
```

**For Contributors:**

If you need to build datasets locally:

**E1 (Network Logs):**

```bash
# Build production datasets (not committed)
make data-e1            # IoT-23 primary (1800 samples)
make data-e1-ood        # CIC-IDS-2017 + UNSW-NB15 OOD (600 each)
make data-all           # Build all E1 datasets

# Build test fixtures (generated on-demand for CI)
make data-e1-test       # Small test datasets (~20-30 samples)
```

**E2 (Config Verification):**

```bash
# Clone source repositories (one-time setup)
make clone-e2-sources   # Clones K8s/Terraform repos to scripts/data/sources/

# Build production datasets (not committed)
make data-e2-local      # From cloned sources

# Build test fixtures (generated on-demand for CI)
make data-e2-test       # Small test datasets for smoke tests

# Or build from custom paths
make data-e2 K8S_ROOT=/path/to/k8s TF_ROOT=/path/to/terraform
```

**Upload to HuggingFace** (maintainers only):

```bash
# Set HF_TOKEN in .env file (recommended)
# HF_TOKEN=your_token_here

# Or export it as environment variable
export HF_TOKEN=your_token_here

# Validate canonical splits before any push
make validate-data

# Push PUBLIC metadata (flat schema for Dataset Viewer)
make hf-e1-push HF_ORG=intertwine-ai
make hf-e2-push HF_ORG=intertwine-ai

# Push PRIVATE canonical splits with explicit HF Features
make hf-e1p-push-canonical HF_ORG=intertwine-ai
make hf-e2p-push-canonical HF_ORG=intertwine-ai

# Or push all metadata at once (public + private repos)
make hf-push-all HF_ORG=intertwine-ai
```

**Public vs Private Datasets:**

- **Public**: Flat metadata schema for HF Dataset Viewer compatibility (sampling, tools, provenance)
- **Private**: Canonical training splits with explicit Features for consistent nested rendering

**Schema Enforcement:**

- Pydantic validators ensure schema consistency before any push
- Explicit HuggingFace Features for stable Dataset Viewer rendering
- Separate workflows for metadata (public) vs canonical data (private)

Datasets are written to `environments/sv-env-{name}/data/` with reproducibility metadata in `sampling-*.json` files.

### Reproducible evaluations

The evaluation scripts support both OpenAI models and 200+ non-OpenAI models via [OpenRouter](https://openrouter.ai):

- **OpenAI models** (gpt-_, o1-_): Use `OPENAI_API_KEY`
- **Non-OpenAI models** (qwen-2.5-7b, llama-3.1-8b, claude-3.5-sonnet, etc.): Use `OPENROUTER_API_KEY`
  - **Auto-discovery**: Model names are automatically resolved using OpenRouter's live model list
  - **Fuzzy matching**: Shorthand names like `qwen3-14b` automatically map to `qwen/qwen3-14b`
  - **Offline fallback**: Cached model list (24h) + hardcoded mappings ensure offline reliability

**E1 (network-logs):**

```bash
# Build datasets first (one-time setup)
make data-e1        # Build primary IoT-23 dataset (N=1800)
make data-e1-ood    # Build OOD datasets (CIC-IDS-2017, UNSW-NB15, N=600 each)

# Run evaluations with locally-built datasets
make eval-e1 MODELS="gpt-5-mini,gpt-5-mini" N=10  # Uses default: iot23-train-dev-test-v1.jsonl

# Mix of OpenAI and non-OpenAI models (requires both API keys)
make eval-e1 MODELS="gpt-5-mini,qwen-2.5-7b,llama-3.1-8b" N=100

# Select specific dataset
make eval-e1 MODELS="gpt-5-mini" N=1800 DATASET="iot23-train-dev-test-v1.jsonl"  # Primary
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="cic-ids-2017-ood-v1.jsonl"       # OOD
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="unsw-nb15-ood-v1.jsonl"          # OOD
```

Artifacts: `outputs/evals/sv-env-network-logs--{model}/<run_id>/{metadata.json,results.jsonl}`

**E2 (config-verification):**

```bash
# Build datasets first (one-time setup, requires source repos)
make clone-e2-sources  # Clone K8s/Terraform repos to scripts/data/sources/
make data-e2-local     # Build E2 datasets (N=444 K8s + N=115 Terraform)

# Run evaluations with locally-built datasets
make eval-e2 MODELS="gpt-5-mini,qwen-2.5-7b" N=2 INCLUDE_TOOLS=true  # Default: combined

# Select specific dataset
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="k8s-labeled-v1.jsonl"        # K8s only
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="terraform-labeled-v1.jsonl"  # Terraform only
make eval-e2 MODELS="gpt-5-mini" N=2 DATASET="builtin"                      # Test fixtures
```

Artifacts: `outputs/evals/sv-env-config-verification--{model}/<run_id>/{metadata.json,results.jsonl}`

**Dataset Selection:**

Both E1 and E2 require locally-built datasets and track which dataset was used in `metadata.json`:

- **E1**: Local `.jsonl` files built with `make data-e1` (relative to `env/data/` or absolute paths)
  - `iot23-train-dev-test-v1.jsonl` (N=1800, default)
  - `cic-ids-2017-ood-v1.jsonl` (N=600, OOD)
  - `unsw-nb15-ood-v1.jsonl` (N=600, OOD)
- **E2**: Local `.jsonl` files built with `make data-e2-local`
  - `combined` (N=559, default - both K8s and Terraform)
  - `k8s-labeled-v1.jsonl` (N=444)
  - `terraform-labeled-v1.jsonl` (N=115)
  - `builtin` (test fixtures)

**Model Name Resolution (Automatic):**

The evaluation scripts use [scripts/model_router.py](scripts/model_router.py) for robust model routing:

1. **Live discovery**: Fetches available models from OpenRouter API (cached 24h)
2. **Fuzzy matching**: Shorthand names auto-resolve (e.g., `qwen3-14b` → `qwen/qwen3-14b`)
3. **Offline fallback**: Works without network via cached + hardcoded mappings
4. **Future-proof**: New OpenRouter models work automatically without code changes

**Examples:**

- `qwen3-14b` → `qwen/qwen3-14b` (auto-discovered from API)
- `llama-3.1-8b` → `meta-llama/llama-3.1-8b-instruct` (hardcoded fallback)
- `qwen/qwen3-14b` → `qwen/qwen3-14b` (full paths work as-is)

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli) (for Hub deployment)
- `make` (usually pre-installed on Unix systems)

### Quick Setup

The easiest way to get started is using the Makefile:

```bash
# Complete one-command setup
make setup

# Activate the virtual environment
source .venv/bin/activate
```

This will create a Python 3.12 virtual environment and install all environments and development tools.

### Environment Configuration

Before using any of the security verification environments, you need to set up your API keys:

1. **Copy the example environment file**:

   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to the `.env` file**:

   ```bash
   # Required for OpenAI models (gpt-*, o1-*): OpenAI API Key
   OPENAI_API_KEY=your-openai-api-key-here

   # Required for non-OpenAI models (qwen, llama, claude, etc.): OpenRouter API Key
   # Get your key at: https://openrouter.ai/keys
   OPENROUTER_API_KEY=your-openrouter-api-key-here

   # Required for Weave/W&B logging: Weights & Biases API Key
   # Sign up free at: https://wandb.ai
   # Get your key at: https://wandb.ai/authorize
   WANDB_API_KEY=your-wandb-api-key-here

   # Optional: HuggingFace Token (for dataset access)
   HF_TOKEN=your-huggingface-token-here

   # Optional: Disable Weave if you don't want logging
   # WEAVE_DISABLED=true
   ```

3. **Load environment variables before running commands**:

   ```bash
   # Load environment variables from .env file
   set -a && source .env && set +a
   ```

**Security Note**: The `.env` file is already included in `.gitignore` to prevent accidentally committing your API keys. Never commit actual API keys to version control.

**Note**: Some environments may require additional API keys or external tools. Check individual environment READMEs for specific requirements.

### Manual Setup (Alternative)

If you prefer manual setup or need more control:

```bash
# Create virtual environment
uv venv --python=python3.12
source .venv/bin/activate

# Install all environments
make install

# Install development tools
make install-dev
```

#### Using Make (Recommended)

#### Using uv Directly

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Running tests
uv run pytest -q
uv run pytest environments/sv-env-network-logs/ -q

# Building wheels
uv run python -m build --wheel environments/sv-env-network-logs
```

## Pre-commit Hooks

```bash
# Install and setup pre-commit hooks
make pre-commit

# Or manually
uv run pre-commit install
uv run pre-commit run --all-files
```

## Environment Specifications

| Environment                  | Type                  | Reward Focus                                   | Key Innovation                                   |
| ---------------------------- | --------------------- | ---------------------------------------------- | ------------------------------------------------ |
| `sv-env-network-logs`        | SingleTurnEnv         | Calibration, abstention, asymmetric costs      | Operational SOC metrics over raw accuracy        |
| `sv-env-phishing-detection`  | SingleTurnEnv         | Evidence-seeking, FN penalties                 | URL heuristics with structured evidence          |
| `sv-env-config-verification` | ToolEnv               | Machine-verified fixes with patch verification | OPA/Rego/KubeLinter/Semgrep ground truth         |
| `sv-env-code-vulnerability`  | ToolEnv               | Test-passing, minimal diffs                    | Executable verification loop                     |
| `sv-env-redteam-attack`      | MultiTurnEnv          | Unsafe elicitation success                     | Llama Guard 3 safety scoring                     |
| `sv-env-redteam-defense`     | SingleTurnEnv (alpha) | Helpful/harmless balance                       | Synthetic refusal curriculum & safety heuristics |

## Shared Toolbox

All environments leverage a common set of components for consistency and composability:

- Implemented in **`sv_shared/`** for reuse across environments
- **Strict JSON Schemas**: Enforced output formats with zero reward for violations
- **Executable Verification**: Tests, policy engines, linters prioritized over LLM judges
- **Calibration Rewards**: Bonuses for well-calibrated confidence scores
- **Abstention Support**: Safe "I don't know" options with appropriate rewards
- **Cost-Sensitive Scoring**: Asymmetric penalties reflecting real operational costs

## Rollout Logging & Telemetry

Security Verifiers uses a dual-mode logging system with both automatic and manual options:

### Primary: Weave Auto-tracing (Recommended)

[Weave](https://weave-docs.wandb.ai/guides/integrations/verifiers) automatically traces all Verifiers operations when enabled. This provides comprehensive logging with zero code changes:

```python
# Weave is automatically initialized when environments are imported
# Configure via environment variables:
export WEAVE_AUTO_INIT=true  # Enable auto-tracing (default: true)
export WEAVE_PROJECT=security-verifiers  # Set project name

# Then just use environments normally - all operations are traced!
from sv_env_network_logs import load_environment
env = load_environment()
```

**Configuration Options:**

- `WEAVE_AUTO_INIT`: Enable/disable automatic initialization (default: `true`)
- `WEAVE_PROJECT`: Weave project name (default: `security-verifiers`)
- `WEAVE_DISABLED`: Completely disable Weave (overrides other settings)

### Supplementary: RolloutLogger (Optional)

For custom logging needs beyond automatic tracing, use the `RolloutLogger`:

```python
from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment

# Create a logger with custom configuration
logger = build_rollout_logger({
    "enabled": True,
    "wandb_project": "security-verifiers-rl",
    "weave_project": "security-verifiers",
    "step_filter": lambda event: event.reward < 0.5,  # Only log low rewards
})

# Pass logger to environment
env = load_environment(logger=logger)

# Query logged events locally
reward_dips = logger.find_reward_dips(threshold=0.2)
```

**Features:**

- Custom event filtering and transformation
- Local event buffering for offline analysis
- Query capabilities (e.g., `find_reward_dips()`)
- Integration with both Weave and Weights & Biases

**Learn More:**

- 📖 **[Comprehensive Logging Guide](docs/logging-guide.md)** - Detailed configuration, examples, and best practices
- [Weave Verifiers Integration](https://weave-docs.wandb.ai/guides/integrations/verifiers)
- [Weave Tracing](https://docs.wandb.com/weave/tracing)
- [W&B Logging](https://docs.wandb.ai/guides/track/log)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, style, and workflow details.

## License

This project is released under the [MIT License](LICENSE), compatible with Prime Intellect's Verifiers library.

## Notes

- Some environments are still being implemented iteratively
- Each environment has its own `pyproject.toml` with specific dependencies
- The environments use the [verifiers](https://github.com/primeintellect-ai/verifiers) library for RL training
