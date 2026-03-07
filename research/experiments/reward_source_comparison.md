# WP3c: Executable Verifier vs LLM-Judge Reward Comparison

## Research Question

Does structured multi-component executable verification outperform holistic
LLM-judge binary assessment as a reward source for GRPO-based RL training
on security classification tasks?

## Experimental Setup

### Shared Parameters (Matched Budget)

| Parameter              | Value                          |
|------------------------|--------------------------------|
| Base model             | Qwen/Qwen3-4B-Instruct-2507   |
| Algorithm              | GRPO                           |
| max_steps              | 200                            |
| batch_size             | 32                             |
| rollouts_per_example   | 8                              |
| learning_rate          | 1e-5                           |
| LoRA alpha             | 32 (rank auto-derived: 16)     |
| max_tokens             | 2048                           |
| temperature            | 0.7                            |
| Dataset                | iot23-train-dev-test-v1.jsonl   |
| max_examples (train)   | 200                            |
| max_examples (eval)    | 50                             |
| eval_interval          | 50 steps                       |
| eval_base_model        | true                           |
| buffer seed            | 42                             |
| System prompt          | Identical across both variants |

### Condition A: Executable Verifier (e1.toml)

- **Environment**: `intertwine/sv-env-network-logs`
- **Reward**: Weighted sum of 4 deterministic functions
  - `reward_accuracy` (weight=1.0): Binary match of predicted vs ground truth label
  - `format_reward` (weight=0.1): JSON schema validity (label + confidence fields)
  - `reward_calibration` (weight=0.2): `1.0 - |confidence - correctness|`
  - `reward_asymmetric_cost` (weight=0.5): Penalizes false negatives (-1.0) more than FPs (0.0)
- **Reward range**: [-0.5, 1.8] (weighted sum)
- **Properties**: Deterministic, decomposed, per-dimension gradient signal

### Condition B: LLM-Judge (e1_judge.toml)

- **Environment**: `intertwine/sv-netlogs-judge`
- **Reward**: Single LLM-judge binary assessment
  - `judge_reward` (weight=1.0): 1.0 if judge says "yes", 0.0 otherwise
- **Judge model**: gpt-4.1-nano (cheapest available, ~$0.10/1M tokens)
- **Judge prompt**: Domain-specific evaluation checking correctness, format, calibration
- **Judge sampling**: temperature=0.0, max_tokens=16
- **Reward range**: {0.0, 1.0} (binary)
- **Properties**: Stochastic, holistic, single-dimensional signal

### Launch Commands

```bash
# Condition A: Executable verifier
make lab-run-e1

# Condition B: LLM-judge
make lab-run-e1-judge
```

## Metrics to Compare

### Primary Metrics (from eval intervals)
- Classification accuracy (% correct labels)
- Mean reward over time (learning curves)
- Convergence speed (steps to plateau)

### Secondary Metrics
- Calibration quality (ECE if available from eval logs)
- False negative rate (security-critical metric)
- Reward variance per batch (signal quality indicator)
- Cost per training run (judge API calls vs none)

### Analysis Plan
1. Plot learning curves (mean eval reward vs step) for both conditions
2. Compare final accuracy at step 200
3. Analyze reward distribution shape (binary vs continuous)
4. Compute cost overhead of judge variant
5. Qualitative analysis of failure modes

## Hypotheses

**H1 (Primary)**: The executable verifier will produce higher final accuracy than
the LLM-judge variant because:
- Multi-component rewards provide per-dimension gradient signal
- Deterministic rewards reduce variance in policy gradient estimates
- Asymmetric cost function encodes domain-specific security priorities

**H2 (Secondary)**: The LLM-judge variant will show slower convergence due to:
- Binary reward providing less gradient information per step
- Stochastic judge responses adding noise to reward signal

**H3 (Null)**: If the LLM-judge matches executable verifier performance, it
suggests that reward decomposition may not be necessary for simple classification
tasks, favoring cheaper judge-based approaches for future environments.

## Status

- [x] Environment implementation (environments/sv-env-netlogs-judge/sv_netlogs_judge_impl.py)
- [x] Training config (configs/rl/e1_judge.toml)
- [x] Makefile target (lab-run-e1-judge)
- [x] Deploy judge environment to Hub
- [ ] Run Condition A (executable verifier)
- [ ] Run Condition B (LLM-judge)
- [ ] Collect results and plot learning curves
- [ ] Write analysis

## Files

| File | Purpose |
|------|---------|
| `environments/sv-env-netlogs-judge/sv_netlogs_judge_impl.py` | Judge variant environment |
| `environments/sv-env-network-logs/sv_env_network_logs.py` | Executable verifier environment (baseline) |
| `configs/rl/e1.toml` | Condition A training config |
| `configs/rl/e1_judge.toml` | Condition B training config |
| `research/experiments/reward_source_comparison.md` | This document |
