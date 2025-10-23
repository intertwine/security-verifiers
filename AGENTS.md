# AGENTS.md

Guidelines for agents working on the Security Verifiers repository.

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
make build              # build wheels for all envs
make build-env E=name   # build one env
make deploy E=name      # build + push to Environments Hub (requires prime login)

# Reproducible evals (artifacts in outputs/evals/...)
# Supports OpenAI models (gpt-*) and 200+ non-OpenAI models via OpenRouter
# Model names auto-resolved via scripts/model_router.py (fuzzy matching + live API + 24h cache)
make eval-e1 MODELS="gpt-4.1-mini,qwen3-14b" N=10  # "qwen3-14b" → "qwen/qwen3-14b" automatically
make eval-e2 MODELS="gpt-4o-mini,llama-3.1-8b" N=2 INCLUDE_TOOLS=true  # Multi-turn eval with tool calling

# Dataset selection (E1: HF datasets or local .jsonl; E2: locally-built datasets)
make eval-e1 MODELS="gpt-4o-mini" N=1800 DATASET="iot23-train-dev-test-v1.jsonl"  # E1 local dataset
make eval-e2 MODELS="gpt-4o-mini" N=50 DATASET="k8s-labeled-v1.jsonl"  # E2 k8s only
make eval-e2 MODELS="gpt-4o-mini" N=10 DATASET="combined"  # E2 both k8s + terraform (default)

# Early failure detection (prevents wasted API costs on misconfigured models)
make eval-e1 MODELS="gpt-4.1-mini" N=100 MAX_CONSECUTIVE_ERRORS=5  # Stop after 5 consecutive errors
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
  - HF_TOKEN (optional for dataset downloads; required for HF push operations)
  - WANDB_API_KEY (required for Weave logging)
  - MAX_CONSECUTIVE_ERRORS (optional, default: 3; set to 0 to disable early stopping)
- HF push scripts (export_metadata_flat.py, push_canonical_with_features.py) automatically load HF_TOKEN from .env using python-dotenv

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
    - `__init__.py` glues these into a Verifiers ToolEnv; tools=[run_kubelinter, run_semgrep, run_opa] (toggle with include_tools)
    - Tests pin behavior and check against golden oracles in dataset/oracle; tool versions pinned in ci/versions.txt
  - E3-E6 (WIP): Skeletons provide dataset/parsers/rubrics and tool hooks; see each env's README.

- Shared toolbox (sv_shared/): Common components used across envs

  - parsers.py: JsonClassificationParser for strict JSON outputs with confidence
  - rewards.py: reward_accuracy, reward_calibration, reward_asymmetric_cost
  - rollout_logging.py: RolloutLogger with optional Weave/W&B backends; enable via build_rollout_logger({...}) and pass logger=... to load_environment

- Reproducible evals & artifacts

  - scripts/eval_network_logs.py, scripts/eval_config_verification.py, scripts/eval_config_verification_singleturn.py write run metadata + per-example results under outputs/evals/sv-env-{name}--{model}/{run_id}/{metadata.json,results.jsonl}
  - All evaluation scripts support early stopping via --max-consecutive-errors (default: 3) to prevent wasted API costs on misconfigured models
  - E2 uses multi-turn evaluation by default, enabling models to call tools (kube-linter, semgrep, OPA) and typically improving rewards significantly compared to tool-free runs
  - scripts/model_router.py provides robust model name resolution: (1) fetches live models from OpenRouter API with 24h caching, (2) fuzzy-matches shorthand names (e.g., qwen3-14b → qwen/qwen3-14b), (3) falls back to hardcoded mappings when offline, (4) supports any OpenRouter model without code changes

- CI
  - .github/workflows/ci.yml installs uv, pins kube-linter version (from E2 ci/versions.txt), runs ruff + pytest (+coverage), and builds wheels on tag/workflow-dispatch.

## Notes for agents

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

## Coding practices

- Use sv_shared components where applicable.
- Include type hints and docstrings for public functions.
- Normalize reward components to [0.0, 1.0].
- Do not commit secrets or API keys. Keep commits focused and descriptive.
- For E2 work, rely on tool adapters and pinned versions in environments/sv-env-config-verification/.../ci/versions.txt (avoid ad hoc heuristics).

## References

- README.md - repo overview and reproducible evals
- PRD.md - environment specifications and reward contracts
- EXECUTIVE_SUMMARY.md - suite-level intent and shared toolbox
- docs/logging-guide.md - comprehensive logging documentation with examples
- CLAUDE.md - Claude Code-specific guidance
- WARP.md - Warp-specific commands
- AGENTS.md - this file
- .github/workflows/ci.yml - CI steps
