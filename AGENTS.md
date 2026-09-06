# AGENTS.md

Default repo-wide instructions for coding agents working in this repository.

## Purpose and status

Open Security Verifiers: a composable suite of six security/alignment RL environments built on Prime Intellect's Verifiers, with executable, programmatic rewards. Status and the release boundary live in `SVBENCH_STATUS.md` — SV-Bench v0.1 is E1 and E2 only; E3–E6 stay alpha/beta until that proof is complete. Roadmap: `plans/ROADMAP-2026-SUITE.md`.

## Layout

- Each environment under `environments/sv-env-*/` is a separately installable package registered via `[project.entry-points."verifiers.environments"]`; each exposes `load_environment(...)` with a parser and a weighted rubric. `sv_shared/` is the shared parser/reward/logging toolbox.
- Two venv layers: the root `.venv` (Python 3.12, created by `make setup`) holds the dev tools and editable installs of every environment, and each `environments/sv-env-*/` has its own `.venv` from `uv sync`. `make setup` creates both. `make test-env E=<name>` runs one environment's tests from the root venv.

## Preferred workflow (use `make`)

- Setup: `make setup && source .venv/bin/activate`
- Scoped review (the default for a change): `make review-check REVIEW_PATHS="<source paths>" REVIEW_TESTS="<test paths>"` — non-fixing checks and the selected tests, using existing dependencies.
- Full quality/fix workflow: `make check` runs lint, all-files fixing hooks, format and tests, and may modify unrelated files. Use only when that scope is intended, and inspect the diff before staging.
- Lint only: `make lint` (Ruff, plus fixing pre-commit hooks). Format only: `make format` (Ruff).
- Tests: `make test`, or `make test-env E=<name>` (e.g. `E=network-logs`). Single test: `uv run pytest environments/sv-env-network-logs/sv_env_network_logs_test.py::TestNetworkLogParser::test_extracts_label_and_confidence -q`
- Evals: `make eval-e1 ...` / `make eval-e2 ...` (artifacts under `outputs/evals/`); reports: `uv run svbench_report --env e1|e2 --input outputs/evals/...`
- Prefer Make targets over raw commands; `make help` and `make info` list them.

## Environment and secrets

- Load `.env` before evals or HuggingFace work: `cp .env.example .env`, then `set -a && source .env && set +a`.
- Never print secrets (values from `.env`, API keys, tokens). Relying on `.env` for local execution is fine; avoid logging environment values.

## Invariants

- Enforce strict JSON schemas; malformed model outputs get zero reward.
- `make hf-e1p-push-canonical` and `make hf-e2p-push-canonical` use `--force`, which deletes and recreates the HuggingFace repo to clear cached schema metadata. Use only for a schema change, and dry-run first with the `-dry` variants.
- Hub deployment (`make deploy`, `make hub-deploy`) publishes: it requires `prime login` and the `intertwine` team (`TEAM=` overrides).
- Update environment READMEs when behavior changes; keep tests green.

## Code style

- Python linting/formatting is handled by Ruff; keep changes Ruff-clean.
- Prefer small, surgical diffs; match existing patterns and naming.

## Reference

- `docs/development.md` (contributing, testing, CI), `docs/getting-started.md` (first evaluation)
- `docs/hub-deployment.md`, `docs/user-dataset-guide.md`, `docs/datasets.md`, `docs/logging.md`, `docs/PRIME-LAB-INTEGRATION.md`
- Skills: `skills/*/SKILL.md` — eval, data, deploy, hf, dev, report; index in `skills/README.md`
