# Contributing to Security Verifiers

Thank you for your interest in contributing! This repository is a Python 3.12 monorepo managed with uv, using ruff for linting/formatting and pytest for tests.

Prerequisites

- Python 3.12
- uv (<https://github.com/astral-sh/uv>)

Setup

1. Create and activate a virtualenv

- uv venv --python=python3.12
- source .venv/bin/activate

1. Install local packages and developer tools

- for env in environments/\*/; do uv pip install -e "$env"; done
- uv pip install pytest ruff build pre-commit

Developer workflow

- Lint: uv run ruff check .
- Format: uv run ruff format .
- Tests (all): uv run pytest -q
- Tests (single file): uv run pytest environments/sv-env-network-logs/sv_env_network_logs_test.py -q
- Build a wheel for a subproject: uv run python -m build --wheel environments/sv-env-network-logs

Pre-commit hooks (recommended)

- Install hooks: uv run pre-commit install
- Run on all files: uv run pre-commit run --all-files

Adding or modifying an environment

- Each environment lives under `environments/<env-name>` with a flat layout and its own pyproject.toml.
- If you add dependencies for a single environment, declare them in that environment’s pyproject.toml under [project].dependencies, then reinstall that package in editable mode.
- Keep public APIs minimal and type-annotated. Run ruff and pytest before opening a PR.

Implementing verifiers and environments

- Each environment is implemented as a single module file <package_name>.py with its corresponding test file <package_name>\_test.py.
- Use the templates in templates/ directory as a starting point for new environments.
- Implement parser classes, reward functions, and the load_environment() entry point.
- See templates/README.md for detailed guidance on creating new environments.

Pull requests

- Keep changes focused and include tests where applicable.
- Ensure ruff and pytest pass locally before submitting.
