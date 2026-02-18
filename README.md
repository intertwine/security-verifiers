# Security Verifiers

[![CI](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml/badge.svg)](https://github.com/intertwine/security-verifiers/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A composable suite of security and alignment RL environments with **executable, verifiable rewards**. Built for [Prime Intellect's Verifiers](https://github.com/primeintellect-ai/verifiers) framework.

## Vision

Security Verifiers demonstrates how executable rewards can advance both security and alignment research. Rather than relying on LLM-as-judge, our environments use real tools (OPA, Semgrep, test suites) to verify agent behavior, producing rewards that are:

- **Executable**: Rewards come from running actual security tools
- **Calibrated**: Agents are rewarded for well-calibrated confidence
- **Cost-aware**: Asymmetric penalties reflect real operational costs (missing malware >> false alarms)
- **Composable**: Shared schemas and tools enable transfer across tasks

## Environments

| Environment | Type | Task | Status |
|-------------|------|------|--------|
| **E1: network-logs** | SingleTurn | Anomaly detection with calibration & abstention | Production |
| **E2: config-verification** | ToolEnv | Security auditing with OPA/KubeLinter/Semgrep | Production |
| E3: code-vulnerability | ToolEnv | Vulnerability detection and repair | WIP |
| E4: phishing-detection | SingleTurn | Phishing classification with evidence | WIP |
| E5: redteam-attack | MultiTurn | Red team attack scenarios | WIP |
| E6: redteam-defense | MultiTurn | Red team defense scenarios | WIP |

## Quick Start

```bash
# Setup
make setup && source .venv/bin/activate

# Configure API keys
cp .env.example .env  # Edit with your OPENAI_API_KEY
set -a && source .env && set +a

# Run your first evaluation
make eval-e1 MODELS="gpt-5-mini" N=10
```

See [docs/getting-started.md](docs/getting-started.md) for detailed setup instructions.

## Evaluation

```bash
# E1: Network log anomaly detection
make eval-e1 MODELS="gpt-5-mini,gpt-4.1-mini" N=100

# E2: Configuration verification (multi-turn with tools)
make eval-e2 MODELS="gpt-5-mini" N=10 INCLUDE_TOOLS=true

# Generate metrics reports
make report-network-logs
make report-config-verification
```

Results are written to `outputs/evals/<env>--<model>/<run_id>/`.

## Hub Deployment

Deploy environments to [Prime Intellect's Environments Hub](https://app.primeintellect.ai/dashboard/environments):

```bash
make hub-deploy E=network-logs
vf-eval your-org/sv-env-network-logs --model gpt-5-mini --num-examples 10
```

See [docs/hub-deployment.md](docs/hub-deployment.md) for complete deployment guide.

## Project Structure

```
security-verifiers/
├── environments/       # E1-E6 environment packages
├── sv_shared/          # Shared parsers, rewards, utilities
├── scripts/            # Evaluation and data building scripts
├── docs/               # Documentation
├── plans/              # Roadmap and productionization plans
└── outputs/            # Evaluation results
```

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first evaluation |
| [Development Guide](docs/development.md) | Contributing, testing, CI |
| [Hub Deployment](docs/hub-deployment.md) | Deploy to Prime Intellect Hub |
| [Prime Lab Integration](docs/PRIME-LAB-INTEGRATION.md) | Hosted RL training and evaluation |
| [Datasets Guide](docs/datasets.md) | Dataset access and management |
| [Logging Guide](docs/logging.md) | Weave tracing configuration |
| [CLAUDE.md](CLAUDE.md) | Agent/LLM instructions |

## Baselines

Run quick baselines on the public mini sets:
```
make baseline-e1 MODEL="gpt-5-mini"
make baseline-e2 MODEL="gpt-5-mini" INCLUDE_TOOLS=true
```

Scoreboards are written to `bench/scoreboards/`.

## Prime Lab Integration

Environments are fully integrated with [Prime Intellect's Lab](https://docs.primeintellect.ai/) for hosted RL training and evaluation:

```bash
# Check platform compatibility
make lab-check

# Hosted training (requires prime lab access + your team credentials)
make lab-run-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team
make lab-run-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team

# Hosted evaluation
make lab-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team

# Fallback: hosted-style eval via prime env
make env-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team N=100
```

Replace `your-team` with your Prime Intellect team slug (from `prime auth status`).

See [docs/PRIME-LAB-INTEGRATION.md](docs/PRIME-LAB-INTEGRATION.md) for the full integration guide.

## Roadmap

See [plans/ROADMAP-Q1-2026.md](plans/ROADMAP-Q1-2026.md) for current development priorities:

| Work Package | Description | Status |
|---|---|---|
| **WP0** | Benchmark integrity hardening | Complete |
| **WP1** | Metrics contracts and report generator | Complete |
| **WP2** | Baselines and public mini sets | Complete |
| **WP2.5** | Prime Lab integration (v0.3.0) | Complete |
| **WP2.5a** | Hosted-eval fallback parity | Complete |
| **WP3a/b** | Hosted RL proof on E1 and E2 | Next |
| **WP4** | Multi-reward RL stability research | Planned |
| **WP5** | SV-Bench v0.1 release | Planned |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
