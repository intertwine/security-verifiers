# Open Security Verifiers

[![CI](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml/badge.svg)](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml)

An integrated suite of composable security and alignment RL environments for Prime Intellect's Environments Hub. This project implements verifiable, executable rewards for training and evaluating AI systems on critical security tasks.

## Vision & Approach

Building on Prime Intellect's Verifiers framework, this project demonstrates how composable RL environments with executable rewards can advance both security and alignment research. Our environments share schemas, tools, and evaluation methods so skills transfer across tasks.

See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for the high-level vision and [PRD.md](PRD.md) for detailed specifications.

## Environment Suite

### Production-Ready

- **`sv-env-network-logs`**: Network log anomaly detection with calibration and abstention (_toy prototype for Hub validation_)

### In Development (Work in Progress)

- **`sv-env-phishing-detection`**: Phishing detection with evidence-seeking and calibrated abstention
- **`sv-env-config-verification`**: Tool-using security configuration auditing (OPA/Rego, KubeLinter, Semgrep)
- **`sv-env-code-vulnerability`**: Vulnerability repair with patch-and-test loops
- **`sv-env-redteam-attack`**: Red-team attack simulator for eliciting unsafe outputs
- **`sv-env-redteam-defense`**: Adversarial alignment defender balancing helpfulness and harmlessness

## Repository Structure

- **`environments/`**: Six RL environment packages (each independently installable)
- **`docs/`**: Research notes and application materials
- **`EXECUTIVE_SUMMARY.md`**: High-level project overview
- **`PRD.md`**: Detailed product requirements and specifications

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli) (for Hub deployment)
- `make` (usually pre-installed on Unix systems)

### Quick Setup

The easiest way to get started is using the Makefile:

```bash
# Complete one-command setup
make setup

# Activate the virtual environment
source .venv/bin/activate
```

This will create a Python 3.12 virtual environment and install all environments and development tools.

### Manual Setup (Alternative)

If you prefer manual setup or need more control:

```bash
# Create virtual environment
uv venv --python=python3.12
source .venv/bin/activate

# Install all environments
make install

# Install development tools
make install-dev
```

## Development Commands

### Using Make (Recommended)

```bash
# Run all quality checks
make check

# Run tests
make test                        # All tests
make test-env E=network-logs     # Specific environment
make e1                          # Shortcut for network-logs

# Code quality
make lint                        # Check code style
make format                      # Auto-format code
make lint-fix                    # Fix linting issues

# Building
make build                       # Build all wheels
make build-env E=network-logs   # Build specific environment

# Deployment
make deploy E=network-logs      # Deploy to Environments Hub

# Evaluation
make eval E=network-logs MODEL=gpt-4o-mini N=100

# Cleanup
make clean                       # Remove build artifacts
make clean-all                   # Remove everything including venv
```

### Using uv Directly

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Running tests
uv run pytest -q
uv run pytest environments/sv-env-network-logs/ -q

# Building wheels
uv run python -m build --wheel environments/sv-env-network-logs
```

## Pre-commit Hooks

```bash
# Install and setup pre-commit hooks
make pre-commit

# Or manually
uv run pre-commit install
uv run pre-commit run --all-files
```

## Environment Specifications

| Environment                  | Type          | Reward Focus                              | Key Innovation                            |
| ---------------------------- | ------------- | ----------------------------------------- | ----------------------------------------- |
| `sv-env-network-logs`        | SingleTurnEnv | Calibration, abstention, asymmetric costs | Operational SOC metrics over raw accuracy |
| `sv-env-phishing-detection`  | SingleTurnEnv | Evidence-seeking, FN penalties            | Tool-calling for URL/domain reputation    |
| `sv-env-config-verification` | ToolEnv       | Machine-verified fixes                    | OPA/Rego/KubeLinter ground truth          |
| `sv-env-code-vulnerability`  | MultiTurnEnv  | Test-passing, minimal diffs               | Executable verification loop              |
| `sv-env-redteam-attack`      | MultiTurnEnv  | Unsafe elicitation success                | Llama Guard 3 safety scoring              |
| `sv-env-redteam-defense`     | MultiTurnEnv  | Helpful/harmless balance                  | Co-training with attacker agent           |

## Shared Toolbox

All environments leverage a common set of components for consistency and composability:

- **Strict JSON Schemas**: Enforced output formats with zero reward for violations
- **Executable Verification**: Tests, policy engines, linters prioritized over LLM judges
- **Calibration Rewards**: Bonuses for well-calibrated confidence scores
- **Abstention Support**: Safe "I don't know" options with appropriate rewards
- **Cost-Sensitive Scoring**: Asymmetric penalties reflecting real operational costs

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, style, and workflow details.

## Notes

- Some environments are still being implemented iteratively
- Each environment has its own `pyproject.toml` with specific dependencies
- The environments use the [verifiers](https://github.com/primeintellect-ai/verifiers) library for RL training
