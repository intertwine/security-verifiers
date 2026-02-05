# ROADMAP Q1 2026 — Security Verifiers → SV‑Bench v0.1

**Last updated:** 2026-02-04
**Primary objective (Q1):** Ship **SV‑Bench v0.1**: a benchmark + training harness demonstrating that **executable security verifiers** can train models (not just evaluate them) with measurable gains in **operationally-relevant security metrics**.

---

## Executive Intent

### Project Pitch
Can Machines Check Their Own Security Work? Verifiable Rewards for Defensive AI Agents. Build an open benchmark + training harness where agent success is mechanically checked: (1) configuration auditing and remediation where reward = OPA/Rego compliance + KubeLinter/Semgrep results + minimal-risk diffs; (2) vulnerability repair where reward = patch passes tests + vulnerability signal eliminated + minimal patch delta; (3) detection tasks where reward = calibrated probability + correct abstention under uncertainty + evidence-grounded outputs.

The research question: Do tool-grounded verification signals produce meaningfully different (and more reliable) agent behavior than LLM-as-a-judge rewards? Under what conditions do verifiable rewards still fail or get "hacked," and what partial-progress signals help without opening new exploit paths?

### SV‑Bench v0.1 Scope
**v0.1 includes only the two production environments**:

- **E1: `sv-env-network-logs`** — calibrated anomaly detection with abstention and asymmetric costs.
- **E2: `sv-env-config-verification`** — tool-grounded auditing with executable checks and patch-aware scoring.

(E3-E6 remain **alpha** in Q1; only touch if needed for shared tooling or stretch goals.)

### Definition of Done for SV‑Bench v0.1
By the end of Q1, SV‑Bench v0.1 is "real" if:

1. **Reproducible evaluation** — Anyone can run `make eval-e1` / `make eval-e2` on a public mini set and reproduce headline baseline metrics.
2. **Reproducible training proof** — At least one end-to-end RL training run per environment (E1 and E2), on an open-weight model, with learning curves and eval deltas.
3. **Benchmark-grade reporting** — A versioned metrics spec and a single command to generate a report from stored rollouts.
4. **Industry-useful metrics** — Report more than accuracy: calibration, abstention/risk‑coverage, cost-weighted loss (E1), and patch/tool-economy metrics (E2).
5. **Clear research wedge** — State and defend a research claim: e.g., multi-reward RL stability and tradeoffs (GRPO vs GDPO-style normalization) or executable verifiers vs LLM-judge rewards.

---

## Ground Rules

### Public vs Gated Benchmark Posture
Goal: maximize adoption **without** destroying benchmark integrity.

- **Public:** environment code, schemas, scoring logic, metrics, baseline scripts, and public mini/dev sets.
- **Gated:** official held-out eval sets accessible via controlled evaluation infrastructure.

### Safety + Responsible Disclosure
- Keep offensive/red-team work **out of v0.1**; don't publish harmful prompt corpora.
- When working on E5/E6 later, keep it defensive-eval oriented and apply a strict publication filter.

---

## Work Packages

### WP-1 — Verifiers v0.1.9 API Compatibility ✓
**Status:** Complete

Updated all environments for verifiers v0.1.9 API compatibility:
- Added `max_turns` parameter to `load_environment()` signatures
- Fixed `is_completed()` signature (state-only, no messages)
- Fixed `env_response()` return type (messages only, state modified in place)

### WP0 — Benchmark Integrity Hardening ✓
**Status:** Complete

Implemented comprehensive metadata tracking and CI for reproducible evaluations:
- `VERSIONING.md` documenting pinned versions for Python, verifiers, tools
- Enhanced `metadata.json` with env_version, python_version, verifiers_version, dataset_revision, seed
- CI workflow (`eval-ci.yml`) for minimal E1/E2 eval integrity checks

### WP1 — Metrics Contracts + Report Generator ✓
**Status:** Complete (2026-02-02; refinements 2026-02-04)
**Why:** SV‑Bench is only as credible as its metric definitions and its ability to generate a report from stored rollouts.

**Definition of Done:**
- Run `uv run svbench_report --env e1 --input outputs/evals/...` and get:
  - `summary.json` (machine-readable)
  - `report.md` (human-readable)

**Artifacts:**
- `bench/metrics/METRICS_E1.md`
- `bench/metrics/METRICS_E2.md`
- `bench/report.py` with a stable CLI
- `bench/schemas/summary.schema.json`

**Completion notes:**
- `svbench_report` CLI added (entrypoint to `bench.report:main`)
- Report generator parses raw `results.jsonl` + `metadata.json` and supports strict mode
- E2 tool economy includes tool call timings (duration_ms) and severity breakdowns
- Summary schema updated to include confusion matrix + severity breakdowns
- Tests cover E1/E2 metrics and report generation
- Added positive-only F1 plus clean-pass/false-positive rates for E2
- Normalizes unprefixed E2 rule IDs to the primary tool prefix (prevents dropping predictions)
- Batch report generator for recent runs (`scripts/generate_svbench_reports.py`) + sv-report skill

**Metric Minimums (v0.1):**

E1 (network logs):
- Detection: TPR, FPR, FNR
- Cost: expected cost with explicit asymmetry (FN ≫ FP)
- Calibration: ECE + Brier score on confidence
- Abstention: risk–coverage curve (or abstain rate + metrics conditional on non‑abstained)

