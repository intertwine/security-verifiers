# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Open Security Verifiers repository.

## Project focus

A composable suite of six security/alignment RL environments using Prime Intellect's Verifiers with executable, programmatic rewards. See EXECUTIVE_SUMMARY.md and PRD.md for specifications. Current status: E1 and E2 are production-ready; E3-E6 are WIP.

## Quick commands (Makefile-backed)

```bash
# One-time setup
make setup
source .venv/bin/activate

# Quality
make check              # lint + format + tests
make lint               # ruff check
make format             # ruff format

# Tests
make test               # all tests
make test-env E=name    # e.g., E=network-logs | config-verification | code-vulnerability | phishing-detection | redteam-attack | redteam-defense
# Run a single test (example)
uv run pytest environments/sv-env-network-logs/sv_env_network_logs_test.py::TestNetworkLogParser::test_extracts_label_and_confidence -q

# Data building - Production (private, not committed; requires .env with HF_TOKEN)
make data-e1            # Build E1 IoT-23 dataset (LIMIT=1800, full mode)
make data-e1-ood        # Build E1 OOD datasets (N=600, CIC+UNSW, full mode)
make clone-e2-sources   # Clone recommended K8s/TF repos to scripts/data/sources/
make data-e2-local      # Build E2 datasets from cloned sources (full mode)
make data-e2 K8S_ROOT=<path> TF_ROOT=<path>  # Build E2 from custom paths (full mode)
make data-all           # Build all E1 production datasets

# HuggingFace dataset management (maintainers only; requires HF_TOKEN in .env)
make validate-data                           # Validate E1 & E2 canonical splits with Pydantic
make hf-e1-push HF_ORG=intertwine-ai        # Push E1 PUBLIC metadata (flat schema)
make hf-e2-push HF_ORG=intertwine-ai        # Push E2 PUBLIC metadata (flat schema)
make hf-e1p-push-canonical HF_ORG=intertwine-ai  # Push E1 PRIVATE canonical with Features
make hf-e2p-push-canonical HF_ORG=intertwine-ai  # Push E2 PRIVATE canonical with Features
make hf-push-all HF_ORG=intertwine-ai       # Push all metadata (public + private)

# Data building - Test fixtures (small, checked in for CI)
make data-e1-test       # Build E1 test fixtures (~20-30 samples)
make data-e2-test       # Build E2 test fixtures (requires clone-e2-sources first)
make data-test-all      # Build all test fixtures

# Build & deploy
make build                         # build wheels for all envs
make build-env E=name              # build one env
make build-utils                   # build security-verifiers-utils wheel
make update-version E=name         # bump patch version (0.0.n) in pyproject.toml
make update-version E=name BUMP=minor  # bump minor version (0.n.0)
make update-version E=name BUMP=major  # bump major version (n.0.0)
make update-utils-version BUMP=patch|minor|major  # bump security-verifiers-utils version
make deploy E=name                 # build + push to Environments Hub (requires prime login, team: intertwine)
make deploy E=name TEAM=your-team  # override team slug for deployment
make hub-deploy E=name             # validate + bump version (patch) + deploy
make hub-deploy E=name BUMP=minor  # validate + bump minor version + deploy
make hub-deploy E=name BUMP=major  # validate + bump major version + deploy
make hub-deploy E=name BUMP=none   # validate + deploy without version bump

# PyPI publishing (security-verifiers-utils)
make pypi-publish-utils-test       # publish to TestPyPI (for testing)
make pypi-publish-utils            # publish to PyPI (production)

# Reproducible evaluations (artifacts go to outputs/evals/...)
# Supports OpenAI models (gpt-*) and 200+ non-OpenAI models via OpenRouter
# Model names auto-resolved via scripts/model_router.py (fuzzy matching + live API + 24h cache)
make eval-e1 MODELS="gpt-5-mini,qwen3-14b" N=10  # "qwen3-14b" → "qwen/qwen3-14b" automatically
make eval-e2 MODELS="gpt-5-mini,llama-3.1-8b" N=2 INCLUDE_TOOLS=true  # Multi-turn eval with tool calling

# Generate E1 (network-logs) evaluation metrics report (Acc, ECE, FN%, FP%, Abstain%)
# Note: Also writes summary.json to each run directory automatically
make report-network-logs                      # Analyze all non-archived runs (auto-timestamped output)
make report-network-logs RUN_IDS="id1 id2"    # Analyze specific run IDs
make report-network-logs OUTPUT="path.json"   # Custom output path

# Dataset selection
# E1 supports: local .jsonl files (relative to env/data/ or absolute paths). Build with 'make data-e1'.
# E2 supports: locally-built datasets from make data-e2-local (k8s, terraform, or combined)
make eval-e1 MODELS="gpt-5-mini" N=1800 DATASET="iot23-train-dev-test-v1.jsonl"  # E1 primary dataset (default)
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="cic-ids-2017-ood-v1.jsonl"  # E1 OOD dataset
make eval-e1 MODELS="gpt-5-mini" N=600 DATASET="unsw-nb15-ood-v1.jsonl"  # E1 OOD dataset
make eval-e2 MODELS="gpt-5-mini" N=10 DATASET="combined"  # E2 both k8s + terraform (default)
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="k8s-labeled-v1.jsonl"  # E2 k8s only
make eval-e2 MODELS="gpt-5-mini" N=50 DATASET="terraform-labeled-v1.jsonl"  # E2 terraform only
make eval-e2 MODELS="gpt-5-mini" N=2 DATASET="builtin"  # E2 test fixtures (for testing)

# Early failure detection (prevents wasted API costs on misconfigured models)
make eval-e1 MODELS="gpt-5-mini" N=100 MAX_CONSECUTIVE_ERRORS=5  # Stop after 5 consecutive errors
make eval-e2 MODELS="invalid-model" N=10 MAX_CONSECUTIVE_ERRORS=0  # Disable early stopping (never stop)

# Shortcuts
make e1  # test E1 (network-logs)
make e2  # test E2 (config-verification)
make e3  # test E3 (code-vulnerability)
make e4  # test E4 (phishing-detection)
make e5  # test E5 (redteam-attack)
make e6  # test E6 (redteam-defense)

# Utilities
make pre-commit         # install + run hooks
make info               # repo/environment status
make clean              # build artifacts and caches
make clean-outputs      # remove outputs/evals (keeps outputs/logs)
make clean-logs         # remove outputs/logs only
make clean-outputs-all  # clear outputs/ (keeps .gitkeep)
# File watch (optional): requires entr; on macOS: brew install entr
make watch

# HuggingFace flat metadata schema (for Dataset Viewer)
make hf-e1-meta     # Build E1 metadata locally
make hf-e2-meta     # Build E2 metadata locally
make hf-e1-push     # Push E1 metadata to PUBLIC repo
make hf-e2-push     # Push E2 metadata to PUBLIC repo
make hf-e1p-push    # Push E1 metadata to PRIVATE repo (meta split only)
make hf-e2p-push    # Push E2 metadata to PRIVATE repo (meta split only)
make hf-push-all    # Push all metadata to all repos

# Pydantic validators & canonical push with Features (PRIVATE repos)
make validate-data            # Validate E1 & E2 splits with Pydantic
make hf-e1p-push-canonical    # Push E1 canonical splits with explicit Features
make hf-e2p-push-canonical    # Push E2 canonical splits with explicit Features
make hf-e1p-push-canonical-dry # Dry run E1 canonical push
make hf-e2p-push-canonical-dry # Dry run E2 canonical push
```

