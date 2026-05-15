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

Hosted training is indexed in `results/v0.1_training.md` after real runs complete.

## 8. Reward-Source Comparator

Matched-budget comparisons use `uv run svbench_compare_rewards`.

## 9. Failure Modes and Limitations

Current limitations include hosted-budget availability, Prime CLI drift, E2 patch semantic preservation, and the absence of E3-E6 from the v0.1 benchmark claim.

## 10. Reproduction Commands

```bash
make baseline-e1 MODEL=gpt-5-mini N=10
make baseline-e2 MODEL=gpt-5-mini INCLUDE_TOOLS=true N=10
make svbench-v0.1-check
```
