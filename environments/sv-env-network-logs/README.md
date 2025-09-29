# Network Log Anomaly Detection

A security-focused RL environment for training and evaluating models on network intrusion detection. Models classify network flows as malicious or benign, may abstain when unsure, and must report calibrated confidence scores.

## Overview

This environment implements calibrated classification with abstention support and asymmetric costs, enabling realistic evaluation of network intrusion detection agents.

**Environment Type**: `SingleTurnEnv` - One prompt, one response per example
**Task**: Ternary classification of network logs (Malicious / Benign / Abstain)
**Reward Structure**: Accuracy, JSON format compliance, calibration, and cost-sensitive penalties
**Dataset**: IoT-23 network traffic with labeled malicious/benign connections

## Installation

Install the environment using the Prime CLI:

```bash
prime env install intertwine/sv-env-network-logs
```

Or using pip directly:

```bash
pip install sv-env-network-logs
```

## Setup

### API Keys Configuration

Before using this environment, you need to configure API keys for model inference and dataset access:

1. **Set your API keys as environment variables**:

   ```bash
   # OpenAI API Key (required for OpenAI models)
   export OPENAI_API_KEY="your-openai-api-key"

   # HuggingFace Token (optional, for IoT-23 dataset access)
   export HF_TOKEN="your-huggingface-token"
   ```

   Get your HuggingFace token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

**Note**: Without the HF_TOKEN, the environment will fall back to using a synthetic dataset with limited examples.

2. **For persistent configuration, add to your shell profile**:

   ```bash
   echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc
   echo 'export HF_TOKEN="your-token"' >> ~/.bashrc
   source ~/.bashrc
   ```

## Usage

### With Verifiers Library

```python
import os
import verifiers as vf

# Load environment variables from .env file (if running in Python script)
# Alternatively, set them manually:
# os.environ['OPENAI_API_KEY'] = 'your-openai-api-key'
# os.environ['HF_TOKEN'] = 'your-huggingface-token'  # optional

# Load the environment
env = vf.load_environment("sv-env-network-logs")

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
# First, load environment variables from .env file
set -a && source .env && set +a

# For OpenAI models (requires OPENAI_API_KEY environment variable)
vf-eval sv-env-network-logs \
  --model gpt-5-mini \
  --num-examples 10

# With custom API endpoint
vf-eval sv-env-network-logs \
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
id = "sv-env-network-logs"
```

Then launch training:

```bash
# First, load environment variables from .env file
set -a && source .env && set +a

# Then run training
uv run rl \
  --trainer.model.name "Qwen/Qwen-7B" \
  --orchestrator.environment.id "sv-env-network-logs" \
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
- `verifiers>=0.1.4`
- API key for model inference (e.g., OpenAI API key)
- HuggingFace token for dataset access (optional but recommended)

## Weights & Biases Logging

This environment supports automatic Weave tracing for comprehensive experiment tracking:

```python
import wandb
import weave
import verifiers as vf

# Initialize Weave (auto-traces all Verifiers operations)
weave.init(project="network-logs-security")

# Load and evaluate
env = vf.load_environment("intertwine/sv-env-network-logs")
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-4o-mini",
    num_examples=100
)

# Results are automatically traced to W&B
```

Configure Weave via environment variables:
- `WEAVE_PROJECT`: Set project name (default: security-verifiers)
- `WEAVE_DISABLED`: Set to 'true' to disable logging
- `WANDB_API_KEY`: Your W&B API key for cloud logging

## Evaluation Approach

### Metrics Tracked
- **Accuracy**: Correct classification rate (Malicious/Benign/Abstain)
- **Format Compliance**: Valid JSON output adherence
- **Calibration Score**: Confidence alignment with actual accuracy
- **Asymmetric Cost**: False negative penalty (missing attacks is worse than false alarms)
- **Overall Reward**: Weighted combination of all metrics

### Example Evaluation Script

```python
import verifiers as vf
import weave

# Initialize tracking
weave.init(project="security-eval")

env = vf.load_environment("intertwine/sv-env-network-logs")

# Run evaluation
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-4o-mini",
    num_examples=500,
    seed=42
)

print(f"Mean Reward: {results.stats['mean_reward']:.2%}")
print(f"Accuracy: {results.stats.get('accuracy', 0):.2%}")
print(f"Calibration: {results.stats.get('calibration', 0):.2%}")
```

## Future Improvements

- **Enhanced Dataset**: Expand beyond IoT-23 to include enterprise network traffic patterns
- **Multi-turn Interaction**: Support for requesting additional context or log entries
- **Explainability**: Require detailed rationale for high-stakes classifications
- **Active Learning**: Dynamic example selection based on model uncertainty
- **Temporal Analysis**: Support for analyzing sequences of related network events
- **Cost Customization**: Allow environment users to specify their own false positive/negative costs

## About

This environment is part of the Open Security Verifiers suite - a collection of security and alignment RL environments using Prime Intellect's Verifiers framework. Each environment provides executable, programmatic rewards for training robust security-aware AI systems.

## Support

For issues or questions:
- Report issues on the [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- Check the [Security Verifiers GitHub repository](https://github.com/intertwine/security-verifiers)
- Contact the Intertwine team
