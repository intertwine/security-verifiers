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
make upload-datasets HF_ORG=intertwine-ai  # Build and upload datasets to HuggingFace (maintainers only)

# Data building - Test fixtures (small, checked in for CI)
make data-e1-test       # Build E1 test fixtures (~20-30 samples)
make data-e2-test       # Build E2 test fixtures (requires clone-e2-sources first)
make data-test-all      # Build all test fixtures

# Build & deploy
make build              # build wheels for all envs
make build-env E=name   # build one env
make deploy E=name      # build + push to Environments Hub (requires prime login)

# Reproducible evaluations (artifacts go to outputs/evals/...)
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini" N=10
make eval-e2 MODELS="gpt-4o-mini" N=2 INCLUDE_TOOLS=true  # Multi-turn eval with tool calling

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
- Common vars: OPENAI_API_KEY (required for OpenAI-compatible endpoints), HF_TOKEN (optional for datasets)

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

  - scripts/eval_network_logs.py, scripts/eval_config_verification.py write run metadata + per-example results under outputs/evals/sv-env-{name}--{model}/{run_id}/{metadata.json,results.jsonl}

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
