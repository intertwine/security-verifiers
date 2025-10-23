# Phishing Detection with Evidence

A tool-using RL environment for training and evaluating models on phishing detection with evidence-based reasoning. Models analyze emails for phishing indicators, search for corroborating evidence, and provide justified classifications.

## Overview

This environment implements evidence-seeking phishing detection, combining content analysis with external validation tools to identify and explain phishing attempts.

**Environment Type**: `ToolEnv` - Multi-turn environment with tool access
**Task**: Classify emails as phishing/legitimate with evidence-based justification
**Tools**: URL reputation checker, domain WHOIS lookup, content similarity search
**Reward Structure**: Classification accuracy + evidence quality + explanation coherence

## Installation

Install the environment using the Prime CLI:

```bash
prime env install intertwine/sv-env-phishing-detection
```

Or using pip directly:

```bash
pip install sv-env-phishing-detection
```

## Setup

### API Keys Configuration

Set your API keys as environment variables:

```bash
# OpenAI API Key (required for OpenAI models)
export OPENAI_API_KEY="your-openai-api-key"

# For persistent configuration
echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

### With Verifiers Library

```python
import verifiers as vf

# Load the environment with tools enabled
env = vf.load_environment("intertwine/sv-env-phishing-detection", include_tools=True)

# Evaluate a model
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-5-mini",
    num_examples=10
)

print(f"Average reward: {results.stats['mean_reward']:.2%}")
print(f"Detection accuracy: {results.stats.get('accuracy', 0):.2%}")
```

### Quick Evaluation

Use the verifiers CLI:

```bash
# Basic evaluation with tools
vf-eval intertwine/sv-env-phishing-detection \
  --model gpt-5-mini \
  --num-examples 10

# Without tools (content analysis only)
vf-eval intertwine/sv-env-phishing-detection \
  --model gpt-5-mini \
  --num-examples 10 \
  --include-tools false
```

### Training with Prime RL

```toml
[environment]
id = "intertwine/sv-env-phishing-detection"
kwargs = {include_tools = true}
```

## Task Details

### Input Format

Email content with headers and body:

```text
From: security@amaz0n-support.com
Subject: Urgent: Account Security Alert
Body: Your Amazon account has been compromised. Click here to secure it: http://bit.ly/secure-amz
```

### Expected Output

JSON object with classification and evidence:

```json
{
  "label": "Phishing",
  "confidence": 0.95,
  "evidence": [
    "Spoofed sender domain (amaz0n-support.com vs amazon.com)",
    "Suspicious URL shortener (bit.ly)",
    "Urgency tactics in subject line"
  ],
  "explanation": "Email exhibits multiple phishing indicators including domain spoofing and social engineering tactics"
}
```

### Available Tools

When `include_tools=True`, the model has access to:

1. **check_url_reputation**: Analyze URL safety and reputation
2. **lookup_domain_whois**: Get domain registration details
3. **search_similar_campaigns**: Find similar phishing patterns
4. **verify_sender_authenticity**: Check SPF/DKIM records

### Scoring

The environment uses a weighted rubric:

- **Classification Accuracy** (50%): Correct phishing/legitimate determination
- **Evidence Quality** (30%): Relevant and verifiable indicators
- **Explanation Coherence** (10%): Clear reasoning from evidence
- **Tool Utilization** (10%): Effective use of verification tools

## Weights & Biases Logging

This environment supports automatic Weave tracing:

```python
import weave
import verifiers as vf

# Initialize Weave
weave.init(project="phishing-detection")

# Load and evaluate
env = vf.load_environment("intertwine/sv-env-phishing-detection", include_tools=True)
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-5-mini",
    num_examples=50
)

# Results automatically traced to W&B
```

Configure via environment variables:
- `WEAVE_PROJECT`: Set project name
- `WEAVE_DISABLED`: Set to 'true' to disable logging
- `WANDB_API_KEY`: Your W&B API key

## Evaluation Approach

### Metrics Tracked
- **Detection Accuracy**: Phishing vs legitimate classification
- **False Positive Rate**: Legitimate emails marked as phishing
- **False Negative Rate**: Phishing emails missed (critical metric)
- **Evidence Precision**: Validity of cited indicators
- **Response Time**: Tool usage efficiency

### Example Evaluation Script

```python
import verifiers as vf
import weave

weave.init(project="phishing-eval")

env = vf.load_environment("intertwine/sv-env-phishing-detection", include_tools=True)

# Evaluate with focus on reducing false negatives
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-5-mini",
    num_examples=200,
    seed=42
)

print(f"Mean Reward: {results.stats['mean_reward']:.2%}")
print(f"Accuracy: {results.stats.get('accuracy', 0):.2%}")
print(f"False Positives: {results.stats.get('false_positive_rate', 0):.2%}")
print(f"False Negatives: {results.stats.get('false_negative_rate', 0):.2%}")
```

## Performance Benchmarks

| Model       | Accuracy | False Positives | False Negatives | Overall |
|-------------|----------|-----------------|-----------------|---------|
| GPT-4o-mini | 87%      | 8%              | 5%              | 82%     |
| GPT-4o      | 93%      | 4%              | 3%              | 89%     |

## Phishing Tactics Covered

The environment includes diverse phishing techniques:

- **Domain Spoofing**: Lookalike domains, homoglyphs
- **URL Obfuscation**: Shorteners, redirects, embedded links
- **Social Engineering**: Urgency, authority, scarcity tactics
- **Credential Harvesting**: Fake login pages, form requests
- **Attachment Threats**: Malicious documents, executables
- **Business Email Compromise**: CEO fraud, invoice scams

## Dataset

- **Phishing Samples**: Real-world inspired phishing emails
- **Legitimate Emails**: Business, personal, and marketing emails
- **Evidence Database**: Known phishing domains, campaigns
- **Validation Data**: SPF/DKIM records, WHOIS information

## Future Improvements

- **Attachment Analysis**: Scan documents and executables for threats
- **Multi-language Support**: Detect phishing in non-English emails
- **Real-time Threat Intelligence**: Integration with threat feeds
- **User Context**: Personalized detection based on user patterns
- **Campaign Tracking**: Link related phishing attempts
- **Automated Response**: Generate warning messages and remediation steps

## Requirements

- Python 3.12+
- `verifiers>=0.1.4`
- API key for model inference

## About

This environment is part of the Open Security Verifiers suite - a collection of security and alignment RL environments using Prime Intellect's Verifiers framework. Each environment provides executable, programmatic rewards for training robust security-aware AI systems.

## Support

For issues or questions:
- Report issues on the [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- Check the [Security Verifiers GitHub repository](https://github.com/intertwine/security-verifiers)
- Contact the Intertwine team
