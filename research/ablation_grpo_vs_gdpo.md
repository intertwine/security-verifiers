# Multi-Reward RL Stability Ablations

Hypothesis: security rewards are easier to optimize when components are normalized or decoupled rather than collapsed into one scalar too early.

## Matrix

| Environment | Scalar GRPO | Component normalized | GDPO-style placeholder | Distillation |
|---|---|---|---|---|
| E1 | `configs/ablations/e1_grpo_scalar.toml` | `configs/ablations/e1_component_normalized.toml` | `configs/ablations/e1_gdpo_style.toml` | `configs/ablations/e1_distillation.toml` |
| E2 | `configs/ablations/e2_grpo_scalar.toml` | `configs/ablations/e2_component_normalized.toml` | `configs/ablations/e2_gdpo_style.toml` | `configs/ablations/e2_distillation.toml` |

GDPO-style configs are intentionally marked unsupported until runtime support is confirmed. They should fail validation with a documented unsupported-feature message in any launch tool that requires executable training support.

## Metrics

E1: accuracy, FNR, expected cost, ECE, Brier, abstention, risk coverage.

E2: violation F1, severity-weighted score, patch success, hallucinated findings, tool calls, runtime, and over-fix risk.
