# Security Verifiers Logging Quick Reference

## 🚀 Quick Start

### Auto-Tracing (Zero Config)

```python
# Just import and use - logging happens automatically!
from sv_env_network_logs import load_environment
env = load_environment()
```

### Custom Logging

```python
from sv_shared import build_rollout_logger
logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger)
```

## ⚙️ Configuration

### Authentication Setup (Required)

```bash
# 1. Get your W&B API key
# Sign up at: https://wandb.ai
# Get key at: https://wandb.ai/authorize

# 2. Set API key (choose one method):
export WANDB_API_KEY=your-key-here    # Shell export
wandb login                            # Interactive login
# Or add to .env file
```

### Environment Variables

```bash
# W&B Authentication (REQUIRED for Weave)
export WANDB_API_KEY=your-key-here

# Weave Auto-Tracing
export WEAVE_AUTO_INIT=true        # Enable auto-tracing (default)
export WEAVE_PROJECT=my-project    # Project name
export WEAVE_DISABLED=true         # Disable if no W&B account

# Additional for RolloutLogger
export WANDB_PROJECT=my-project
export WANDB_ENTITY=my-team
```

### .env File

```env
# Required for Weave
WANDB_API_KEY=your-key-here

# Weave config
WEAVE_AUTO_INIT=true
WEAVE_PROJECT=security-verifiers

# Optional
WANDB_PROJECT=security-verifiers-rl
```

## 📊 Common Patterns

### Production Monitoring

```python
# Both systems for comprehensive monitoring
os.environ["WEAVE_PROJECT"] = "production"

logger = build_rollout_logger({
    "enabled": True,
    "step_filter": lambda e: e.reward < 0.5,  # Focus on failures
    "default_tags": ["production"]
})

env = load_environment(logger=logger)
```

### Local Development

```python
# Disable remote logging
os.environ["WEAVE_DISABLED"] = "true"

logger = build_rollout_logger({
    "enabled": True,
    "weave_enabled": False,
    "wandb_enabled": False
})
```

### Selective Logging

```python
logger = build_rollout_logger({
    "step_filter": lambda e: (
        e.reward < 0.3 or      # Failures
        e.reward > 0.95 or     # Successes
        e.step_index % 100 == 0  # Sample
    )
})
```

### Event Querying

```python
# Find specific events
failures = logger.find_reward_dips(0.5)
critical = logger.query_events(
    lambda e: e.metrics and e.metrics.get("is_critical")
)
```

## 🎯 When to Use What

| Scenario         | Use           | Why                    |
| ---------------- | ------------- | ---------------------- |
| Basic evaluation | Weave Auto    | Zero config needed     |
| Training runs    | Weave Auto    | Comprehensive tracing  |
| Custom metrics   | RolloutLogger | Fine control           |
| Event filtering  | RolloutLogger | Reduce noise           |
| Local debugging  | RolloutLogger | Query offline          |
| Production       | Both          | Complete observability |

## 🔍 Viewing Logs

### Weave Traces

```text
https://wandb.ai/<entity>/<project>/weave
```

### W&B Dashboard

```text
https://wandb.ai/<entity>/<project>
```

### Local Analysis

```python
events = logger.query_events(lambda e: True)
print(f"Total: {len(events)}")
```

## 🐛 Quick Debugging

### No Weave Traces?

```bash
# Check config
echo $WEAVE_DISABLED  # Should be empty or "false"
echo $WEAVE_AUTO_INIT # Should be "true" or empty

# Verify installation
pip list | grep weave
```

### No Logger Events?

```python
# Check enabled
print(logger.enabled)  # Should be True

# Remove filters for testing
logger = build_rollout_logger({
    "step_filter": lambda e: True
})
```

## 📚 Full Documentation

See the [Comprehensive Logging Guide](logging-guide.md) for:

- Detailed configuration options
- Advanced code examples
- Troubleshooting guide
- Best practices
- Custom backends
