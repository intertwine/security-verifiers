# SV-Bench v0.1 Technical Report

## 1. What SV-Bench Measures

SV-Bench v0.1 measures E1 network-log classification and E2 tool-grounded config verification.

## 2. Why Executable Rewards for Security

Security tasks often have external evidence: logs, policies, static analyzers, and patch checks. SV-Bench tests whether those executable signals produce better behavior than judge-only reward.

## 3. Environments Included in v0.1

Only E1 and E2 are included. E3-E6 are suite roadmap environments.

## 4. Datasets and Public/Gated Split

Public mini sets support smoke tests. Larger splits may be gated or held out. Red-team corpora are not released in v0.1.

## 5. Metrics

E1 reports detection, calibration, cost, abstention, and risk-coverage metrics. E2 reports finding quality, patch success, clean-pass behavior, hallucination risk, and tool economy.

## 6. Baselines

Baseline artifacts are indexed in `results/v0.1_baselines.md`.

## 7. Hosted RL Runs

Hosted training is indexed in `results/v0.1_training.md`. The `svbench-research-claim-20260515T141203Z` run set contains six completed Prime hosted-training runs:

| Environment | Reward source | Model | Prime run ID | Primary metric |
|---|---|---|---|---:|
| E1 | executable | Qwen/Qwen3.5-2B | `bp6qd19u06wzeqkdrf0h24xx` | `avg@1=1.7850` |
| E1 | llm_judge | Qwen/Qwen3.5-2B | `j1i1ys9rpdcluvtqneql2o4l` | `avg@1=0.4400` |
| E1 | hybrid | Qwen/Qwen3.5-2B | `iiy65ubvx5xwke4dfb9vos64` | `avg@1=1.7900` |
| E2 | executable | Qwen/Qwen3.5-9B | `hu1j9b61il8dydv2bh1aj97d` | `avg@1=0.1571` |
| E2 | llm_judge | Qwen/Qwen3.5-9B | `h4y9hb6fjom4xfbclitb2938` | `avg@1=0.5000` |
| E2 | hybrid | Qwen/Qwen3.5-9B | `hzu95jfm266370x9kr9wwgkz` | `avg@1=1.1571` |

The selected hosted models were current small Prime models that completed within the pilot budget: Qwen/Qwen3.5-2B for E1 and Qwen/Qwen3.5-9B for E2 after hosted signal checks.

## 8. Reward-Source Comparator

Matched-budget comparisons use `uv run svbench_compare_rewards`. The E2 comparison in `results/ablations/reward_source/e2_reward_comparison.md` is the primary research-claim artifact: all variants completed on `intertwine/sv-env-config-verification@0.2.19`, required budget fields match, hosted identity matches, and failed/truncated/no-response rollout counts are zero. On this small hosted pilot (`max_steps=1`), hybrid reward improved `avg@1` by `+1.0000` over executable-only reward and judge-only reward improved `avg@1` by `+0.3429`.

The E1 comparison in `results/ablations/reward_source/e1_reward_comparison.md` is retained as completed hosted evidence but is exploratory. Executable and hybrid used `intertwine/sv-env-network-logs@0.2.15`, while the judge variant used `intertwine/sv-netlogs-judge@0.2.18`; the comparator reports that hosted identity mismatch and requires `--allow-unmatched`.

## 9. Failure Modes and Limitations

Current limitations include hosted-budget availability, Prime CLI drift, E2 patch semantic preservation, and the absence of E3-E6 from the v0.1 benchmark claim.

For E2, hosted scanner execution may use deterministic KubeLinter/Semgrep fallbacks when external binaries are unavailable. The completed `0.2.19` pilot artifacts record this provenance limitation in their run manifests; current environment code emits `tool_backend` on future tool findings so adapter-vs-fallback evidence can be separated directly.

## 10. Reproduction Commands

```bash
make baseline-e1 MODEL=gpt-5-mini N=10
make baseline-e2 MODEL=gpt-5-mini INCLUDE_TOOLS=true N=10
uv run svbench_compare_rewards \
  --env e2 \
  --executable results/runs/svbench-research-claim-20260515T141203Z/hu1j9b61il8dydv2bh1aj97d/run_manifest.json \
  --judge results/runs/svbench-research-claim-20260515T141203Z/h4y9hb6fjom4xfbclitb2938/run_manifest.json \
  --hybrid results/runs/svbench-research-claim-20260515T141203Z/hzu95jfm266370x9kr9wwgkz/run_manifest.json \
  --out results/ablations/reward_source/e2_reward_comparison.md
make svbench-v0.1-check
```
