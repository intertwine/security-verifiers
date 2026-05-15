# Prime Lab Integration for Hosted RL Training and Evaluation

This document defines the GA hosted-training, hosted-evaluation, fallback hosted-style eval, and local eval workflow for SV-Bench E1/E2.

> **Note:** All examples below use `intertwine` as the team slug. Verify yours with `prime whoami`.

## Prerequisites

- A Prime Intellect account with team access
- Prime CLI v0.5+ installed and authenticated
- Your team slug (visible in `prime whoami` or your Prime dashboard)

## 1) Install Prime CLI

```bash
uv tool install prime
```

Verify installation:

```bash
prime --version
# Expected: prime 0.5.41 (or later)
```

## 2) Authentication

Login and verify:

```bash
prime login
prime whoami
```

`prime whoami` should show your authenticated user and team.

## 3) Compatibility gate

Run the automated compatibility check:

```bash
make lab-check
```

This verifies:
- `prime` CLI is installed and >= v0.5.0
- `prime whoami` succeeds (authenticated)
- `prime rl` subcommand is available
- `prime env` subcommand is available

## 4) Available models

Check which models are available for hosted RL training:

```bash
prime rl models
```

## 5) Hosted RL training

Training configs are in `configs/rl/`:
- `configs/rl/e1_executable_reward.toml`
- `configs/rl/e1_llm_judge_reward.toml`
- `configs/rl/e1_hybrid_reward.toml`
- `configs/rl/e2_executable_reward.toml`
- `configs/rl/e2_llm_judge_reward.toml`
- `configs/rl/e2_hybrid_reward.toml`

Launch training:

```bash
make lab-run-e1 REWARD_SOURCE=executable
make lab-run-e1 REWARD_SOURCE=llm_judge
make lab-run-e1 REWARD_SOURCE=hybrid

make lab-run-e2 REWARD_SOURCE=executable
make lab-run-e2 REWARD_SOURCE=llm_judge
make lab-run-e2 REWARD_SOURCE=hybrid

# Or directly
prime rl run configs/rl/e1_executable_reward.toml
prime rl run configs/rl/e2_executable_reward.toml
```

The config files record model, batch size, learning rate, LoRA settings, reward source, budget group, eval intervals, and environment args. Validate all configs before launch:

```bash
make config-validate
```

## 6) Monitoring training runs

Once a run is launched, monitor it with:

```bash
# View training logs
prime rl logs <run-id>

# View training metrics (loss, reward, etc.)
prime rl metrics <run-id>

# View sample rollouts
prime rl rollouts <run-id>
```

## 7) Environment info

Check that environments are deployed and accessible:

```bash
prime env info intertwine/sv-env-network-logs
prime env info intertwine/sv-env-config-verification
```

## 8) Hosted eval, fallback eval, and local eval

Hosted eval uses Prime platform resources. Fallback hosted-style eval uses `prime env eval`/`vf-eval` wrappers to preserve metadata/report parity when hosted training is unavailable. Local eval uses the repo's Python scripts and writes `outputs/evals/...`.

Use `prime env eval` wrappers when full RL training is not needed:

```bash
make env-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=100
make env-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=50
```

Local eval:

```bash
make eval-e1 MODELS=gpt-5-mini N=10
make eval-e2 MODELS=gpt-5-mini INCLUDE_TOOLS=true N=2
```

## 9) Metadata normalization for report pipeline

Normalize hosted metadata into SV-Bench schema:

```bash
python scripts/normalize_hosted_eval.py \
  --input hosted/metadata.json \
  --output outputs/evals/<run-id>/metadata.json \
  --environment sv-env-network-logs \
  --dataset public-mini-e1
```

Expected normalized fields include `run_id`, model/revision, dataset revision, platform metadata, and git SHA.

Every reportable hosted, fallback-hosted, or local run should produce or be paired with a run manifest:

```bash
uv run svbench_manifest validate results/runs/<id>/run_manifest.json
```
