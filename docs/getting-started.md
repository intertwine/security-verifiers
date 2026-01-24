# Getting Started with Security Verifiers

This guide will help you set up and run your first evaluation with Security Verifiers.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys for model inference (OpenAI or OpenRouter)

## Quick Setup

```bash
# Clone the repository
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers

# One-time setup (creates venv, installs dependencies)
make setup
source .venv/bin/activate

# Copy environment variables template
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables

Set these in your `.env` file:

```bash
# Required for OpenAI models (gpt-*)
OPENAI_API_KEY=sk-...

# Required for non-OpenAI models via OpenRouter
OPENROUTER_API_KEY=sk-or-...

# Optional: HuggingFace token for gated datasets
HF_TOKEN=hf_...

# Optional: Weights & Biases for logging
WANDB_API_KEY=...
```

Load your environment:
```bash
set -a && source .env && set +a
```

## Run Your First Evaluation

### E1: Network Log Anomaly Detection

```bash
# Run evaluation with GPT-5-mini on 10 examples
make eval-e1 MODELS="gpt-5-mini" N=10

# Results are written to outputs/evals/sv-env-network-logs--gpt-5-mini/<run_id>/
```

### E2: Configuration Verification (Multi-turn)

```bash
# Run multi-turn evaluation with tool use
make eval-e2 MODELS="gpt-5-mini" N=2 INCLUDE_TOOLS=true

# Results are written to outputs/evals/sv-env-config-verification--gpt-5-mini/<run_id>/
```

## Understanding Results

Each evaluation run creates:
- `metadata.json`: Run configuration (model, params, timestamps)
- `results.jsonl`: Per-example results with rewards and completions

Generate a metrics report:
```bash
make report-network-logs      # E1 metrics
make report-config-verification  # E2 metrics
```

## Available Environments

| Environment | Type | Task | Status |
|-------------|------|------|--------|
| E1: network-logs | SingleTurn | Anomaly detection with calibration | Production |
| E2: config-verification | ToolEnv | Security auditing with tools | Production |
| E3: code-vulnerability | ToolEnv | Vulnerability detection/repair | WIP |
| E4: phishing-detection | SingleTurn | Phishing email classification | WIP |
| E5: redteam-attack | MultiTurn | Red team attack scenarios | WIP |
| E6: redteam-defense | MultiTurn | Red team defense scenarios | WIP |

## Next Steps

- [Development Guide](development.md) - Contributing and testing
- [Hub Deployment](hub-deployment.md) - Deploy to Prime Intellect Hub
- [Logging Guide](logging.md) - Configure Weave tracing
- [Dataset Guide](user-dataset-guide.md) - Build and manage datasets

## Troubleshooting

### API Errors
```bash
# Test your API key
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Missing Dependencies
```bash
make setup  # Reinstall dependencies
```

### Dataset Access
If you see "gated dataset" errors, request access at the HuggingFace dataset page and set `HF_TOKEN`.

## Getting Help

- [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)
- See `CLAUDE.md` for detailed command reference
