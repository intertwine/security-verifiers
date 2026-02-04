# Baselines

This directory holds baseline configurations used for WP2.

**Baselines**
- `e1_prompt`: prompt-only baseline for E1 (LLM)
- `e1_heuristic`: rule-based baseline for E1 (no LLM)
- `e2_prompt`: tool-first prompt baseline for E2 (LLM + tools)
- `e2_tool_only`: tool-only baseline for E2 (no LLM)

Run all baselines via:
```
make baseline-e1
make baseline-e2
```

Scoreboards are written to `bench/scoreboards/`.
