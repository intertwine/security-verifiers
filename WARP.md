# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Commands commonly used in this codebase
- Environment setup (uv):
• Create venv (Python 3.12): uv venv --python=python3.12; then activate: source .venv/bin/activate
  • Install all local packages (editable):
    uv pip install -e environments/sv-env-prompt-injection -e environments/sv-env-secrets-leakage -e environments/sv-env-tool-use-safety -e environments/sv-env-code-exec-safety -e environments/sv-env-network-safety -e environments/sv-env-policy-compliance
  • Developer tools (install once per venv): uv pip install pytest ruff build pre-commit
- Lint:
  • uv run ruff check .
- Format:
  • uv run ruff format .
- Tests:
  • Run all tests: uv run pytest -q
  • Run a single test file: uv run pytest environments/sv-env-prompt-injection/tests/test_placeholder.py -q
  • Run tests by pattern: uv run pytest -k "pattern" -q
- Build a wheel for a subproject:
  • uv run python -m build --wheel environments/sv-env-prompt-injection
- Pre-commit hooks (optional):
  • uv run pre-commit install
  • uv run pre-commit run --all-files

High-level architecture and structure (big-picture)
- Monorepo of six independent Python packages under environments/:
  • sv-env-prompt-injection
  • sv-env-secrets-leakage
  • sv-env-tool-use-safety
  • sv-env-code-exec-safety
  • sv-env-network-safety
  • sv-env-policy-compliance
  Each uses src/ layout and setuptools packaging; no runtime implementation yet.
- Each package is intended to become an RL environment built atop the Prime Intellect verifiers library.
- docs/ contains product/implementation planning:
  • prd-environments-md: outlines building and publishing environments and model training workflows.
  • prd-verifiers.md: scoping decisions (local vs. cloud workflows, stack choices, model targets).

In-repo rules and guides
- No Claude, Cursor, or Copilot rules files are present in this repository.
- README.md provides uv workflows and monorepo usage; keep WARP.md aligned with README.md when workflows change.

Project-specific operational constraints for Warp
- Never run git commit or git push from Warp in this repository. The user handles all commits and pushes manually.

