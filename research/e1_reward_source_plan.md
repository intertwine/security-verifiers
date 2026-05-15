# E1 Reward Source Plan

Use E1 as the cheapest matched-budget reward-source comparison.

| Variant | Config | Reward |
|---|---|---|
| Executable | `configs/rl/e1_executable_reward.toml` | Deterministic label, calibration, abstention, and asymmetric cost. |
| LLM judge | `configs/rl/e1_llm_judge_reward.toml` | Judge score with strict schema validation. |
| Hybrid | `configs/rl/e1_hybrid_reward.toml` | Executable primary reward plus low-weight explanation-quality judge. |

Launch wrappers:

```bash
make lab-run-e1 REWARD_SOURCE=executable
make lab-run-e1 REWARD_SOURCE=llm_judge
make lab-run-e1 REWARD_SOURCE=hybrid
```

Run manifests must record `reward_source`, `reward_config_id`, `reward_config_hash`, and budget fields before results are used in a report.
