# Security Verifiers Logging Guide

This guide covers the comprehensive logging capabilities in Security Verifiers, including automatic Weave tracing and the supplementary RolloutLogger system.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Weave Auto-Tracing (Primary)](#weave-auto-tracing-primary)
- [RolloutLogger (Supplementary)](#rolloutlogger-supplementary)
- [Configuration](#configuration)
- [Code Examples](#code-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Security Verifiers provides a dual-mode logging system designed for flexibility and comprehensive observability:

1. **Weave Auto-Tracing**: Automatic, zero-configuration logging that traces all Verifiers operations
2. **RolloutLogger**: Supplementary custom logging for advanced use cases

### When to Use Each System

| Use Case                  | Recommended System | Why                                         |
| ------------------------- | ------------------ | ------------------------------------------- |
| Basic evaluation tracking | Weave Auto-Tracing | Automatic, no code changes needed           |
| Training runs             | Weave Auto-Tracing | Comprehensive tracing out-of-the-box        |
| Custom metrics            | RolloutLogger      | Fine-grained control                        |
| Event filtering           | RolloutLogger      | Filter what gets logged                     |
| Local analysis            | RolloutLogger      | Query events offline                        |
| Production monitoring     | Both               | Weave for tracing, RolloutLogger for alerts |

## Quick Start

### Option 1: Run Without Logging (No Account Needed)

If you don't have a W&B account or want to run without logging:

```bash
# Disable Weave completely
export WEAVE_DISABLED=true

# Run normally - no logging will occur
python scripts/eval_network_logs.py --models gpt-5-mini --num-examples 10
```

### Option 2: Automatic Logging (Recommended)

1. **Get a free W&B account**: Sign up at [wandb.ai](https://wandb.ai)
2. **Get your API key**: Visit [wandb.ai/authorize](https://wandb.ai/authorize)
3. **Set up authentication**:

```bash
# Set your API key
export WANDB_API_KEY=your-api-key-here

# Configure Weave
export WEAVE_AUTO_INIT=true
export WEAVE_PROJECT=my-security-project

# Run your evaluation - logging happens automatically!
python scripts/eval_network_logs.py --models gpt-5-mini --num-examples 10
```

### Option 3: Custom Logging

```python
from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment

# Create logger with custom config
logger = build_rollout_logger({
    "enabled": True,
    "weave_project": "my-project"
})

# Pass to environment
env = load_environment(logger=logger)
```

## Weave Auto-Tracing (Primary)

Weave provides automatic tracing of all Verifiers operations through its [native integration](https://weave-docs.wandb.ai/guides/integrations/verifiers).

### Authentication Requirements

**IMPORTANT**: Weave requires a Weights & Biases (W&B) account and API key to function:

1. **Create an Account**: Sign up at [wandb.ai](https://wandb.ai) (free tier available)
2. **Get Your API Key**: Visit [wandb.ai/authorize](https://wandb.ai/authorize)
3. **Configure Authentication** (choose one):

   **Option A: Environment Variable (Recommended for automation)**

   ```bash
   export WANDB_API_KEY=your-api-key-here
   ```

   **Option B: Interactive Login (for development)**

   ```bash
   wandb login
   # You'll be prompted to paste your API key
   ```

   **Option C: In .env file (for projects)**

   ```env
   WANDB_API_KEY=your-api-key-here
   ```

4. **For Teams**: Use `team-name/project-name` format:

   ```bash
   export WEAVE_PROJECT=my-team/security-verifiers
   ```

### How It Works

When you import any Security Verifiers environment, Weave is automatically initialized and patches the Verifiers library to trace:

- Environment initialization
- Dataset loading
- Model evaluations
- Individual rollout steps
- Reward calculations
- Parser operations

### Configuration

Configure Weave through environment variables:

```bash
# Enable/disable auto-initialization (default: true)
export WEAVE_AUTO_INIT=true

# Set project name (default: security-verifiers)
export WEAVE_PROJECT=my-security-project

# Completely disable Weave
export WEAVE_DISABLED=true  # Overrides all other settings
```

Or in your `.env` file:

```env
WEAVE_AUTO_INIT=true
WEAVE_PROJECT=security-verifiers
# WEAVE_DISABLED=false  # Uncomment to disable
```

### Basic Usage

No code changes needed! Just use environments normally:

```python
# Weave auto-initializes when you import an environment
from sv_env_network_logs import load_environment
import verifiers as vf
from openai import OpenAI

# Load environment - automatically traced
env = load_environment(max_examples=100)

# Run evaluation - automatically traced
client = OpenAI()
results = env.evaluate(
    client,
    "gpt-5-mini",
    num_examples=10,
    rollouts_per_example=2
)

# View traces at: https://wandb.ai/<entity>/<project>/weave
```

### Advanced Usage

For explicit control, initialize Weave manually:

```python
import weave

# Initialize with custom settings
weave.init("my-custom-project")

# Now import verifiers - it will be auto-patched
import verifiers as vf
from sv_env_config_verification import load_environment

# Everything is traced from here
env = load_environment()
```

### Viewing Traces

Access your traces at:

```text
https://wandb.ai/<your-entity>/<project-name>/weave
```

Features available in the Weave UI:

- Trace visualization
- Latency analysis
- Token usage tracking
- Error debugging
- Custom filtering

## RolloutLogger (Supplementary)

The RolloutLogger provides additional custom logging capabilities beyond automatic tracing.

### When to Use RolloutLogger

Use RolloutLogger when you need:

- Custom event filtering (e.g., only log failures)
- Local event storage for offline analysis
- Custom metrics not captured by auto-tracing
- Integration with both Weave and W&B
- Programmatic event queries

### Custom Configuration

Create a logger with custom configuration:

```python
from sv_shared import build_rollout_logger, RolloutLoggingConfig

# Option 1: Using build_rollout_logger helper
logger = build_rollout_logger({
    "enabled": True,
    "weave_enabled": True,
    "wandb_enabled": True,
    "weave_project": "security-verifiers",
    "wandb_project": "security-verifiers-rl",
    "wandb_entity": "my-team",
    "default_tags": ["experiment-1", "security"],
    "step_filter": lambda event: event.reward < 0.5,  # Only log low rewards
    "episode_filter": lambda summary: summary["total_reward"] > 0.8
})

# Option 2: Using RolloutLoggingConfig directly
from sv_shared import RolloutLogger, RolloutLoggingConfig

config = RolloutLoggingConfig(
    enabled=True,
    weave_enabled=True,
    wandb_enabled=True,
    weave_project="security-verifiers",
    wandb_project="security-verifiers-rl",
    default_tags=["production", "v1.0"]
)
logger = RolloutLogger(config)
```

### Basic RolloutLogger Usage

```python
from sv_shared import build_rollout_logger
from sv_env_phishing_detection import load_environment

# Create logger
logger = build_rollout_logger({"enabled": True})

# Pass to environment
env = load_environment(logger=logger)

# Logger automatically captures environment initialization
# Manual logging is also available:

# Log individual steps
logger.log_step(
    episode_id="episode-001",
    step_index=0,
    state={"email_content": "..."},
    action={"classification": "phishing"},
    reward=0.95,
    info={"confidence": 0.92},
    metrics={"processing_time": 0.23}
)

# Log episode summaries
logger.log_episode_summary(
    episode_id="episode-001",
    total_reward=0.95,
    length=1,
    metrics={"accuracy": 0.95, "false_positives": 0}
)

# Log custom metrics
logger.log_metrics(
    {"batch_accuracy": 0.94, "avg_confidence": 0.89},
    step=100
)
```

### Event Querying

Query logged events locally:

```python
# Find all events where reward dropped below threshold
low_rewards = logger.find_reward_dips(threshold=0.3)

# Custom queries
high_confidence_errors = logger.query_events(
    lambda event: (
        event.metrics and
        event.metrics.get("confidence", 0) > 0.9 and
        event.reward < 0.5
    )
)

# Analyze results
for event in high_confidence_errors:
    print(f"Step {event.step_index}: High confidence ({event.metrics['confidence']}) "
          f"but low reward ({event.reward})")
```

## Environment Configuration

### Complete Configuration Example

Create a `.env` file with all logging options:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Weave Auto-Tracing
WEAVE_AUTO_INIT=true
WEAVE_PROJECT=security-verifiers
# WEAVE_DISABLED=false  # Uncomment to disable

# Weights & Biases (for RolloutLogger)
WANDB_API_KEY=...
WANDB_PROJECT=security-verifiers-rl
WANDB_ENTITY=my-team

# HuggingFace (optional)
HF_TOKEN=hf_...
```

Load environment variables:

```bash
# Option 1: Export to shell
set -a && source .env && set +a

# Option 2: Use python-dotenv
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

### Disabling Logging

To completely disable all logging:

```bash
# Disable Weave auto-tracing
export WEAVE_DISABLED=true

# Don't pass logger to environments
env = load_environment()  # No logger parameter
```

## Code Examples

### Example 1: Production Evaluation with Full Logging

```python
"""Production evaluation with comprehensive logging."""

import os
from sv_env_config_verification import load_environment
from sv_shared import build_rollout_logger
from openai import OpenAI

# Configure logging
os.environ["WEAVE_PROJECT"] = "production-security-audit"

# Create supplementary logger for custom metrics
logger = build_rollout_logger({
    "enabled": True,
    "wandb_project": "security-production",
    "default_tags": ["production", "config-audit"],
    "step_filter": lambda e: e.reward < 0.7  # Focus on failures
})

# Load environment with logger
env = load_environment(
    max_examples=100,
    include_tools=True,
    logger=logger
)

# Run evaluation - both Weave and RolloutLogger capture data
client = OpenAI()
results = env.evaluate(
    client,
    "gpt-4o",
    num_examples=50,
    rollouts_per_example=3,
    max_concurrent=8
)

# Query for analysis
failures = logger.find_reward_dips(0.5)
print(f"Found {len(failures)} failed security audits")

# Log summary metrics
logger.log_metrics({
    "total_audits": 50,
    "success_rate": sum(r > 0.7 for r in results) / len(results),
    "avg_reward": sum(results) / len(results)
})
```

### Example 2: Training with Selective Logging

```python
"""RL training with selective event logging."""

from sv_shared import build_rollout_logger
from sv_env_redteam_defense import load_environment
import verifiers as vf

# Configure selective logging
logger = build_rollout_logger({
    "enabled": True,
    "weave_enabled": False,  # Disable Weave for training
    "wandb_enabled": True,   # Use W&B for training metrics
    "wandb_project": "redteam-defense-training",
    "step_filter": lambda e: (
        e.step_index % 100 == 0 or  # Log every 100th step
        e.reward < 0.2 or            # Log failures
        e.reward > 0.95              # Log successes
    )
})

env = load_environment(logger=logger)

# Training loop with selective logging
for episode in range(1000):
    state = env.reset()
    total_reward = 0

    for step in range(env.max_turns):
        action = agent.act(state)
        next_state, reward, done, info = env.step(action)

        # Logger automatically captures based on filter
        logger.log_step(
            episode_id=f"ep-{episode}",
            step_index=step,
            state=state,
            action=action,
            reward=reward,
            info=info,
            metrics={"q_value": agent.get_q_value(state, action)}
        )

        total_reward += reward
        if done:
            break

    # Log episode summary
    logger.log_episode_summary(
        episode_id=f"ep-{episode}",
        total_reward=total_reward,
        length=step + 1,
        metrics={"epsilon": agent.epsilon}
    )
```

### Example 3: Multi-Environment Comparison

```python
"""Compare performance across multiple environments."""

from sv_shared import build_rollout_logger
import importlib

# Environments to compare
ENVIRONMENTS = [
    "sv_env_network_logs",
    "sv_env_phishing_detection",
    "sv_env_code_vulnerability"
]

# Create logger for comparison
logger = build_rollout_logger({
    "enabled": True,
    "weave_project": "security-comparison",
    "default_tags": ["comparison", "benchmark"]
})

results = {}

for env_name in ENVIRONMENTS:
    # Dynamically import environment
    module = importlib.import_module(env_name)
    load_env = getattr(module, "load_environment")

    # Load with shared logger
    env = load_env(max_examples=50, logger=logger)

    # Log environment metadata
    logger.log_environment_init(
        environment_name=env_name,
        dataset_name="benchmark",
        total_examples=50,
        metadata={"comparison_run": True}
    )

    # Run evaluation
    client = OpenAI()
    env_results = env.evaluate(
        client,
        "gpt-5-mini",
        num_examples=50
    )

    results[env_name] = env_results

    # Log comparison metrics
    logger.log_metrics({
        f"{env_name}_avg_reward": sum(env_results) / len(env_results),
        f"{env_name}_success_rate": sum(r > 0.7 for r in env_results) / len(env_results)
    })

# Analyze logged events
all_events = logger.query_events(lambda e: True)
print(f"Total events logged: {len(all_events)}")
```

### Example 4: Debugging with Local Event Analysis

```python
"""Debug evaluation failures using local event querying."""

from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment
import json

# Create logger with all events captured locally
logger = build_rollout_logger({
    "enabled": True,
    "weave_enabled": False,  # No remote logging
    "wandb_enabled": False,  # Keep everything local
})

env = load_environment(logger=logger)

# Run evaluation
results = env.evaluate(client, "gpt-5-mini", num_examples=100)

# Analyze failures locally
failures = logger.query_events(
    lambda e: e.reward is not None and e.reward < 0.5
)

print(f"Found {len(failures)} failures to analyze")

# Detailed failure analysis
for event in failures[:5]:  # Examine first 5 failures
    print(f"\n--- Failure at step {event.step_index} ---")
    print(f"Episode: {event.episode_id}")
    print(f"Reward: {event.reward}")

    if event.state:
        print(f"Input: {event.state.get('prompt', 'N/A')[:100]}...")

    if event.action:
        print(f"Model output: {json.dumps(event.action, indent=2)}")

    if event.info:
        print(f"Error: {event.info.get('error', 'No error details')}")

# Find patterns in failures
high_confidence_failures = logger.query_events(
    lambda e: (
        e.reward is not None and
        e.reward < 0.5 and
        e.action and
        e.action.get("confidence", 0) > 0.8
    )
)

print(f"\nHigh confidence failures: {len(high_confidence_failures)}")
```

## Best Practices

### 1. Use Weave Auto-Tracing by Default

For most use cases, Weave auto-tracing provides sufficient observability:

```python
# Just import and use - no configuration needed!
from sv_env_network_logs import load_environment
env = load_environment()
```

### 2. Add RolloutLogger for Production

In production, combine both systems for comprehensive monitoring:

```python
# Weave for tracing, RolloutLogger for alerts
logger = build_rollout_logger({
    "enabled": True,
    "step_filter": lambda e: e.reward < 0.3,  # Alert on failures
    "default_tags": ["production", "monitoring"]
})
```

### 3. Use Filters to Reduce Noise

Filter events to focus on what matters:

```python
logger = build_rollout_logger({
    "step_filter": lambda e: (
        e.reward < 0.5 or  # Failures
        e.step_index == 0 or  # First steps
        (e.metrics and e.metrics.get("is_critical"))  # Critical events
    )
})
```

### 4. Tag Your Experiments

Use tags for organization:

```python
logger = build_rollout_logger({
    "default_tags": [
        f"model-{model_name}",
        f"dataset-{dataset_version}",
        f"experiment-{experiment_id}",
        "security"
    ]
})
```

### 5. Local Development Settings

For local development, disable remote logging:

```python
# .env.local
WEAVE_DISABLED=true

# Or in code
if os.getenv("ENV") == "local":
    logger = build_rollout_logger({"enabled": False})
else:
    logger = build_rollout_logger({"enabled": True})
```

### 6. Query Before Remote Logging

Use local querying to validate before sending to remote:

```python
# Capture locally first
logger = build_rollout_logger({
    "enabled": True,
    "weave_enabled": False,
    "wandb_enabled": False
})

# Run experiment
# ...

# Analyze locally
interesting_events = logger.query_events(
    lambda e: e.reward > 0.9 or e.reward < 0.1
)

if len(interesting_events) > 0:
    # Now log to remote
    logger._config.weave_enabled = True
    for event in interesting_events:
        logger._log_to_backends(event)
```

## Troubleshooting

### Issue: Weave Not Initializing

**Symptoms**: No traces appearing in Weave UI

**Solutions**:

1. Check W&B authentication:

```bash
# Verify API key is set
echo $WANDB_API_KEY  # Should show your key (or partial)

# If not set, get your key:
# 1. Sign up at https://wandb.ai
# 2. Get key at https://wandb.ai/authorize
# 3. Set it:
export WANDB_API_KEY=your-key-here

# Or login interactively
wandb login
```

1. Check environment variables:

```bash
echo $WEAVE_AUTO_INIT  # Should be "true" or empty
echo $WEAVE_DISABLED   # Should be "false" or empty
```

1. Verify Weave is installed:

```bash
pip list | grep weave
# Should show: weave 0.52.8 or higher
```

1. Check initialization order:

```python
# WRONG - Weave initializes after verifiers import
import verifiers as vf
import weave
weave.init("project")

# CORRECT - Weave initializes before verifiers
import weave
weave.init("project")
import verifiers as vf
```

1. Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from sv_shared import weave_init
# Check console for initialization messages
```

### Issue: RolloutLogger Not Capturing Events

**Symptoms**: No events in local buffer or remote backends

**Solutions**:

1. Verify logger is enabled:

```python
logger = build_rollout_logger({"enabled": True})
print(f"Logger enabled: {logger.enabled}")  # Should be True
```

1. Check filter functions:

```python
# Filters might be too restrictive
logger = build_rollout_logger({
    "step_filter": lambda e: True,  # Accept all events for testing
})
```

1. Ensure logger is passed to environment:

```python
# WRONG
env = load_environment()

# CORRECT
env = load_environment(logger=logger)
```

### Issue: Deprecation Warnings

**Symptoms**: Warnings about Sentry SDK, Pydantic, or GQL

**Solution**: These are from Weave's dependencies and are already suppressed in test configuration. They don't affect functionality.

### Issue: High Memory Usage

**Symptoms**: Memory grows during long evaluations

**Solutions**:

1. Use filters to reduce local buffer size:

```python
logger = build_rollout_logger({
    "step_filter": lambda e: e.step_index % 100 == 0  # Sample events
})
```

1. Clear local buffer periodically:

```python
# After processing events
logger._events.clear()
```

1. Disable local buffering:

```python
class StreamOnlyLogger(RolloutLogger):
    def log_step(self, **kwargs):
        # Skip local storage
        if self._config.step_filter and not self._config.step_filter(event):
            return
        self._log_to_backends(payload)
```

### Issue: Authentication Errors

**Symptoms**: Can't connect to Weave or W&B, or errors like "Not logged in"

**Solutions**:

1. Ensure W&B account exists:

```bash
# Sign up for free account at:
https://wandb.ai

# Get your API key at:
https://wandb.ai/authorize
```

1. Check API key configuration:

```bash
# Method 1: Environment variable
export WANDB_API_KEY=your-key-here

# Method 2: Interactive login
wandb login
# Paste your key when prompted

# Method 3: .env file
echo "WANDB_API_KEY=your-key-here" >> .env
source .env
```

1. Verify authentication:

```bash
# Check if key is set
echo $WANDB_API_KEY

# Test connection
python -c "import wandb; wandb.login()"
```

1. For CI/CD environments:

```yaml
# GitHub Actions
env:
  WANDB_API_KEY: ${{ secrets.WANDB_API_KEY }}

# GitLab CI
variables:
  WANDB_API_KEY: $WANDB_API_KEY
```

1. Verify project permissions:

```python
# Test connection
import wandb
wandb.init(project="test-project")

import weave
weave.init("test-project")
```

## Advanced Topics

### Custom Backends

Extend RolloutLogger for custom backends:

```python
from sv_shared import RolloutLogger

class CustomLogger(RolloutLogger):
    def _log_to_backends(self, payload):
        # Call parent implementation
        super()._log_to_backends(payload)

        # Add custom backend
        if self._custom_backend:
            self._custom_backend.send(payload)
```

### Async Logging

For high-throughput scenarios:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncLogger(RolloutLogger):
    def __init__(self, config):
        super().__init__(config)
        self._executor = ThreadPoolExecutor(max_workers=2)

    def log_step(self, **kwargs):
        # Log asynchronously
        self._executor.submit(super().log_step, **kwargs)
```

### Integration with Monitoring

Connect to monitoring systems:

```python
from prometheus_client import Counter, Histogram

# Metrics
evaluation_counter = Counter('evaluations_total', 'Total evaluations')
reward_histogram = Histogram('reward_distribution', 'Reward distribution')

class MonitoringLogger(RolloutLogger):
    def log_step(self, **kwargs):
        super().log_step(**kwargs)

        # Update metrics
        evaluation_counter.inc()
        if kwargs.get('reward'):
            reward_histogram.observe(kwargs['reward'])
```

## References

- [Weave Documentation](https://weave-docs.wandb.ai/)
- [Weave Verifiers Integration](https://weave-docs.wandb.ai/guides/integrations/verifiers)
- [W&B Documentation](https://docs.wandb.ai/)
- [Security Verifiers README](../README.md)
- [Environment Configuration](../.env.example)

## Support

For issues or questions:

- GitHub Issues: [security-verifiers/issues](https://github.com/intertwine/security-verifiers/issues)
- Weave Support: [W&B Support](https://wandb.ai/support)
