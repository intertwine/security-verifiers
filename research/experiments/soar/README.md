# SOAR Experiments: Self-Optimization via Asymmetric RL

Supporting code for the [SOAR investigation](../../future-experiments/SOAR-INVESTIGATION.md).

## Overview

This directory contains prototype tooling for evaluating SOAR-style bilevel
meta-RL curriculum generation applied to security verification training.

## Structure

```
soar/
├── README.md                          # This file
├── cold_start_analysis.py             # Phase 1: Quantify the cold-start problem
├── generate_stepping_stones.py        # Phase 2: Teacher stepping-stone generation
├── configs/
│   ├── e1_soar_prototype.yaml         # E1 experiment configuration
│   └── e2_soar_prototype.yaml         # E2 experiment configuration
├── teacher_prompts/
│   ├── e1_network_log_teacher.txt     # Teacher prompt for E1 log generation
│   └── e2_config_audit_teacher.txt    # Teacher prompt for E2 config generation
└── results/                           # Generated artifacts (gitignored)
```

## Phases

| Phase | Script | Status | Dependency |
|-------|--------|--------|------------|
| 1. Cold-start analysis | `cold_start_analysis.py` | Ready | Existing eval runs |
| 2. Teacher prototype | `generate_stepping_stones.py` | Ready | API key |
| 3. Full bilevel loop | TBD | Blocked | WP3 training infra |
| 4. SOAR + MaxRL | TBD | Blocked | Phase 3 + MaxRL |

## Quick Start

```bash
# Phase 1: Analyze cold-start severity from existing eval runs
python research/experiments/soar/cold_start_analysis.py --env e1
python research/experiments/soar/cold_start_analysis.py --env e2

# Phase 2: Generate stepping stones (requires API key)
source .env
python research/experiments/soar/generate_stepping_stones.py \
    --env e1 --model gpt-5-mini --num-problems 20 --difficulty medium

# Validate generated stepping stones
python research/experiments/soar/generate_stepping_stones.py \
    --env e1 --validate-only --input results/stepping_stones_e1_*.jsonl
```

## References

- [SOAR Investigation](../../future-experiments/SOAR-INVESTIGATION.md)
- [MaxRL Investigation](../../future-experiments/MAXRL-INVESTIGATION.md)
- [Roadmap WP3/WP4](../../../plans/ROADMAP-Q1-2026.md)
