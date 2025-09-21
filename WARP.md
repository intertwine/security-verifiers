# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project focus: A composable suite of six security/alignment RL environments using Prime Intellect's Verifiers with executable, programmatic rewards. See EXECUTIVE_SUMMARY.md and PRD.md for specifications. Current status: E1 and E2 are production-ready; E3-E6 are WIP.

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

# Build & deploy
make build              # build wheels for all envs
make build-env E=name   # build one env
make deploy E=name      # build + push to Environments Hub (requires prime login)

# Reproducible evaluations (artifacts go to outputs/evals/...)
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini" N=10
make eval-e2 MODELS="gpt-5-mini,gpt-4.1-mini,gpt-4o-mini" N=2 INCLUDE_TOOLS=true

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

## Big-picture architecture (how to be productive fast)

- Environment packages (environments/\*): Each env is an installable Python package with a pyproject entry point under [project.entry-points."verifiers.environments"]. All envs expose load_environment(...)-> Verifiers Env and declare a parser and a rubric with weighted reward components.

  - E1 (sv-env-network-logs): SingleTurnEnv. Uses sv_shared.JsonClassificationParser and shared rewards: reward_accuracy, reward_calibration, reward_asymmetric_cost. Dataset: IoT-23 via datasets with a synthetic fallback. See environments/sv-env-network-logs/sv_env_network_logs.py and tests.
  - E2 (sv-env-config-verification): ToolEnv. End-to-end, tool-grounded pipeline in sv_env_config_verification/e2_config_auditing/:
    - adapters/{kubelinter_adapter.py, opa_adapter.py, semgrep_adapter.py} normalize tool outputs to ToolFinding
    - mapping.py -> normalize_findings(...) → Violation + to_prd_schema(...)
    - schema.py -> pydantic-validated model output (violations/patch/confidence)
    - patching.py -> unified-diff/JSON-patch application and re-scan support
    - reward.py -> severity-weighted detection (precision/recall/F1) + patch delta; exposed via reward_config_auditing
    - **init**.py glues these into a Verifiers ToolEnv; tools=[run_kubelinter, run_semgrep, run_opa] (toggle with include_tools)
    - Tests pin behavior and check against golden oracles in e2_config_auditing/dataset/oracle; tool versions pinned in e2_config_auditing/ci/versions.txt
  - E3-E6 (WIP): Skeletons provide dataset/parsers/rubrics and tool hooks; see each env's README.

- Shared toolbox (sv_shared/): Common components used across envs

  - parsers.py: JsonClassificationParser for strict JSON outputs with confidence
  - rewards.py: reward_accuracy, reward_calibration, reward_asymmetric_cost
  - rollout_logging.py: RolloutLogger with optional Weave/W&B backends; enable via build_rollout_logger({...}) and pass logger=... to load_environment

- Evaluation scripts & artifacts

  - scripts/eval_network_logs.py, scripts/eval_config_verification.py write run metadata + per-example results under outputs/evals/sv-env-{name}-{model}/{run_id}/{metadata.json,results.jsonl}

- CI

  - .github/workflows/ci.yml installs uv, pins kube-linter version (from E2 ci/versions.txt), runs ruff + pytest (+coverage), and builds wheels on tag/workflow-dispatch.

- Templates
  - templates/ contains minimal stubs (environment_template.py, environment_test_template.py, pyproject_template.toml) to scaffold new env packages aligned with the project conventions.

## Notes and guardrails

- Never run git commit/push from Warp; the user handles all Git operations.
- Prefer Make targets over raw commands; check make help and make info.
- For environment-specific details and examples, see each env's README and README-DEV (where present).

## Key references (read as needed)

- README.md: repo overview, quick start, reproducible evals
- PRD.md: environment specifications and reward contracts
- EXECUTIVE_SUMMARY.md: suite-level intent and shared toolbox
- CLAUDE.md: additional agent-facing guidance (strict schemas, rubric-based rewards, deployment checklist)

—

### Improvements over the previous WARP.md

- Adds concrete, tested targets present in Makefile: eval-e1/eval-e2 (with MODELS, N, INCLUDE_TOOLS), clean-outputs\*, watch, info, ci/cd shortcuts
- Documents single-test invocation with pytest node id
- Captures E2's real tool-grounded architecture (adapters → mapping → schema → patching → reward → ToolEnv) with file references
- Points to scripts/eval\_\* and outputs/ layout for reproducible artifacts
- Documents rollout logging utility and how to enable it
- Aligns phrasing with current repository status (E1/E2 ready; E3-E6 WIP)
- Avoids redundant/general guidelines and omits undiscoverable or non-existent targets

### Acceptance criteria

- The file begins with the exact required prefix
- Commands match existing Makefile targets and work in the current repo
- Architecture section references the actual modules/files and accurately describes E2's pipeline and sv_shared components
- No generic advice; no exhaustive file trees; no duplicated sections
- Preserve "never git commit/push from Warp" reminder
