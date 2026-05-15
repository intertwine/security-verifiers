# E2 Reward Source Plan

E2 is the full tool-use comparator for SV-Bench v0.1.

| Variant | Config | Reward |
|---|---|---|
| Executable | `configs/rl/e2_executable_reward.toml` | OPA, KubeLinter, Semgrep, and patch verifier primary. |
| LLM judge | `configs/rl/e2_llm_judge_reward.toml` | Judge-only final answer scoring after schema validation. |
| Hybrid | `configs/rl/e2_hybrid_reward.toml` | Executable primary with judge tie-breaks for explanation quality/severity. |

Launch wrappers:

```bash
make lab-run-e2 REWARD_SOURCE=executable
make lab-run-e2 REWARD_SOURCE=llm_judge
make lab-run-e2 REWARD_SOURCE=hybrid
```

The multi-turn budget is explicit in `configs/rl/e2_matched_budget_base.toml`: max turns, tool budget, allowed tools, timeouts, sandbox mode, and failure handling.
