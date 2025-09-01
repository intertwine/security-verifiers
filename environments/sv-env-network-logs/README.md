# Network Log Anomaly Detection

A security-focused reinforcement learning environment for training models to detect malicious activity in network logs. Part of the Security Verifiers suite by Intertwine.

## Overview

This environment challenges models to classify network log entries as either malicious or benign, helping train AI systems for cybersecurity applications. Models analyze IoT network traffic logs and must accurately identify potential security threats.

**Environment Type**: `SingleTurnEnv` - One prompt, one response per example  
**Task**: Binary classification of network logs  
**Reward Structure**: Multi-criteria scoring based on accuracy and format compliance

## Installation

Install the environment using the Prime CLI:

```bash
prime env install intertwine/sv-env-network-logs
```

Or using pip/uv directly:

```bash
pip install intertwine-sv-env-network-logs
```

## Usage

### With Verifiers Library

```python
import verifiers as vf

# Load the environment
env = vf.load_environment("intertwine/sv-env-network-logs")

# Evaluate a model
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-4-mini",
    num_examples=100
)

print(f"Average reward: {results.stats['mean_reward']:.2%}")
```

### Quick Evaluation

Use the verifiers CLI for quick testing:

```bash
vf-eval intertwine/sv-env-network-logs --model gpt-4-mini --num-examples 10
```

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

Single-word classification:

- `Malicious` - for detected threats
- `Benign` - for normal traffic

### Scoring

The environment uses a weighted multi-criteria rubric:

- **Classification Accuracy** (weight: 1.0): Correct malicious/benign prediction
- **Format Compliance** (weight: 0.2): Proper single-word response format

Total score = weighted combination of both criteria

## Performance Benchmarks

| Model      | Accuracy | Format Score | Overall |
| ---------- | -------- | ------------ | ------- |
| GPT-4-mini | 60.3%    | 100%         | 80.3%   |

Benchmarks on 100 examples from the IoT-23 dataset

## Dataset

The environment uses the [IoT-23 dataset](https://huggingface.co/datasets/19kmunz/iot-23-preprocessed-minimumcolumns), containing real network traffic from IoT devices with labeled malicious and benign connections. A synthetic fallback dataset ensures the environment works even without dataset access.

## Requirements

- Python 3.12+
- `verifiers>=0.1.2`
- API key for model inference (e.g., OpenAI API key)

## About Security Verifiers

Security Verifiers is a suite of cybersecurity-focused RL environments designed to train and evaluate AI models on real-world security tasks. Created by the Intertwine team, these environments cover:

- Network security and anomaly detection
- Phishing and social engineering defense
- Code vulnerability assessment
- Security configuration verification
- Red team/blue team scenarios

For more environments, search for the `security-verifiers` tag on the Prime Intellect Environments Hub.

## Support

For issues or questions about this environment:

- Check the [Security Verifiers repository](https://github.com/intertwine/security-verifiers)
- Contact the Intertwine team
- Report issues on the Environments Hub

## License

Part of the Security Verifiers open-source project. See repository for license details.
