# Prime Lab Integration for Hosted Training and Evaluation

This document defines the GA hosted-training, hosted-evaluation, fallback hosted-style eval, and local eval workflow for SV-Bench E1/E2.

> **Note:** All examples below use `intertwine` as the team slug. Verify yours with `prime whoami`.

## Prerequisites

- A Prime Intellect account with team access
- Prime CLI v0.6.2+ installed in the active project environment and authenticated
- Your team slug (visible in `prime whoami` or your Prime dashboard)
- `OPENAI_API_KEY` available to hosted judge/hybrid runs, either exported locally or stored in a local `.env` file passed with `--env-file`

## 1) Install Prime CLI

```bash
uv tool install prime
```

Verify installation:

```bash
uv run prime --version
# Expected: Prime CLI version: 0.6.2 (or later)
```

## 2) Authentication

Login and verify:

```bash
uv run prime login
uv run prime whoami --plain
```

`prime whoami` should show your authenticated user and team.

## 3) Compatibility gate

Run the automated compatibility check:

```bash
make lab-check
```

This verifies:
- `prime` CLI is installed and current enough for hosted training
- `prime whoami` succeeds (authenticated)
- `prime train` subcommand is available
- `prime eval` subcommand is available

## 4) Available models

Check which models are available for hosted training:

```bash
make prime-models
# or
prime train models --output json --plain
```

To generate a matched launch matrix with a small available model selected from the Prime catalog:

```bash
make prime-plan-research-claim PROFILE=pilot SECRET_ENV_FILE=.env
```

To force a known model:

```bash
make prime-plan-research-claim PROFILE=pilot MODEL=Qwen/Qwen3-4B-Instruct-2507
```

Generated configs and commands are written under `outputs/prime_research_claim/...` and should be treated as run artifacts, not source files.
Judge and hybrid launch commands include `--env-file .env` when `SECRET_ENV_FILE=.env` is provided.

## 5) Hosted training

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
make lab-run-e1 REWARD_SOURCE=llm_judge PRIME_SECRET_FLAGS="--env-file .env"
make lab-run-e1 REWARD_SOURCE=hybrid PRIME_SECRET_FLAGS="--env-file .env"

make lab-run-e2 REWARD_SOURCE=executable
make lab-run-e2 REWARD_SOURCE=llm_judge PRIME_SECRET_FLAGS="--env-file .env"
make lab-run-e2 REWARD_SOURCE=hybrid PRIME_SECRET_FLAGS="--env-file .env"

# Or directly
prime train configs/rl/e1_executable_reward.toml --plain
prime train configs/rl/e2_executable_reward.toml --plain

# Judge/hybrid runs need the OpenAI key in the hosted container.
uv run prime train configs/rl/e1_llm_judge_reward.toml --plain --env-file .env
```

The Make targets automatically add `--env-file .env` for judge/hybrid runs when `.env` contains `OPENAI_API_KEY`; use `PRIME_SECRET_FLAGS` to point at a different secret source.

The config files record model, batch size, learning rate, LoRA settings, reward source, budget group, eval intervals, and environment args. Validate all configs before launch:

```bash
make config-validate
```

## 6) Monitoring training runs

Once a run is launched, monitor it with:

```bash
# View training logs
prime train logs <run-id>

# View training metrics (loss, reward, etc.)
prime train metrics <run-id>

# View sample rollouts
prime train rollouts <run-id>
```

## 7) Environment info

Check that environments are deployed and accessible:

```bash
prime env info intertwine/sv-env-network-logs
prime env info intertwine/sv-env-config-verification
```

## 8) Hosted eval, fallback eval, and local eval

Hosted eval uses Prime platform resources. Fallback hosted-style eval uses `prime eval run`/`vf-eval` wrappers to preserve metadata/report parity when hosted training is unavailable. Local eval uses the repo's Python scripts and writes `outputs/evals/...`.

Use `prime eval run` wrappers when full hosted training is not needed:

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

For claim-grade comparison artifacts, collect only completed runs:

```bash
uv run python scripts/collect_prime_research_claim.py \
  --matrix outputs/prime_research_claim/<run-set>/run_matrix.json \
  --require-completed
uv run svbench_compare_rewards --env e1 \
  --executable outputs/prime_research_claim/<run-set>/artifacts/<executable-run-id>/run_manifest.json \
  --judge outputs/prime_research_claim/<run-set>/artifacts/<judge-run-id>/run_manifest.json \
  --hybrid outputs/prime_research_claim/<run-set>/artifacts/<hybrid-run-id>/run_manifest.json \
  --out results/ablations/reward_source/e1_<run-set>.md
```

Only copy curated artifacts into `results/runs/<run-set>/...` after `--require-completed` succeeds
and `svbench_compare_rewards` accepts the manifests without `--allow-incomplete`.