### Manual equivalents (fallback)

```bash
# If not using make
uv venv --python=python3.12 && source .venv/bin/activate
uv run ruff check . --fix && uv run ruff format .
uv run pytest -q
uv run python -m build --wheel environments/sv-env-network-logs
```

## Environment configuration

- Copy and load .env (for API keys/tokens) before evals:
  - cp .env.example .env
  - set -a && source .env && set +a
- Common vars:
  - OPENAI_API_KEY (required for OpenAI models: gpt-*, o1-*)
  - OPENROUTER_API_KEY (required for non-OpenAI models: qwen-2.5-7b, llama-3.1-8b, claude-3.5-sonnet, etc.)
    - Get your key at: https://openrouter.ai/keys
    - Supports 200+ models with unified API
  - HF_TOKEN (optional for dataset downloads; required for HF metadata pushes)
  - WANDB_API_KEY (required for Weave logging)
  - MAX_CONSECUTIVE_ERRORS (optional, default: 3; set to 0 to disable early stopping)
- Evaluation script defaults:
  - E1 (eval_network_logs.py): --max-tokens defaults to 2048 (sufficient for classification tasks)
  - E2 multi-turn (eval_config_verification.py): --max-tokens defaults to 4096 (handles tool interactions)
  - E2 single-turn (eval_config_verification_singleturn.py): --max-tokens defaults to 2048
  - Override via script invocation: `uv run python scripts/eval_network_logs.py --models gpt-5-mini --num-examples 10 --max-tokens 1024`
