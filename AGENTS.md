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
make test-env E=name    # E=network-logs | config-verification | code-vulnerability | phishing-detection | redteam-attack | redteam-defense
# Run a single test (example)
uv run pytest environments/sv-env-network-logs/sv_env_network_logs_test.py::TestNetworkLogParser::test_extracts_label_and_confidence -q

# Build & deploy
make build              # build wheels for all envs
make build-env E=name   # build one env
make deploy E=name      # build + push to Environments Hub (requires prime login)

# Reproducible evals (artifacts in outputs/evals/...)
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini" N=10
make eval-e2 MODELS="gpt-4o-mini" N=2 INCLUDE_TOOLS=true  # Multi-turn eval with tool calling

# Utilities
make pre-commit         # install + run hooks
make info               # repo/environment status
make clean-outputs*     # clean outputs; variants documented in WARP.md
```

## Environment configuration

- cp .env.example .env
- set -a && source .env && set +a
- OPENAI_API_KEY required for OpenAI-compatible endpoints; HF_TOKEN optional for datasets.

## Architecture highlights (be productive fast)

- Environments are installable packages under environments/\* with pyproject entry points under [project.entry-points."verifiers.environments"]. Each exports load_environment(...), a parser, and a rubric with weighted rewards.
- E2 (sv-env-config-verification) pipeline:
  - adapters/{kubelinter_adapter.py, opa_adapter.py, semgrep_adapter.py} → ToolFinding
  - mapping.py → normalize_findings(...) → Violation → to_prd_schema(...)
  - schema.py → pydantic-validated model output (violations/patch/confidence)
  - patching.py → unified-diff/JSON-patch application and re-scan support
  - reward.py → severity-weighted detection (precision/recall/F1) + patch delta; exposed via reward_config_auditing
  - sv_env_config_verification.py wires ToolEnv; tools=[run_kubelinter, run_semgrep, run_opa] (toggle with include_tools)
  - Golden oracles in dataset/oracle; versions pinned in ci/versions.txt
  - Multi-turn eval: Models achieve ~0.93 reward with tools vs ~0.62 without
- Shared toolbox (sv_shared/): parsers.py (JsonClassificationParser), rewards.py (accuracy, calibration, asymmetric cost), rollout_logging.py (RolloutLogger; enable with build_rollout_logger({...})).

## Reproducible evaluations & artifacts

- scripts/eval_network_logs.py and scripts/eval_config_verification.py write:
  - outputs/evals/sv-env-{name}--{model}/{run_id}/{metadata.json,results.jsonl}
  - E2 now uses multi-turn evaluation by default, enabling models to call tools (kube-linter, semgrep, OPA)

## Required checks (per change)

- make check (or make lint && make format && make test)
- make pre-commit (first time: installs hooks; subsequent runs as needed)
- Update relevant READMEs/CLAUDE.md/WARP.md if behavior changes

## Coding practices

- Use sv_shared components where applicable.
- Include type hints and docstrings for public functions.
- Normalize reward components to [0.0, 1.0].

## Workflow notes

- Prefer Makefile targets over raw commands; consult make help and make info.
- Do not commit secrets or API keys. Keep commits focused and descriptive.
- For E2 work, rely on tool adapters and pinned versions in environments/sv-env-config-verification/.../ci/versions.txt (avoid ad hoc heuristics).
