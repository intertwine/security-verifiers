# Prime Hosted Training Launch Plan: svbench-research-claim-20260515T141203Z

- profile: `pilot`
- model: `Qwen/Qwen3.5-2B`

Run these commands after `make lab-check` reports `hosted-ready`:

```bash
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e1_executable_pilot.toml --plain --yes
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e1_llm_judge_pilot.toml --plain --yes
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e1_hybrid_pilot.toml --plain --yes
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e2_executable_pilot.toml --plain --yes
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e2_llm_judge_pilot.toml --plain --yes
uv run prime train results/runs/svbench-research-claim-20260515T141203Z/configs/e2_hybrid_pilot.toml --plain --yes
```

After each launch, record the returned Prime run ID in `run_matrix.json` before collecting artifacts.