E2 (config verification):
- Finding quality: precision/recall/F1 on violations
- Patch success: % patches that pass verifiers after patch
- Severity weighting: score weighted by severity of fixed findings
- Tool economy: tool calls + tool time per episode

### WP2 — Baselines + Public Mini Sets ✓
**Status:** Complete (2026-02-05)
**Why:** You need a floor, a strong prompt baseline, and a tool-only baseline to establish difficulty.

**Definition of Done:**
- `make baseline-e1` and `make baseline-e2` exist and populate a `scoreboard.md`.
- There is a **public mini set** for each env (50–200 items) that is always runnable.

**Artifacts:**
- `baselines/e1_prompt/` (system prompt + few-shot)
- `baselines/e1_heuristic/` (simple rules baseline)
- `baselines/e2_tool_only/` (OPA/KubeLinter/Semgrep pipeline outputs)
- `baselines/e2_prompt/` (tool-first prompt baseline)
- `bench/scoreboards/e1_scoreboard.md`, `e2_scoreboard.md`
- `datasets/public_mini/e1.jsonl`, `e2.jsonl`

**Completion notes:**
- Public mini sets committed under `datasets/public_mini/`
- `make baseline-e1` / `make baseline-e2` run heuristic/tool-only + prompt baselines
- Scoreboards updated from run artifacts

### WP3 — Canonical RL Training Runs (GRPO Baseline)
**Why:** This is the "prove it trains" milestone.

**Model recommendation:** Start with a ~4B instruct model and LoRA for cost efficiency.

**Definition of Done:**
- One RL training run per env (E1 and E2) showing:
  - A learning curve that isn't pure noise
  - Improvement on at least one operational metric (not just scalar reward)
- Full run artifacts: config, seeds, dataset revisions, commit hash, eval deltas.

**Artifacts:**
- `train/configs/e1_grpo_lora.yaml`
- `train/configs/e2_grpo_lora.yaml`
- `train/run_train.py` (or Makefile targets)
- `results/runs/<date>_e1_grpo_lora/` (curves + report)
- `results/runs/<date>_e2_grpo_lora/`

### WP4 — Research Ablation: Multi-Reward RL Stability
**Why:** Security tasks are inherently multi-objective. This is the strongest research wedge.

**Core question:** When rewards are a vector (correctness, calibration, abstention, cost, tool-economy), do common GRPO setups collapse signal or destabilize training? Does decoupled normalization (GDPO-style) improve stability?

**Definition of Done:**
- A small but convincing experiment matrix showing at least one of:
  - Improved stability
  - Better Pareto tradeoff across metrics
  - Reduced sensitivity to reward-weight tuning

**Minimal Experiment Matrix:**
- Variant A: GRPO with scalar summed reward
- Variant B: Per-component normalization + weighted sum
- Variant C: GDPO-style decoupled normalization

**Artifacts:**
- `research/ablation_grpo_vs_gdpo.md` (setup + results)
- `results/ablations/grpo_vs_gdpo/<date>/` (plots + tables + configs)

### WP5 — SV‑Bench v0.1 Release Package
**Why:** A clean, versioned release is the on-ramp for adoption and collaboration.

**Definition of Done:**
- A tagged release (`sv-bench-v0.1`) with:
  - Metrics contracts
  - Baselines
  - At least one RL run per env
  - A short paper-style report / preprint draft outline

**Artifacts:**
- `SVBENCH.md` (what it is, what it measures, how to run)
- `bench/changelog.md`
- `results/v0.1_baselines.md`
- `results/v0.1_training.md`

---

## Stretch Goals (only if v0.1 is on track)

### SG1 — Adversarial Robustness Variants
Add controlled perturbations that model realistic evasions while keeping evaluation deterministic:
- E1: log field obfuscation, benign-looking noise injection, distribution shifts
- E2: configs with tricky edge cases, partial tool-output noise

**Why:** Directly supports "when verifiable rewards still fail or get hacked."

### SG2 — Bring One Alpha Env to Beta
If pursued in Q1, do it as a focused "beta slice" with a small dataset and deterministic verifiers.

---

## Experiment Tracking Standards

### Run Naming and Directory Layout
- Every run gets a `run_id` (timestamp + short hash)
- All artifacts live under:
  - `results/runs/<run_id>/` (training)
  - `outputs/evals/.../<run_id>/` (raw eval)
  - `results/ablations/.../<run_id>/` (ablations)

### Metadata Required Fields
Every run must write:
- git SHA
- environment package versions
- dataset revision hashes
- model name + weights revision
- sampling params
- trainer config (GRPO/GDPO variant)
- seed(s)
- token counts
- tool call counts and tool runtime

### Budget Parity Rule
When comparing two approaches, match:
- number of rollouts per example
- max tokens
- max turns
- tool budget constraints

---

## Q1 Milestone Checklist

- [x] WP-1 complete (verifiers v0.1.9 API compatibility)
- [x] WP0 complete (benchmark integrity)
- [x] WP1 complete (metrics contracts + report generator)
- [ ] WP2 complete (baselines + public mini sets)
- [ ] WP3 complete (canonical RL runs on E1 and E2)
- [ ] WP4 complete (GRPO vs GDPO-style ablation)
- [ ] WP5 complete (SV‑Bench v0.1 release package)
