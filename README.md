# Security Verifiers

A monorepo scaffold for six Reinforcement Learning (RL) environments built in Python and intended to use the Prime Intellect verifiers library. This repo currently contains placeholders only (no environment logic yet).

Monorepo layout
- environments/
  - sv-env-prompt-injection: prompt-injection and jailbreak resilience
  - sv-env-secrets-leakage: sensitive data leakage prevention
  - sv-env-tool-use-safety: safe external tool/action usage
  - sv-env-code-exec-safety: generated code execution safety
  - sv-env-network-safety: outbound network request safety
  - sv-env-policy-compliance: organizational policy compliance
- docs/
  - prd-environments-md, prd-verifiers.md: product/implementation planning docs

Getting started (uv)
- Prereqs: Python 3.12+ and uv installed

1) Create and activate a virtual environment
- uv venv --python=python3.12
- source .venv/bin/activate

2) Install editable packages and dev tools
- Install all local packages in editable mode:
  - uv pip install -e environments/sv-env-prompt-injection -e environments/sv-env-secrets-leakage -e environments/sv-env-tool-use-safety -e environments/sv-env-code-exec-safety -e environments/sv-env-network-safety -e environments/sv-env-policy-compliance
- Install dev tools:
  - uv pip install pytest ruff build

3) Lint and test
- Lint entire repo:
  - uv run ruff check .
- Run all tests:
  - uv run pytest -q
- Run a single test file:
  - uv run pytest environments/sv-env-prompt-injection/tests/test_placeholder.py -q
- Run tests matching a pattern:
  - uv run pytest -k "placeholder" -q

Building a wheel for a subproject
- Build a wheel for sv-env-prompt-injection:
  - uv run python -m build --wheel environments/sv-env-prompt-injection
  (Artifacts are emitted to the subproject’s dist/ directory.)

Notes
- The environment packages are placeholders; implementation will be added iteratively.
