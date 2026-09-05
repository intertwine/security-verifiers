# AGENTS.md

These are default repo-wide instructions for coding agents working in this repository.

## Preferred workflow (use `make`)

- Setup: `make setup && source .venv/bin/activate`
- Scoped review: `make review-check REVIEW_PATHS="<source paths>" REVIEW_TESTS="<test paths>"` with existing dependencies; checks do not fix files.
- Full quality/fix workflow: `make check` (runs lint, all-files fixing hooks, format and tests; may modify unrelated files). Use only when that scope is intended.
- Lint only: `make lint` (Ruff)
- Format only: `make format` (Ruff)
- Tests: `make test` (or `make test-env E=<name>`)
- Evals: `make eval-e1 ...` / `make eval-e2 ...` (artifacts under `outputs/evals/`)
- Reports: `uv run svbench_report --env e1|e2 --input outputs/evals/...`

## Code style

- Python linting/formatting is handled by Ruff; keep changes Ruff-clean.
- Prefer small, surgical diffs; match existing patterns and naming.

## Secrets / credentials

- Never print secrets (e.g., values from `.env`, API keys/tokens).
- It’s OK to rely on `.env` for local execution, but avoid logging environment values.

## Reference

- See `CLAUDE.md` for the full project workflow and command catalog.