- HF push scripts (export_metadata_flat.py, push_canonical_with_features.py) automatically load HF_TOKEN from .env using python-dotenv

## Prime Intellect Hub Deployment

All Security Verifiers environments are fully compatible with Prime Intellect's Environments Hub. The repository includes complete infrastructure for:

1. **Multi-tiered dataset loading**: Automatic fallback from local → hub → synthetic
2. **User-configurable HF repos**: Push datasets to your own HuggingFace repositories
3. **Hub validation & deployment**: Automated testing and deployment workflows

### Quick Hub Deployment

```bash
# Validate environment
make hub-validate E=network-logs

# Deploy with validation
make hub-deploy E=network-logs

# Use on Hub
vf-eval your-org/sv-env-network-logs --model gpt-5-mini --num-examples 10
```

### Dataset Management for Hub Users

When deploying to the Hub, users won't have access to intertwine's private datasets. Two options:

**Option 1: Use synthetic datasets (for testing)**

```python
# Environments work without any datasets using synthetic fallback
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

**Option 2: Build and push to user's own HF repos (for production)**

```bash
# Build datasets locally
make data-e1 data-e1-ood
make clone-e2-sources && make data-e2-local

# Configure user's HF repositories
export HF_TOKEN=hf_your_token_here
export E1_HF_REPO=your-org/security-verifiers-e1-private
export E2_HF_REPO=your-org/security-verifiers-e2-private

# Push datasets
make hub-push-datasets

# Test loading
make hub-test-datasets
```

### Dataset Loading Modes

All environments support flexible dataset loading via `dataset_source` parameter:

- `auto` (default): Try local → hub → synthetic
- `local`: Require local JSONL files
- `hub`: Load from HuggingFace (requires HF_TOKEN and E1_HF_REPO/E2_HF_REPO)
- `synthetic`: Use test fixtures

**Examples:**

```python
# Auto mode with fallback
env = vf.load_environment("sv-env-network-logs")

# Explicit Hub loading
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")

# Synthetic for quick testing
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

### Hub Deployment Checklist

Use this checklist when deploying environments to the Hub:

```bash
# 1. Validate environment
make hub-validate E=network-logs

# 2. (Optional) Build and push datasets to your HF repo
make data-e1
export HF_TOKEN=... E1_HF_REPO=...
make hub-push-datasets

# 3. Deploy to Hub
make hub-deploy E=network-logs

# 4. Test deployed environment
vf-eval your-org/sv-env-network-logs --model gpt-5-mini --num-examples 3
```

### Documentation

- **[docs/hub-deployment.md](docs/hub-deployment.md)**: Complete Hub deployment guide
- **[docs/user-dataset-guide.md](docs/user-dataset-guide.md)**: Build and push datasets to your own HF repos
- **Environment READMEs**: E1 and E2 READMEs include Hub usage examples

## Logging Architecture

Security Verifiers uses a dual-mode logging system:

