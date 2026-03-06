# Network Logs Judge Variant (WP3c)

This is the short-name Hub package for the E1 LLM-judge variant.

Why this package exists:
- Prime RL truncates long environment names when deriving Kubernetes labels.
- The original env id `sv-env-network-logs-judge` truncates to `sv-env-network-logs-`, which is invalid because it ends with `-`.
- This package publishes the same judge environment under the shorter env id `sv-netlogs-judge`.

Install:
- `prime env install intertwine/sv-netlogs-judge`

Usage:
- `from verifiers import load_environment`
- `env = load_environment("sv-netlogs-judge")`

The environment reuses the same dataset, parser, and judge reward logic as the original E1 judge implementation.
