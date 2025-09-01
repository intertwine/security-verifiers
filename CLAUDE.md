# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Python monorepo for security-focused reinforcement learning environments built with Prime Intellect's verifiers library. The repository contains six security verifier environments designed for training and evaluating LLMs on security tasks.

## Environment Structure

Each environment follows a consistent structure under `environments/`:

- `<package_name>.py`: Main environment implementation module
- `<package_name>_test.py`: Test file for the environment
- `pyproject.toml`: Environment-specific dependencies

The six environments are:

- `sv-env-network-logs`: Network log anomaly detection (SingleTurnEnv)
- `sv-env-phishing-detection`: Phishing email detection (SingleTurnEnv)
- `sv-env-redteam-defense`: Defensive AI security boundaries (MultiTurnEnv)
- `sv-env-redteam-attack`: Red team attack generation (MultiTurnEnv)
- `sv-env-code-vulnerability`: Code vulnerability assessment (ToolEnv/MultiTurnEnv)
- `sv-env-config-verification`: Security configuration verification (MultiTurnEnv)

## Common Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
uv venv --python=python3.12
source .venv/bin/activate

# Install dependencies for an environment
cd environments/<env-name> && uv sync && cd ../..

# Install environment in editable mode
uv pip install -e environments/<env-name>

# Add new dependencies to an environment
cd environments/<env-name> && uv add <package-name> && cd ../..
```

### Linting and Formatting

```bash
# Run linter on entire repo
uv run ruff check .

# Format code
uv run ruff format .

# Fix linting issues automatically
uv run ruff check . --fix
```

### Testing

```bash
# Run all tests from repo root
uv run pytest

# Run tests for specific environment
uv run pytest environments/<env-name>/ -q

# Run tests matching pattern
uv run pytest -k "pattern" -q

# Run tests with verbose output
uv run pytest -v
```

### Building

```bash
# Build wheel for specific environment
uv run python -m build --wheel environments/<env-name>
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Architecture Patterns

### Environment Implementation Pattern

Each environment implements the verifiers library interface with:

1. **Parser classes** (extending `vf.Parser`): Extract and validate model responses
2. **Environment classes**: Handle task setup, multi-turn interactions, and reward calculation
3. **Verifier classes**: Core evaluation logic for security tasks
4. **Interface protocols**: Type-safe contracts defined in `interfaces.py`
5. **Skeleton implementations**: Base stub classes in `skeletons.py`

### Reward System

Environments use a rubric-based reward system:

- Format rewards: Check response formatting compliance
- Correctness rewards: Evaluate accuracy of security classifications
- Partial credit: Intermediate rewards for multi-turn tasks

### Dataset Loading

Environments support multiple dataset sources:

- Local synthetic datasets (fallback when external sources unavailable)
- HuggingFace datasets via `load_dataset()`
- Custom dataset generation for security scenarios

## Integration with Prime Intellect Verifiers

The environments are designed to work with Prime Intellect's infrastructure:

- Use `load_environment()` function as entry point
- Compatible with `vf-eval` CLI for testing
- Support both SingleTurnEnv and MultiTurnEnv patterns
- Tool-enabled environments use ToolEnv for function calling

## Important Implementation Notes

- Always use absolute imports within environment packages
- Each environment module is self-contained at the environment root level
- Include proper error handling for missing dependencies or datasets
- Follow the existing parser pattern for extracting model responses
- Ensure rewards are normalized between 0.0 and 1.0
- Test with small examples before full dataset evaluation
