# WARP.md

This file provides guidance to WARP (warp.dev) terminal when working with the Open Security Verifiers repository.

## Project Overview

Open Security Verifiers: A composable suite of six security and alignment RL environments for Prime Intellect's Environments Hub, emphasizing verifiable, executable rewards.

- **Vision**: Build environments where agents learn behaviors we can verify
- **Docs**: See EXECUTIVE_SUMMARY.md and PRD.md for specifications
- **Status**: E1 baseline using shared `sv_shared` utilities; E2 implemented with tool-grounded adapters; E3-E6 in development

## Quick Commands

### Using Makefile (Recommended)

```bash
# Initial setup - one command!
make setup
source .venv/bin/activate

# Daily development
make check                    # Run all quality checks
make test                     # Run all tests
make format                   # Format code
make lint-fix                 # Fix linting issues
make quick-fix                # Format + fix linting

# Test specific environment
make test-env E=network-logs  # Full name
make e1                       # Shortcut for E1

# Build and deploy
make build-env E=network-logs
make deploy E=network-logs

# Evaluate locally
make eval E=network-logs MODEL=gpt-4o-mini N=10

# Get help
make help                     # Show all commands
make info                     # Show project status
```

### Manual Commands (fallback)

```bash
# If make is not available
source .venv/bin/activate
uv run ruff check . --fix
uv run ruff format .
uv run pytest -q
uv run python -m build --wheel environments/sv-env-network-logs
```

## Repository Structure

```shell
security-verifiers/
├── environments/              # Six RL environments
│   ├── sv-env-network-logs/   # E1: Network anomaly detection
│   ├── sv-env-phishing-detection/  # E4: Phishing + evidence
│   ├── sv-env-config-verification/ # E2: Config audit (tools)
│   ├── sv-env-code-vulnerability/  # E3: Vuln repair (tests)
│   ├── sv-env-redteam-attack/      # E5: Attack simulator
│   └── sv-env-redteam-defense/     # E6: Alignment defender
├── sv_shared/                  # Shared parsers, rewards, utilities
├── EXECUTIVE_SUMMARY.md       # High-level vision
├── PRD.md                     # Detailed specifications (E1-E6)
└── CONTRIBUTING.md            # Dev guidelines
```

## Environment Specs (PRD.md)

| Env | Type          | Focus        | Key Feature                 |
| --- | ------------- | ------------ | --------------------------- |
| E1  | SingleTurnEnv | Network logs | Calibration + abstention    |
| E2  | ToolEnv       | Config audit | OPA/KubeLinter/Semgrep      |
| E3  | MultiTurnEnv  | Code repair  | Tests pass + minimal diff   |
| E4  | SingleTurnEnv | Phishing     | Evidence + asymmetric costs |
| E5  | MultiTurnEnv  | Attack       | Llama Guard 3 scoring       |
| E6  | MultiTurnEnv  | Defense      | Helpful/harmless balance    |

## Development Workflow

### Adding Dependencies

```bash
# Add to specific environment
cd environments/sv-env-network-logs
uv add package-name
uv sync
cd ../..
```

### Common Workflows

```bash
# Morning setup
make info                     # Check project status
make test                     # Ensure tests pass

# Before committing
make check                    # Lint + format + test
make pre-commit               # Run pre-commit hooks

# CI/CD simulation
make ci                       # Run CI checks locally
make cd                       # Full CD pipeline

# Cleanup
make clean                    # Remove build artifacts
make clean-all                # Full reset (including venv)
```

## Key Design Principles

1. **Executable verification**: Tests/tools over LLM judges
2. **Strict schemas**: Zero reward for malformed JSON
3. **Calibration**: Reward well-calibrated confidence
4. **Abstention**: "I don't know" is valid
5. **Asymmetric costs**: FN >> FP for security

## Important Reminders

- **Never run git commit/push from WARP** - User handles all Git operations
- **Check PRD.md** - Each environment (E1-E6) has detailed specs
- **Test locally first** - Run pytest before pushing
- **Update READMEs** - Document changes in environment READMEs
- **Composability** - Use shared toolbox components

## Resources

- [Verifiers Docs](https://verifiers.readthedocs.io)
- [Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli)
- [Project GitHub](https://github.com/intertwine/security-verifiers)

## Common Issues

### Import Errors

```bash
# Reinstall environment in editable mode
uv pip install -e environments/sv-env-network-logs
```

### Dataset Access

```bash
# Set HuggingFace token for datasets
export HF_TOKEN="your-token-here"
```

### Build Failures

```bash
# Clean and rebuild
rm -rf environments/*/dist/
cd environments/sv-env-network-logs
uv run python -m build --wheel
```

## Project Status

- ✅ E1 Network Logs: Baseline using shared `sv_shared` components
- ✅ E2 Config Audit: Tool-grounded environment using `e2_config_auditing` adapters and patch verification
- 🚧 E3 Code Repair: Sandbox setup needed
- 🚧 E4 Phishing: Evidence tools pending
- 🚧 E5 Attack: Llama Guard 3 integration
- 🚧 E6 Defense: Co-training infrastructure