1. **Primary: Weave Auto-tracing** (enabled by default)
   - Automatically traces all Verifiers operations when `weave_init` is imported before `verifiers`
   - Provides comprehensive tracing with zero code changes
   - Configure via environment variables:
     - `WEAVE_AUTO_INIT=true/false` - Enable/disable auto-initialization (default: true)
     - `WEAVE_PROJECT=<name>` - Set project name (default: security-verifiers)
     - `WEAVE_DISABLED=true/false` - Completely disable Weave

2. **Supplementary: RolloutLogger** (optional)
   - Use for custom logging needs beyond automatic tracing
   - Features: event filtering, local buffering, custom metrics
   - Pass `logger=build_rollout_logger(...)` to `load_environment()`

## Big-picture architecture (be productive fast)

- Environment packages (environments/\*): Each env is an installable Python package with a pyproject entry point under [project.entry-points."verifiers.environments"]. All envs expose load_environment(...)-> Verifiers Env and declare a parser and a rubric with weighted reward components.

  - E1 (sv-env-network-logs): SingleTurnEnv. Uses sv_shared.JsonClassificationParser and shared rewards: reward_accuracy, reward_calibration, reward_asymmetric_cost. Dataset: IoT-23 via datasets with a synthetic fallback. See environments/sv-env-network-logs/sv_env_network_logs.py and tests.
  - E2 (sv-env-config-verification): ToolEnv. End-to-end, tool-grounded pipeline with:
    - adapters/{kubelinter_adapter.py, opa_adapter.py, semgrep_adapter.py} normalize tool outputs to ToolFinding
    - mapping.py -> normalize_findings(...) → Violation + to_prd_schema(...)
    - schema.py -> pydantic-validated model output (violations/patch/confidence)
    - patching.py -> unified-diff/JSON-patch application and re-scan support
    - reward.py -> severity-weighted detection (precision/recall/F1) + patch delta; exposed via reward_config_auditing
    - **init**.py glues these into a Verifiers ToolEnv; tools=[run_kubelinter, run_semgrep, run_opa] (toggle with include_tools)
    - Tests pin behavior and check against golden oracles in dataset/oracle; tool versions pinned in ci/versions.txt
  - E3-E6 (WIP): Skeletons provide dataset/parsers/rubrics and tool hooks; see each env's README.

- Shared toolbox (sv_shared/): Common components used across envs

  - parsers.py: JsonClassificationParser for strict JSON outputs with confidence
  - rewards.py: reward_accuracy, reward_calibration, reward_asymmetric_cost
  - rollout_logging.py: RolloutLogger with optional Weave/W&B backends; enable via build_rollout_logger({...}) and pass logger=... to load_environment

- Reproducible evals & artifacts

  - scripts/eval_network_logs.py, scripts/eval_config_verification.py, scripts/eval_config_verification_singleturn.py write run metadata + per-example results under outputs/evals/sv-env-{name}--{model}/{run_id}/{metadata.json,results.jsonl}
  - All evaluation scripts support early stopping via --max-consecutive-errors (default: 3) to prevent wasted API costs
  - scripts/model_router.py: Robust model routing with OpenRouter API auto-discovery, fuzzy matching, and offline fallbacks

- CI
  - .github/workflows/ci.yml installs uv, pins kube-linter version (from E2 ci/versions.txt), runs ruff + pytest (+coverage), and builds wheels on tag/workflow-dispatch.

## Notes for Claude

- Never run git commit/push from the terminal; the user handles Git operations.
- Prefer Make targets over raw commands; check make help and make info.
- Enforce strict JSON schemas; malformed outputs get zero reward.
- Update environment READMEs when you change behavior; keep tests green.

## Deployment checklist (concise)

- [ ] make test-env E=name
- [ ] make lint && make format
- [ ] README updated; pyproject deps correct
- [ ] make build-env E=name
- [ ] make eval E=name (or eval-e1/eval-e2)

## References

- README.md - repo overview and reproducible evals
- PRD.md - environment specifications and reward contracts
- EXECUTIVE_SUMMARY.md - suite-level intent and shared toolbox
- docs/logging-guide.md - comprehensive logging documentation with examples
- CLAUDE.md - this file
- WARP.md - Warp-specific commands (mirrors this guidance)
- .github/workflows/ci.yml - CI steps
