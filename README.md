# Open Security Verifiers

[![CI](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml/badge.svg)](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An integrated suite of composable security and alignment RL environments for Prime Intellect's Environments Hub. This project implements verifiable, executable rewards for training and evaluating AI systems on critical security tasks.

## Vision & Approach

Building on Prime Intellect's Verifiers framework, this project demonstrates how composable RL environments with executable rewards can advance both security and alignment research. Our environments share schemas, tools, and evaluation methods so skills transfer across tasks.

See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) for the high-level vision and [PRD.md](PRD.md) for detailed specifications.

## Environment Suite

### Production-Ready

- **`sv-env-network-logs`**: Network log anomaly detection with calibration and abstention using shared parsers and reward helpers
- **`sv-env-config-verification`**: Tool-grounded configuration auditing using OPA/Rego, KubeLinter, and Semgrep with patch-aware rewards

### Alpha / Preview Releases

- **`sv-env-phishing-detection`**: Phishing detection with evidence-seeking and calibrated abstention
- **`sv-env-code-vulnerability`**: Vulnerability repair with patch-and-test loops
- **`sv-env-redteam-attack`**: Red-team attack simulator for eliciting unsafe outputs
- **`sv-env-redteam-defense`**: Adversarial alignment defender balancing helpfulness and harmlessness ([docs](docs/sv-env-redteam-defense.md))

## Repository Structure

- **`environments/`**: Six RL environment packages (each independently installable)
- **`sv_shared/`**: Shared parsers, reward components, and utilities
- **`docs/`**: Research notes and application materials
- **`EXECUTIVE_SUMMARY.md`**: High-level project overview
- **`PRD.md`**: Detailed product requirements and specifications

## Getting Started

### Reproducible evaluations

- E1 (network-logs):

```bash
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini" N=10
```

Artifacts: outputs/evals/sv-env-network-logs--{model}/<run_id>/{metadata.json,results.jsonl}

- E2 (config-verification):

```bash
make eval-e2 MODELS="gpt-5-mini,gpt-4.1-mini,gpt-4o-mini" N=2 INCLUDE_TOOLS=true
```

Artifacts: outputs/evals/sv-env-config-verification--{model}/<run_id>/{metadata.json,results.jsonl}

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

### Environment Configuration

Before using any of the security verification environments, you need to set up your API keys:

1. **Copy the example environment file**:

   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to the `.env` file**:

   ```bash
   # Required: OpenAI API Key (for model inference)
   OPENAI_API_KEY=your-openai-api-key-here

   # Optional: HuggingFace Token (for dataset access)
   HF_TOKEN=your-huggingface-token-here
   ```

3. **Load environment variables before running commands**:

   ```bash
   # Load environment variables from .env file
   set -a && source .env && set +a
   ```

**Security Note**: The `.env` file is already included in `.gitignore` to prevent accidentally committing your API keys. Never commit actual API keys to version control.

**Note**: Some environments may require additional API keys or external tools. Check individual environment READMEs for specific requirements.

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

#### Using Make (Recommended)

#### Using uv Directly

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

| Environment                  | Type          | Reward Focus                                   | Key Innovation                            |
| ---------------------------- | ------------- | ---------------------------------------------- | ----------------------------------------- |
| `sv-env-network-logs`        | SingleTurnEnv | Calibration, abstention, asymmetric costs      | Operational SOC metrics over raw accuracy |
| `sv-env-phishing-detection`  | SingleTurnEnv | Evidence-seeking, FN penalties                 | Tool-calling for URL/domain reputation    |
| `sv-env-config-verification` | ToolEnv       | Machine-verified fixes with patch verification | OPA/Rego/KubeLinter/Semgrep ground truth  |
| `sv-env-code-vulnerability`  | MultiTurnEnv  | Test-passing, minimal diffs                    | Executable verification loop              |
| `sv-env-redteam-attack`      | MultiTurnEnv  | Unsafe elicitation success                     | Llama Guard 3 safety scoring              |
| `sv-env-redteam-defense`     | SingleTurnEnv (alpha) | Helpful/harmless balance                       | Co-training with attacker agent           |

## Shared Toolbox

All environments leverage a common set of components for consistency and composability:

- Implemented in **`sv_shared/`** for reuse across environments
- **Strict JSON Schemas**: Enforced output formats with zero reward for violations
- **Executable Verification**: Tests, policy engines, linters prioritized over LLM judges
- **Calibration Rewards**: Bonuses for well-calibrated confidence scores
- **Abstention Support**: Safe "I don't know" options with appropriate rewards
- **Cost-Sensitive Scoring**: Asymmetric penalties reflecting real operational costs

## Rollout Logging & Telemetry

Security Verifiers ships with a central rollout logging utility that can stream
environment metadata and RL interaction traces to both [Weave](https://docs.wandb.com/weave/)
and [Weights & Biases](https://docs.wandb.ai/).

- The `sv_shared.rollout_logging.RolloutLogger` class lazily initialises
  both backends and keeps a local buffer so you can query for reward dips or other
  security insights (`logger.find_reward_dips(0.2)`).
- Default configuration lives in `sv_shared/rollout_logging.py` as
  `DEFAULT_ROLLOUT_LOGGING_CONFIG`. Enable logging by cloning the default settings:

  ```python
  from sv_shared import build_rollout_logger
  from environments.sv-env-network-logs.sv_env_network_logs import load_environment

  logger = build_rollout_logger({
      "enabled": True,
      "wandb_project": "security-verifiers-rl",
      "weave_project": "security-verifiers",
  })
  env = load_environment(logger=logger)
  ```

- All environment loaders accept an optional `logger` argument and will emit dataset
  metadata when present. Training loops can then call `logger.log_step` and
  `logger.log_episode_summary` to stream detailed rollout metrics.
- Install the optional telemetry dependencies with `uv pip install -r requirements.txt`.
- Learn more about the logging backends via the official docs:
  [Weave Tracing](https://docs.wandb.com/weave/tracing) •
  [WandB Logging](https://docs.wandb.ai/guides/track/log).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, style, and workflow details.

## License

This project is released under the [MIT License](LICENSE), compatible with Prime Intellect's Verifiers library.

## Notes

- Some environments are still being implemented iteratively
- Each environment has its own `pyproject.toml` with specific dependencies
- The environments use the [verifiers](https://github.com/primeintellect-ai/verifiers) library for RL training
