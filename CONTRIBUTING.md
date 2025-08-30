# Contributing to Security Verifiers

Thank you for your interest in contributing! This repository is a Python 3.12 monorepo managed with uv, using ruff for linting/formatting and pytest for tests.

Prerequisites
- Python 3.12
- uv (https://github.com/astral-sh/uv)

Setup
1) Create and activate a virtualenv
- uv venv --python=python3.12
- source .venv/bin/activate

2) Install local packages and developer tools
- uv pip install -e environments/sv-env-prompt-injection -e environments/sv-env-secrets-leakage -e environments/sv-env-tool-use-safety -e environments/sv-env-code-exec-safety -e environments/sv-env-network-safety -e environments/sv-env-policy-compliance
- uv pip install pytest ruff build pre-commit

Developer workflow
- Lint: uv run ruff check .
- Format: uv run ruff format .
- Tests (all): uv run pytest -q
- Tests (single file): uv run pytest environments/sv-env-prompt-injection/tests/test_prompt_injection_placeholder.py -q
- Build a wheel for a subproject: uv run python -m build --wheel environments/sv-env-prompt-injection

Pre-commit hooks (recommended)
- Install hooks: uv run pre-commit install
- Run on all files: uv run pre-commit run --all-files

Adding or modifying an environment
- Each environment lives under environments/<env-name> with src/ layout and its own pyproject.toml.
- If you add dependencies for a single environment, declare them in that environment’s pyproject.toml under [project].dependencies, then reinstall that package in editable mode.
- Keep public APIs minimal and type-annotated. Run ruff and pytest before opening a PR.

Implementing verifiers and environments
- Each environment ships with Protocols in src/<package>/interfaces.py and stub classes in src/<package>/skeletons.py.
- Implement concrete verifiers and environments by following those shapes; prefer small, composable verifiers.
- See docs/verifier-template.md for a fuller template and guidance.

Pull requests
- Keep changes focused and include tests where applicable.
- Ensure ruff and pytest pass locally before submitting.

