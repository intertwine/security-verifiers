# Development Guide

This guide covers contributing to Security Verifiers, testing, and CI/CD.

## Development Setup

```bash
# Clone and setup
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers
make setup
source .venv/bin/activate

# Install pre-commit hooks
make pre-commit
```

## Code Quality

### Linting and Formatting

```bash
make check    # Run all checks (lint + format + tests)
make lint     # Ruff linting only
make format   # Ruff formatting only
```

### Testing

```bash
# Run all tests
make test

# Test a specific environment
make test-env E=network-logs
make test-env E=config-verification

# Run a single test
uv run pytest environments/sv-env-network-logs/sv_env_network_logs_test.py::TestNetworkLogParser::test_extracts_label_and_confidence -q
```

## Project Structure

```
security-verifiers/
├── environments/           # Environment packages (E1-E6)
│   ├── sv-env-network-logs/
│   ├── sv-env-config-verification/
│   └── ...
├── sv_shared/              # Shared utilities package
│   ├── parsers.py          # Output parsers
│   ├── rewards.py          # Reward functions
│   ├── dataset_loader.py   # Multi-tier dataset loading
│   └── weave_init.py       # Logging initialization
├── scripts/                # Evaluation and data scripts
├── docs/                   # Documentation
├── plans/                  # Roadmaps and plans
└── outputs/                # Evaluation outputs
```

## Environment Development

Each environment is an installable Python package with a standard structure:

```
sv-env-<name>/
├── pyproject.toml          # Package configuration
├── sv_env_<name>.py        # Main environment module
├── sv_env_<name>_test.py   # Tests
├── README.md               # Environment documentation
└── data/                   # Local datasets (if any)
```

### Key Components

1. **`load_environment()`**: Entry point that returns a Verifiers environment
2. **Parser**: Extracts structured output from model completions
3. **Rubric**: Defines reward functions and weights

### Adding a New Environment

1. Copy an existing environment as a template
2. Update `pyproject.toml` with the entry point
3. Implement `load_environment()` returning `vf.SingleTurnEnv`, `vf.ToolEnv`, or `vf.MultiTurnEnv`
4. Add tests covering parser, rewards, and environment loading
5. Add documentation (README.md, DATA_CARD.md)

## Building and Deploying

### Build Wheels

```bash
make build                    # Build all environments
make build-env E=network-logs # Build one environment
make build-utils              # Build sv_shared package
```

### Deploy to Prime Intellect Hub

```bash
# Validate and deploy
make hub-deploy E=network-logs

# Bump version and deploy
make hub-deploy E=network-logs BUMP=patch
```

### Publish sv_shared to PyPI

```bash
make pypi-publish-utils-test  # Test on TestPyPI
make pypi-publish-utils       # Publish to PyPI
```

## Dataset Development

### Building Datasets

```bash
# E1 datasets
make data-e1                  # Build IoT-23 dataset
make data-e1-ood              # Build OOD datasets

# E2 datasets
make clone-e2-sources         # Clone K8s/Terraform repos
make data-e2-local            # Build from cloned sources
```

### Pushing to HuggingFace

```bash
make validate-data                        # Validate with Pydantic
make hf-e1p-push-canonical HF_ORG=...     # Push E1 private
make hf-e2p-push-canonical HF_ORG=...     # Push E2 private
```

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

1. **Linting**: `ruff check`
2. **Tests**: `pytest` with coverage
3. **Build**: Wheel building on tags

### Local CI Simulation

```bash
make check  # Runs lint + format + tests
```

## Version Management

```bash
# Bump environment versions
make update-version E=network-logs BUMP=patch  # 0.0.x
make update-version E=network-logs BUMP=minor  # 0.x.0
make update-version E=network-logs BUMP=major  # x.0.0

# Bump sv_shared version
make update-utils-version BUMP=patch
```

## Debugging Tips

### Verbose Test Output
```bash
uv run pytest -v --tb=long
```

### Check Tool Versions (E2)
```bash
cat environments/sv-env-config-verification/ci/versions.txt
```

### Inspect Evaluation Results
```bash
cat outputs/evals/sv-env-network-logs--gpt-5-mini/<run_id>/metadata.json | jq .
head -1 outputs/evals/sv-env-network-logs--gpt-5-mini/<run_id>/results.jsonl | jq .
```

## Code Style

- Follow existing patterns in the codebase
- Use type hints throughout
- Keep functions focused and testable
- Document public APIs with docstrings
- Avoid over-engineering - solve the current problem simply

## Getting Help

- Check `CLAUDE.md` for comprehensive command reference
- See environment READMEs for environment-specific details
- Open a GitHub issue for bugs or feature requests
