# Security Configuration Verification (E2)

A tool-using RL environment for training and evaluating models on infrastructure configuration auditing. Models analyze Kubernetes and Terraform configurations, detect security violations using real security tools, and generate patches to fix issues.

## Overview

This environment implements end-to-end configuration security auditing with tool grounding, combining static analysis tools with intelligent patch generation and validation.

**Environment Type**: `ToolEnv` - Multi-turn environment with tool access
**Task**: Detect security violations and generate fixes for infrastructure configurations
**Tools**: OPA (Open Policy Agent), KubeLinter, Semgrep
**Reward Structure**: Severity-weighted detection accuracy + successful patch generation

## Dataset Access

**Public Metadata**: Browse sampling information, dataset composition, and tool versions at:

- <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata>

**Full Dataset**: Private to prevent training contamination. Request access via:

- [GitHub Issues](https://github.com/intertwine/security-verifiers/issues) with title "Dataset Access Request: E2"
- Include: name, affiliation, research purpose, HuggingFace username

The public metadata repo includes detailed model cards explaining the privacy rationale, tool versions (KubeLinter, Semgrep, OPA), and dataset composition. Multi-turn evaluation shows models achieve ~0.93 reward with tool calling vs ~0.62 without tools.

### Dataset Loading Strategies

This environment supports **multi-tiered dataset loading** for flexibility across different deployment scenarios:

1. **Local datasets** (built with `make data-e2-local`)
2. **HuggingFace Hub** (with `HF_TOKEN` authentication)
3. **Builtin fixtures** (for testing without data dependencies)

#### Loading Modes

```python
import verifiers as vf

# Auto mode (default): Try local → hub → builtin
env = vf.load_environment("sv-env-config-verification")

# Local only: Require local dataset
env = vf.load_environment("sv-env-config-verification", dataset_source="local")

# Hub only: Load from HuggingFace
env = vf.load_environment("sv-env-config-verification", dataset_source="hub")

# Synthetic only: Use builtin fixtures (no data needed)
env = vf.load_environment("sv-env-config-verification", dataset_source="synthetic")

# Select specific dataset
env = vf.load_environment(
    "sv-env-config-verification",
    dataset_name="k8s-labeled-v1.jsonl",  # Kubernetes only
    dataset_source="local"
)
```

#### Using Your Own HuggingFace Repository

If you've built and pushed datasets to your own HuggingFace repository:

```python
import os

# Configure custom repository
os.environ["HF_TOKEN"] = "hf_your_token_here"
os.environ["E2_HF_REPO"] = "your-org/security-verifiers-e2-private"

# Load from your repository
env = vf.load_environment(
    "sv-env-config-verification",
    dataset_source="hub",
    max_examples=100
)
```

**See [docs/user-dataset-guide.md](../../docs/user-dataset-guide.md) for instructions on building and pushing datasets to your own HuggingFace repository.**

## Installation

Install the environment using the Prime CLI:

```bash
prime env install intertwine/sv-env-config-verification
```

Or using pip directly:

```bash
pip install sv-env-config-verification
```

### Tool Dependencies

This environment requires security scanning tools. Install them based on your platform:

**macOS:**

```bash
# Install kube-linter
brew install kube-linter

# Install OPA
brew install opa

# Install Semgrep
brew install semgrep
```

**Linux/Other:**

```bash
# Install kube-linter
wget https://github.com/stackrox/kube-linter/releases/download/v0.6.8/kube-linter-linux.tar.gz
tar xzf kube-linter-linux.tar.gz
sudo mv kube-linter /usr/local/bin/

# Install OPA
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod 755 opa
sudo mv opa /usr/local/bin/

# Install Semgrep
pip install semgrep
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
env = vf.load_environment("intertwine/sv-env-config-verification", include_tools=True)

# Evaluate a model
results = env.evaluate(
    client=vf.OpenAIClient(),
    model="gpt-5-mini",
    num_examples=10
)

print(f"Average reward: {results.stats['mean_reward']:.2%}")
print(f"Detection F1: {results.stats.get('detection_f1', 0):.2%}")
```

### Quick Evaluation

Use the verifiers CLI:

```bash
# Basic evaluation
vf-eval intertwine/sv-env-config-verification \
  --model gpt-5-mini \
  --num-examples 10

# Evaluation without tools (model must detect issues directly)
vf-eval intertwine/sv-env-config-verification \
  --model gpt-5-mini \
  --num-examples 10 \
  --include-tools false
```

### Training with Prime RL

```toml
[environment]
id = "intertwine/sv-env-config-verification"
kwargs = {include_tools = true}
```

## Task Details

### Input Format

Infrastructure configuration files (Kubernetes YAML or Terraform HCL):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        runAsUser: 0 # Security violation: running as root
```

### Expected Output

JSON object with detected violations and optional patches:

```json
{
  "violations": [
    {
      "type": "RunAsRoot",
      "severity": "HIGH",
      "location": "spec.containers[0].securityContext",
      "description": "Container runs as root user"
    }
  ],
  "patch": "spec:\n  containers:\n  - securityContext:\n      runAsUser: 1000",
  "confidence": 0.95
}
```

### Available Tools

When `include_tools=True`, the model has access to:

1. **run_kubelinter**: Analyze Kubernetes manifests for security issues
2. **run_opa**: Policy-based security validation
3. **run_semgrep**: Static analysis for configuration vulnerabilities

### Scoring

The environment uses a multi-component rubric:

- **Detection Accuracy**: Precision, recall, and F1 for finding violations
- **Severity Weighting**: Higher rewards for catching critical issues
- **Patch Success**: Bonus for generating fixes that resolve violations
- **Format Compliance**: Valid JSON schema adherence

## Weights & Biases Logging

This environment supports automatic Weave tracing:

```python
import weave
import verifiers as vf

# Initialize Weave
weave.init(project="config-security")

# Load and evaluate
env = vf.load_environment("intertwine/sv-env-config-verification", include_tools=True)
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

- **Detection Precision**: Correct violation identification rate
- **Detection Recall**: Coverage of actual violations
- **Detection F1**: Harmonic mean of precision and recall
- **Severity Accuracy**: Proper severity classification
- **Patch Success Rate**: Percentage of successful fixes
- **Tool Utilization**: Effective use of available security scanners

### Example Evaluation Script

```python
import verifiers as vf
import weave

weave.init(project="config-audit-eval")

env = vf.load_environment("intertwine/sv-env-config-verification", include_tools=True)

# Compare with and without tools
for use_tools in [True, False]:
    results = env.evaluate(
        client=vf.OpenAIClient(),
        model="gpt-5-mini",
        num_examples=100,
        include_tools=use_tools,
        seed=42
    )

    mode = "with tools" if use_tools else "without tools"
    print(f"\nResults {mode}:")
    print(f"  Mean Reward: {results.stats['mean_reward']:.2%}")
    print(f"  Detection F1: {results.stats.get('detection_f1', 0):.2%}")
    print(f"  Patch Success: {results.stats.get('patch_success', 0):.2%}")
```

## Early Failure Detection

All E2 evaluation scripts support early stopping to prevent wasted API costs on misconfigured models or API issues:

```bash
# Multi-turn evaluation (default: stop after 3 consecutive errors)
python scripts/eval_config_verification.py \
  --models "gpt-5-mini" \
  --num-examples 100 \
  --max-consecutive-errors 3

# Disable early stopping (process all examples regardless of errors)
python scripts/eval_config_verification.py \
  --models "experimental-model" \
  --num-examples 50 \
  --max-consecutive-errors 0

# Single-turn evaluation with custom threshold
python scripts/eval_config_verification_singleturn.py \
  --models "gpt-5-mini" \
  --num-examples 100 \
  --max-consecutive-errors 5
```

**Via Makefile:**

```bash
# Use default threshold (3 errors)
make eval-e2 MODELS="gpt-5-mini" N=100

# Custom threshold
make eval-e2 MODELS="gpt-5-mini" N=100 MAX_CONSECUTIVE_ERRORS=5

# Disable early stopping
make eval-e2 MODELS="test-model" N=50 MAX_CONSECUTIVE_ERRORS=0
```

The early stopping system tracks consecutive API/completion errors and halts evaluation when the threshold is reached, saving time and costs. Tool execution failures are not counted toward the error threshold - only API-level errors trigger early stopping.

## Performance Benchmarks

| Model       | Detection F1 | Patch Success | With Tools | Overall |
| ----------- | ------------ | ------------- | ---------- | ------- |
| GPT-4o-mini | 72%          | 45%           | Yes        | 68%     |
| GPT-4o-mini | 51%          | 28%           | No         | 44%     |

## Dataset

The environment includes:

- **Kubernetes manifests**: Deployments, Services, ConfigMaps with security issues
- **Terraform configurations**: AWS, GCP, Azure resources with misconfigurations
- **Oracle labels**: Ground-truth violations from tool outputs for validation

## Future Improvements

- **Expanded Tool Suite**: Add Checkov, Terrascan, and Trivy
- **Custom Policies**: Support for organization-specific security rules
- **Multi-file Analysis**: Cross-file dependency and security analysis
- **Incremental Patching**: Iterative refinement of fixes based on re-scanning
- **Compliance Frameworks**: Map violations to CIS, NIST, PCI-DSS standards
- **Explanation Generation**: Require detailed rationale for each violation

## Requirements

- Python 3.12+
- `verifiers>=0.1.4`
- Security scanning tools (kube-linter, opa, semgrep)
- API key for model inference

## About

This environment is part of the Open Security Verifiers suite - a collection of security and alignment RL environments using Prime Intellect's Verifiers framework. Each environment provides executable, programmatic rewards for training robust security-aware AI systems.

## Support

For issues or questions:

- Report issues on the [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- Check the [Security Verifiers GitHub repository](https://github.com/intertwine/security-verifiers)
- Contact the Intertwine team
