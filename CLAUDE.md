# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Open Security Verifiers repository.

## Repository Overview

Open Security Verifiers is a composable suite of six security and alignment RL environments for Prime Intellect's Environments Hub. The project emphasizes verifiable, executable rewards for training and evaluating AI systems on critical security tasks.

**Vision**: Build environments where agents learn behaviors we can verify: policies satisfied, tests pass, safe refusals, calibrated abstention. See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) and [PRD.md](PRD.md) for complete specifications.

## Project Structure

```markdown
security-verifiers/
├── environments/ # Six RL environment packages
│ ├── sv-env-network-logs/ # E1: Network anomaly (prototype)
│ ├── sv-env-phishing-detection/ # E4: Phishing + evidence
│ ├── sv-env-config-verification/# E2: Tool-using config audit
│ ├── sv-env-code-vulnerability/ # E3: Patch-and-test repair
│ ├── sv-env-redteam-attack/ # E5: Attack simulator
│ └── sv-env-redteam-defense/ # E6: Alignment defender
├── docs/ # Research notes and application materials
├── EXECUTIVE_SUMMARY.md # High-level vision
├── PRD.md # Detailed specifications
└── CONTRIBUTING.md # Contribution guidelines
```

## Development Commands

### Quick Start with Makefile

The project includes a comprehensive Makefile for common tasks:

```bash
# Complete setup (recommended)
make setup
source .venv/bin/activate

# Daily workflow
make check                     # Run all quality checks
make test                      # Run all tests
make test-env E=network-logs   # Test specific environment
make format                    # Format code
make lint-fix                  # Fix linting issues

# Building and deployment
make build-env E=network-logs  # Build environment wheel
make deploy E=network-logs     # Deploy to Hub
make eval E=network-logs       # Evaluate locally

# Shortcuts for testing environments
make e1  # Test network-logs
make e2  # Test config-verification
make e3  # Test code-vulnerability
make e4  # Test phishing-detection
make e5  # Test redteam-attack
make e6  # Test redteam-defense
```

### Manual Commands (when needed)

```bash
# Environment management
uv venv --python=python3.12
source .venv/bin/activate
cd environments/sv-env-network-logs && uv sync && cd ../..
uv pip install -e environments/sv-env-network-logs

# Add new dependency
cd environments/sv-env-network-logs && uv add package-name && cd ../..

# Code quality (without make)
uv run ruff check . --fix
uv run ruff format .
uv run pytest

# Manual deployment
cd environments/sv-env-network-logs
uv run python -m build --wheel
prime login
prime env push -v PUBLIC
```

## Key Design Principles

### 1. Executable Verification First

- Use actual tools (OPA, KubeLinter, Semgrep, tests) as ground truth
- Minimize reliance on LLM judges
- Zero reward for malformed outputs

### 2. Composable Components

- Shared schemas across environments
- Common reward functions (calibration, abstention, costs)
- Reusable tool wrappers
- Standardized evaluation metrics

### 3. Operational Focus

- Calibration rewards for well-calibrated confidence
- Abstention support ("I don't know" is valid)
- Asymmetric costs (e.g., false negatives >> false positives)
- Real-world datasets and benchmarks

## Environment Implementation Guidelines

### Required Components

Each environment must implement:

1. **`load_environment()` function**: Entry point returning a Verifiers environment
2. **Strict output schemas**: JSON with exact fields per PRD
3. **Rubric-based rewards**: Multiple weighted reward components
4. **Test coverage**: Unit and integration tests

### Example Structure

```python
# sv_env_network_logs.py
import verifiers as vf

def r_label(*, completion, info, **_):
    """Exact label match reward."""
    # Implementation

def r_calibration(*, completion, info, **_):
    """Calibration bonus for confidence scores."""
    # Implementation

RUBRIC = vf.Rubric(
    funcs=[r_label, r_calibration],
    weights=[1.0, 0.5]
)

def load_environment(split="train"):
    dataset = load_dataset(split)
    return vf.SingleTurnEnv(
        dataset=dataset,
        rubric=RUBRIC,
        system_prompt="..."
    )
```

## Current Status

- **E1 (Network Logs)**: Toy prototype deployed to Hub for validation
- **E2-E6**: Work in progress, READMEs updated with PRD specifications

## Important Notes for Claude

### When Working on Environments

1. **Check PRD.md first**: Each environment (E1-E6) has detailed specifications
2. **Maintain composability**: Use shared toolbox components
3. **Test locally**: Run `vf-eval` before pushing to Hub
4. **Document changes**: Update environment READMEs

### Code Standards

- Use type hints for all function signatures
- Normalize rewards to [0.0, 1.0]
- Handle missing dependencies gracefully
- Include docstrings for public functions
- Follow existing parser patterns

### Security Considerations

- Never commit API keys or secrets
- Hash/remove sensitive content from datasets
- Sandbox code execution in E3
- Use Llama Guard 3 for E5/E6 safety scoring

### Deployment Checklist

Before deploying an environment:

- [ ] Tests pass (`make test-env E=name`)
- [ ] Linting clean (`make lint`)
- [ ] Code formatted (`make format`)
- [ ] README updated with examples
- [ ] Output schema matches PRD specification
- [ ] Rewards properly normalized
- [ ] Dependencies in pyproject.toml
- [ ] Build successful (`make build-env E=name`)
- [ ] Local evaluation works (`make eval E=name`)

## Resources

- [Verifiers Documentation](https://verifiers.readthedocs.io)
- [Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli)
- [Project PRD](PRD.md) - Detailed specifications for each environment

## Workflow Reminders

- This is an open-source project - contributions welcome!
- Focus on executable verification over subjective judgments
- Test with multiple datasets for OOD evaluation
- Document security considerations for each environment
- Coordinate with other environments for shared components
