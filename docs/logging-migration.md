# Logging Migration Guide

This guide helps you migrate from manual RolloutLogger usage to the new dual-mode logging system with Weave auto-tracing.

## What Changed

### Before (Manual Logging Only)

- Required explicit logger creation and configuration
- Manual passing of logger to environments
- No automatic tracing of Verifiers operations

### After (Dual-Mode System)

- **Primary**: Weave auto-tracing enabled by default
- **Supplementary**: RolloutLogger still available for custom needs
- Zero-configuration logging for most use cases

## Migration Steps

### Step 1: Update Your Imports

**Old Pattern:**

```python
from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment
import verifiers as vf

# Had to manually create logger
logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger)
```

**New Pattern (Automatic):**

```python
# Weave auto-initializes when you import environments
from sv_env_network_logs import load_environment
import verifiers as vf

# Just use - no logger needed for basic tracing!
env = load_environment()
```

### Step 2: Update Configuration

**Old .env:**

```env
OPENAI_API_KEY=...
HF_TOKEN=...
# No Weave configuration
```

**New .env:**

```env
OPENAI_API_KEY=...
HF_TOKEN=...

# Weave auto-tracing (enabled by default)
WEAVE_AUTO_INIT=true
WEAVE_PROJECT=security-verifiers

# Optional: W&B for RolloutLogger
WANDB_API_KEY=...
WANDB_PROJECT=security-verifiers-rl
```

### Step 3: Update Evaluation Scripts

**Old Script:**

```python
#!/usr/bin/env python3
from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment

# Always needed logger
logger = build_rollout_logger({
    "enabled": True,
    "wandb_project": "my-project"
})

env = load_environment(logger=logger)
results = env.evaluate(client, model)

# Manual metric logging
logger.log_metrics({"accuracy": 0.95})
```

**New Script (Simplified):**

```python
#!/usr/bin/env python3
from sv_env_network_logs import load_environment

# Weave traces automatically!
env = load_environment()
results = env.evaluate(client, model)

# Metrics are captured automatically by Weave
```

### Step 4: Keep RolloutLogger for Advanced Use Cases

If you need custom filtering or local analysis, keep using RolloutLogger:

```python
from sv_shared import build_rollout_logger
from sv_env_network_logs import load_environment

# Use RolloutLogger for custom logic
logger = build_rollout_logger({
    "enabled": True,
    "step_filter": lambda e: e.reward < 0.5,  # Only log failures
})

# Both Weave and RolloutLogger work together
env = load_environment(logger=logger)

# Query local events
failures = logger.find_reward_dips(0.3)
```

## Common Migration Scenarios

### Scenario 1: Basic Evaluation Script

**Before:**

```python
from sv_shared import build_rollout_logger
from sv_env_config_verification import load_environment

logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger, include_tools=True)
results = env.evaluate(client, "gpt-4o-mini", num_examples=10)
```

**After:**

```python
from sv_env_config_verification import load_environment

# No logger needed - Weave traces automatically
env = load_environment(include_tools=True)
results = env.evaluate(client, "gpt-4o-mini", num_examples=10)
```

### Scenario 2: Production Monitoring

**Before:**

```python
logger = build_rollout_logger({
    "enabled": True,
    "wandb_enabled": True,
    "wandb_project": "production",
    "default_tags": ["prod", "monitoring"]
})
env = load_environment(logger=logger)
```

**After:**

```python
# Weave for tracing
os.environ["WEAVE_PROJECT"] = "production"

# Keep RolloutLogger for alerts
logger = build_rollout_logger({
    "enabled": True,
    "step_filter": lambda e: e.reward < 0.3,  # Alert on failures
    "default_tags": ["prod", "monitoring"]
})
env = load_environment(logger=logger)
```

### Scenario 3: Local Development

**Before:**

```python
# Had to disable logger manually
logger = build_rollout_logger({"enabled": False})
env = load_environment(logger=logger)
```

**After:**

```python
# Disable Weave for local dev
os.environ["WEAVE_DISABLED"] = "true"

# No logger needed
env = load_environment()
```

### Scenario 4: Custom Metrics

**Before:**

```python
logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger)

# Manual metric logging
for episode in range(100):
    # ... run episode ...
    logger.log_metrics({
        "episode": episode,
        "custom_metric": calculate_metric()
    })
```

**After:**

```python
# Weave captures standard metrics automatically
env = load_environment()

# Use RolloutLogger only for custom metrics
logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger)

for episode in range(100):
    # ... run episode ...
    # Only log custom metrics
    logger.log_metrics({"custom_metric": calculate_metric()})
```

## Backward Compatibility

### All Existing Code Still Works

Your existing code using RolloutLogger continues to work without changes:

```python
# This still works exactly as before
logger = build_rollout_logger({"enabled": True})
env = load_environment(logger=logger)
```

### Gradual Migration

You can migrate gradually:

1. **Phase 1**: Keep existing RolloutLogger code
2. **Phase 2**: Enable Weave auto-tracing via environment variables
3. **Phase 3**: Remove unnecessary RolloutLogger usage
4. **Phase 4**: Keep RolloutLogger only where needed

### Disabling New Features

To maintain old behavior exactly:

```env
# Disable Weave auto-tracing
WEAVE_DISABLED=true
```

## Benefits of Migration

### Immediate Benefits (No Code Changes)

- Automatic tracing of all Verifiers operations
- Comprehensive evaluation metrics
- Token usage tracking
- Latency analysis

### With Minimal Changes

- Cleaner, simpler code
- Better performance (less manual logging)
- Automatic error tracking
- Built-in trace visualization

### Long-term Benefits

- Easier debugging with trace UI
- Automatic dashboard creation
- Integration with W&B ecosystem
- Future features automatically available

## FAQ

### Q: Do I need to change all my code immediately?

**A:** No, existing code continues to work. Weave auto-tracing is additive.

### Q: Can I use both systems together?

**A:** Yes! Weave for automatic tracing, RolloutLogger for custom needs.

### Q: How do I disable Weave if there are issues?

**A:** Set `WEAVE_DISABLED=true` in your environment.

### Q: Will this affect performance?

**A:** Weave auto-tracing has minimal overhead. You may see performance improvements by removing unnecessary manual logging.

### Q: What about my existing W&B dashboards?

**A:** RolloutLogger still sends to W&B if configured. You get both Weave traces and W&B metrics.

## Getting Help

- **Full Documentation**: [Logging Guide](logging-guide.md)
- **Quick Reference**: [Quick Reference Card](logging-quick-reference.md)
- **Issues**: [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)

## Summary

The new dual-mode logging system provides:

1. **Zero-config automatic tracing** via Weave
2. **Backward compatibility** with existing RolloutLogger code
3. **Flexibility** to use both systems together

Most users can simply remove logger creation and get better observability with less code!
