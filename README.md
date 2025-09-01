# Security Verifiers

[![CI](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml/badge.svg)](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml)

A monorepo scaffold for six Reinforcement Learning (RL) environments built in Python and intended to use the Prime Intellect verifiers library. This repo currently contains placeholders and initial implementations for security-focused RL environments.

## Monorepo Layout

- **environments/**
  - `sv-env-network-logs`: Network logs anomaly detection (SingleTurnEnv)
  - `sv-env-phishing-detection`: Phishing email detection (SingleTurnEnv)
  - `sv-env-redteam-defense`: Defensive AI assistant security (MultiTurnEnv)
  - `sv-env-redteam-attack`: Red team attack generation (MultiTurnEnv)
  - `sv-env-code-vulnerability`: Code vulnerability assessment (ToolEnv/MultiTurnEnv)
  - `sv-env-config-verification`: Configuration security verification (MultiTurnEnv)
- **docs/**
  - `prd-environments.md`, `prd-verifiers.md`: Product/implementation planning docs

## Getting Started (uv)

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed

### 1. Create and Activate a Virtual Environment

```bash
uv venv --python=python3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Environment Packages

Each environment has its own dependencies. Install them using `uv sync`:

```bash
# Install dependencies for each environment
cd environments/sv-env-network-logs && uv sync && cd ../..
cd environments/sv-env-phishing-detection && uv sync && cd ../..
cd environments/sv-env-redteam-defense && uv sync && cd ../..
cd environments/sv-env-redteam-attack && uv sync && cd ../..
cd environments/sv-env-code-vulnerability && uv sync && cd ../..
cd environments/sv-env-config-verification && uv sync && cd ../..
```

Then install all environments in editable mode:

```bash
# Install all local packages in editable mode
uv pip install -e environments/sv-env-network-logs
uv pip install -e environments/sv-env-phishing-detection
uv pip install -e environments/sv-env-redteam-defense
uv pip install -e environments/sv-env-redteam-attack
uv pip install -e environments/sv-env-code-vulnerability
uv pip install -e environments/sv-env-config-verification
```

### 3. Install Development Tools

```bash
uv pip install pytest ruff build pre-commit
```

## Development Commands

### Linting and Formatting

```bash
# Lint entire repo
uv run ruff check .

# Format code
uv run ruff format .
```

### Running Tests

```bash
# Run all tests
uv run pytest -q

# Run tests for a specific environment
uv run pytest environments/sv-env-network-logs/ -q

# Run tests matching a pattern
uv run pytest -k "network" -q
```

### Building Wheels

Build a wheel for a specific environment:

```bash
uv run python -m build --wheel environments/sv-env-network-logs
```

Artifacts are emitted to the subproject's `dist/` directory.

## Pre-commit Hooks (Optional)

```bash
# Install pre-commit and enable hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Environment Details

| Environment | Type | Description |
|------------|------|-------------|
| `sv-env-network-logs` | SingleTurnEnv | Classifies network log entries as malicious or benign |
| `sv-env-phishing-detection` | SingleTurnEnv | Detects phishing attempts in emails |
| `sv-env-redteam-defense` | MultiTurnEnv | Defensive AI assistant maintaining security boundaries |
| `sv-env-redteam-attack` | MultiTurnEnv | Red team attack scenario generation |
| `sv-env-code-vulnerability` | ToolEnv/MultiTurnEnv | Code vulnerability assessment with static analysis tools |
| `sv-env-config-verification` | MultiTurnEnv | Security configuration verification |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, style, and workflow details.

## Notes

- Some environments are still being implemented iteratively
- Each environment has its own `pyproject.toml` with specific dependencies
- The environments use the [verifiers](https://github.com/primeintellect-ai/verifiers) library for RL training