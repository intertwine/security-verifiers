# security-verifiers-utils

Shared utilities and components for Security Verifiers RL environments.

## Overview

This package provides common functionality used across all Security Verifiers environments, including:

- **Dataset Loading**: Multi-tiered dataset loading with automatic fallback (local → HuggingFace → synthetic)
- **Response Parsing**: Strict JSON schema validation for classification outputs
- **Reward Functions**: Reusable reward components for accuracy, calibration, and asymmetric costs
- **Logging**: Structured rollout logging with Weave and Weights & Biases integration
- **Weave Integration**: Automatic tracing initialization for Verifiers operations

## Installation

```bash
pip install security-verifiers-utils
# or with uv
uv add security-verifiers-utils
```

## Usage

### Dataset Loading

```python
from sv_shared import load_dataset_with_fallback, DatasetSource

# Automatic fallback: local → hub → synthetic
dataset = load_dataset_with_fallback(
    dataset_name="my-dataset.jsonl",
    local_path="./data",
    hf_repo="org/repo",
    dataset_source="auto",  # or "local", "hub", "synthetic"
    synthetic_factory=lambda: [{"example": "data"}],
    max_examples=1000,
)
```

### Response Parsing

```python
from sv_shared import JsonClassificationParser

parser = JsonClassificationParser(
    allowed_labels=["Benign", "Malicious", "Abstain"]
)

# Parse and validate JSON response
result = parser(response)
# Returns: {"label": str, "confidence": float, "rationale": str}
# Or None if invalid
```

### Reward Functions

```python
from sv_shared import (
    reward_accuracy,
    reward_calibration,
    reward_asymmetric_cost,
)

# Accuracy reward (0.0 to 1.0)
acc_reward = reward_accuracy(
    predicted="Malicious",
    ground_truth="Malicious",
    abstain_label="Abstain"
)

# Calibration reward (encourages well-calibrated confidence)
cal_reward = reward_calibration(
    predicted="Malicious",
    ground_truth="Malicious",
    confidence=0.85,
    abstain_label="Abstain"
)

# Asymmetric cost (penalizes false negatives more than false positives)
cost_reward = reward_asymmetric_cost(
    predicted="Benign",
    ground_truth="Malicious",
    fn_cost=10.0,  # False negative cost
    fp_cost=1.0,   # False positive cost
    abstain_label="Abstain"
)
```

### Rollout Logging

```python
from sv_shared import build_rollout_logger

# Build logger with Weave and W&B backends
logger = build_rollout_logger({
    "weave_project": "my-project",
    "wandb_project": "my-project",
    "wandb_entity": "my-org",
})

# Use with environment
env = load_environment(logger=logger)
```

### Weave Auto-tracing

```python
# Import before verifiers to enable automatic tracing
from sv_shared import weave_init  # Initializes Weave if enabled
import verifiers as vf

# Configure via environment variables:
# WEAVE_AUTO_INIT=true/false (default: true)
# WEAVE_PROJECT=<name> (default: security-verifiers)
# WEAVE_DISABLED=true/false
```

## Components

### Dataset Loader (`dataset_loader.py`)

- `load_dataset_with_fallback()` - Multi-tiered dataset loading
- `DatasetSource` - Type alias for dataset source modes
- `DEFAULT_E1_HF_REPO`, `DEFAULT_E2_HF_REPO` - Default HuggingFace repositories

### Parsers (`parsers.py`)

- `JsonClassificationParser` - Validates JSON classification outputs with strict schema adherence

### Rewards (`rewards.py`)

- `reward_accuracy()` - Classification accuracy reward
- `reward_calibration()` - Confidence calibration reward
- `reward_asymmetric_cost()` - Asymmetric false positive/negative costs

### Rollout Logging (`rollout_logging.py`)

- `RolloutLogger` - Base logger class
- `build_rollout_logger()` - Factory for creating loggers with backends
- `RolloutLoggingConfig` - Configuration dataclass
- `DEFAULT_ROLLOUT_LOGGING_CONFIG` - Default configuration

### Weave Initialization (`weave_init.py`)

- `initialize_weave_if_enabled()` - Conditional Weave initialization
- Automatic tracing setup for Verifiers

### Utilities (`utils.py`)

- `get_response_text()` - Extract text from Verifiers response objects

## Development

### Setup

```bash
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers/sv_shared
uv venv && source .venv/bin/activate
uv sync --extra dev
```

### Testing

```bash
pytest
```

### Linting

```bash
ruff check .
ruff format .
```

## Environment Variables

- `WEAVE_AUTO_INIT` - Enable/disable automatic Weave initialization (default: `true`)
- `WEAVE_PROJECT` - Weave project name (default: `security-verifiers`)
- `WEAVE_DISABLED` - Completely disable Weave (default: `false`)
- `WANDB_API_KEY` - Weights & Biases API key (required for W&B logging)
- `HF_TOKEN` - HuggingFace token (required for private dataset access)

## License

MIT License - see LICENSE file for details.

## Links

- **Repository**: <https://github.com/intertwine/security-verifiers>
- **Issues**: <https://github.com/intertwine/security-verifiers/issues>
- **Documentation**: <https://github.com/intertwine/security-verifiers/blob/main/README.md>

## Related Packages

- [verifiers](https://pypi.org/project/verifiers/) - Core Verifiers RL framework
- [sv-env-network-logs](https://pypi.org/project/sv-env-network-logs/) - Network log anomaly detection environment
- [sv-env-config-verification](https://pypi.org/project/sv-env-config-verification/) - Configuration security verification environment
