# Prime CLI Integration for Hosted RL Training (WP3a/WP3b)

This document defines the hosted RL training workflow for SV-Bench E1/E2 using Prime CLI v0.5+.

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
- `configs/rl/e1.toml` — E1 (sv-env-network-logs)
- `configs/rl/e2.toml` — E2 (sv-env-config-verification)

Launch training:

```bash
# Via make
make lab-run-e1
make lab-run-e2

# Or directly
prime rl run configs/rl/e1.toml
prime rl run configs/rl/e2.toml
```

The config files contain all training parameters (model, batch size, learning rate, LoRA settings, eval intervals, etc.) in the flat TOML format expected by `prime rl run`.

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

## 8) Fallback hosted-style eval parity

Use `prime env eval` wrappers when full RL training is not needed:

```bash
make env-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=100
make env-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=intertwine N=50
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
