# Network Log Anomaly Detection

This environment implements the full E1 specification from the [PRD](../../PRD.md). Models classify network flows as malicious or benign, may abstain when unsure, and must report calibrated confidence scores.

## Overview

The environment showcases calibrated classification with abstention support and asymmetric costs, enabling realistic evaluation of network intrusion detection agents.

**Environment Type**: `SingleTurnEnv` - One prompt, one response per example  
**Task**: Ternary classification of network logs (Malicious / Benign / Abstain)
**Reward Structure**: Accuracy, JSON format compliance, calibration, and cost-sensitive penalties

## Installation

Install the environment using the Prime CLI:

```bash
prime env install intertwine/sv-env-network-logs
```

Or using pip/uv directly:

```bash
pip install intertwine-sv-env-network-logs
```

## Setup

### API Keys Configuration

Before using this environment, you need to configure API keys for model inference and dataset access:

1. **OpenAI API Key** (optional, for OpenAI models):

   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

2. **HuggingFace Token** (required for IoT-23 dataset access):

   ```bash
   export HF_TOKEN="your-huggingface-token"
   ```

   Get your HuggingFace token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

**Note**: Without the HF_TOKEN, the environment will fall back to using a synthetic dataset with limited examples.

## Usage

### With Verifiers Library

```python
import verifiers as vf

# Load the environment
env = vf.load_environment("intertwine/sv-env-network-logs")

# Evaluate a model
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-5-mini",
    num_examples=100
)

print(f"Average reward: {results.stats['mean_reward']:.2%}")
```

### Quick Evaluation

Use the verifiers CLI for quick testing:

```bash
# For OpenAI models (requires OPENAI_API_KEY environment variable)
vf-eval intertwine/sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 10

# With custom API endpoint
vf-eval intertwine/sv-env-network-logs \
  --model your-model-name \
  --api-host-base https://your-api-endpoint.com/v1 \
  --api-key-var YOUR_API_KEY_ENV_VAR \
  --num-examples 10
```

#### Command Options

- `-m, --model`: Model name to use for evaluation
- `-b, --api-host-base`: Base URL for the API endpoint (e.g., `https://api.openai.com/v1`)
- `-k, --api-key-var`: Name of the environment variable containing your API key
- `--num-examples`: Number of examples to evaluate (default: 100)
- `--verbose`: Enable verbose output for debugging

### Training with Prime RL

In your Prime RL orchestrator configuration:

```toml
[environment]
id = "intertwine/sv-env-network-logs"
```

Then launch training:

```bash
uv run rl \
  --trainer.model.name "Qwen/Qwen-7B" \
  --orchestrator.environment.id "intertwine/sv-env-network-logs" \
  --trainer.steps 1000
```

## Task Details

### Input Format

Network log entries with connection metadata:

```text
"Log Entry: id.orig_h=None, id.orig_p=None, id.resp_h=None, id.resp_p=8081, proto=tcp, service=None, detailed-label=None"
```

### Expected Output

Strict JSON object:

```json
{"label": "Benign|Malicious|Abstain", "confidence": 0.0, "rationale": "string (optional)"}
```

### Scoring

The environment uses a weighted multi-criteria rubric:

- **Classification Accuracy** (1.0)
- **Format Compliance** (0.1)
- **Calibration Bonus** (0.2)
- **Asymmetric Cost** (0.5, heavy penalty for false negatives)

Total reward is the weighted sum of these components.

## Performance Benchmarks

| Model       | Accuracy | Format | Calibration | Overall |
| ----------- | -------- | ------ | ----------- | ------- |
| GPT-4o-mini | 60.3%    | 100%   | 85%         | 82%     |

Benchmarks on 100 examples from the IoT-23 dataset (illustrative).

## Dataset

The environment uses the [IoT-23 dataset](https://huggingface.co/datasets/19kmunz/iot-23-preprocessed-minimumcolumns), containing real network traffic from IoT devices with labeled malicious and benign connections. A synthetic fallback dataset ensures the environment works even without dataset access.

## Requirements

- Python 3.12+
- `verifiers>=0.1.2`
- API key for model inference (e.g., OpenAI API key)
- HuggingFace token for dataset access (optional but recommended)

## About Open Security Verifiers

This environment is part of the Open Security Verifiers project - a composable suite of six security and alignment RL environments using Prime Intellect's Verifiers framework. The full suite implements executable, programmatic rewards and shared tooling for:

- Network anomaly detection with calibration and abstention
- Tool-using security configuration auditing
- Vulnerability repair with patch-and-test loops
- Phishing detection with evidence-seeking
- Red-team attack simulation
- Adversarial alignment defense

See [EXECUTIVE_SUMMARY.md](../../EXECUTIVE_SUMMARY.md) and [PRD.md](../../PRD.md) for the complete vision and specifications.

## Support

For issues or questions about this environment:

- Check the [Security Verifiers repository](https://github.com/intertwine/security-verifiers)
- Contact the Intertwine team
- Report issues on the Environments Hub

## License

Part of the Security Verifiers open-source project. See repository for license details.
