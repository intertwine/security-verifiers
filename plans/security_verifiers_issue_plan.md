# Security Verifiers → SV-Bench v0.1 and Suite Completion: Issue Plan

Prepared for `intertwine/security-verifiers`. Titles are intentionally prefixed with an ordered milestone number so Codex or another implementation agent can work through them independently and sequentially.

General Codex contract for every issue:

- Work only on the current issue scope unless a failing test reveals a direct prerequisite bug.
- Preserve public mini-set reproducibility.
- Add or update tests for every new code path.
- Run at minimum: `uv run ruff check .`, `uv run pytest -q`, and the issue-specific command listed under acceptance criteria.
- Update docs and Makefile targets when new user-facing commands are added.
- Do not commit secrets, external API keys, raw harmful prompt corpora, or private heldout data.

---

## Issue 01 — [SV-Bench v0.1 01/17] Add canonical project status and milestone docs

Suggested labels: `type:docs`, `area:roadmap`, `milestone:svbench-v0.1`

### Goal
Create a single source of truth that separates the near-term **SV-Bench v0.1** release from the broader **Security Verifiers Suite** roadmap. SV-Bench v0.1 should be scoped to E1 and E2 only. E3-E6 should remain alpha/beta roadmap items until the v0.1 empirical proof is complete.

### Context
The repo currently contains six environments, with E1 `sv-env-network-logs` and E2 `sv-env-config-verification` production-ready, while E3-E6 are alpha/preview. The Q1 roadmap defines SV-Bench v0.1 as the first benchmark release focused on E1/E2, with hosted RL proof, reward-source comparison, and a technical report. Codex should make this status obvious to new contributors.

### Implementation notes
Add or update:

- `SVBENCH_STATUS.md`
- `SVBENCH.md` skeleton if it does not already exist
- `plans/ROADMAP-2026-SUITE.md` or an updated roadmap section that distinguishes:
  - SV-Bench v0.1: E1/E2 benchmark and training harness
  - Security Verifiers Suite v1.0: all six environments
- README status section that links to the above docs

`SVBENCH_STATUS.md` should include:

- Environment status table: E1/E2 production, E3-E6 alpha/preview
- Completed work packages: WP0/WP1/WP2/WP2.5/WP2.5a
- Open work packages: WP3a/WP3b/WP3c/WP4/WP5
- Definition of Done for v0.1
- Current known blockers or unknowns
- “Do not expand E3-E6 before v0.1” guardrail

### Acceptance criteria
- `SVBENCH_STATUS.md` exists and gives a contributor a truthful current-state map in under 5 minutes.
- README links to `SVBENCH_STATUS.md`, `SVBENCH.md`, and the roadmap.
- The docs explicitly state that v0.1 includes only E1/E2.
- The docs explicitly state that E5/E6 offensive/red-team corpora must not be expanded or publicly released for v0.1.
- `uv run ruff check .` and `uv run pytest -q` pass.

---

## Issue 02 — [SV-Bench v0.1 02/17] Modernize Prime Lab GA workflow docs, configs, and Make targets

Suggested labels: `type:infra`, `area:prime-lab`, `milestone:svbench-v0.1`

### Goal
Update Prime Lab integration so the repository reflects Lab’s generally available hosted-training / hosted-evaluation workflow, while preserving fallback parity through `prime env eval` / `vf-eval` when hosted training is unavailable.

### Context
The project already has Prime Lab integration from v0.3.0, but the platform has moved to GA. Codex should ensure the repo docs and commands are aligned with the current operating mode: baseline eval → hosted training → inspect logs/metrics/rollouts → hosted eval → adapter/report artifacts.

### Implementation notes
Review and update:

- `docs/PRIME-LAB-INTEGRATION.md`
- `scripts/prime_lab_check.py`
- `scripts/normalize_hosted_eval.py`
- `configs/rl/e1.toml`
- `configs/rl/e2.toml`
- `configs/eval/e1.toml`
- `configs/eval/e2.toml`
- `configs/endpoints.toml`
- `Makefile`

Add config aliases or new files if helpful:

```text
configs/rl/e1_executable_reward.toml
configs/rl/e1_llm_judge_reward.toml
configs/rl/e1_hybrid_reward.toml
configs/rl/e2_executable_reward.toml
configs/rl/e2_llm_judge_reward.toml
configs/rl/e2_hybrid_reward.toml
```

Make targets should remain friendly wrappers. Expected target shape:

```bash
make lab-check
make lab-run-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team
make lab-run-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team
make lab-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team
make lab-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team
make env-eval-e1 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team N=100
make env-eval-e2 MODEL=Qwen/Qwen3-4B-Instruct-2507 TEAM=your-team N=50
```

### Acceptance criteria
- `make lab-check` provides a clear pass/fail/fallback result and prints next steps.
- Docs distinguish hosted training, hosted eval, fallback hosted-style eval, and local eval.
- Hosted and fallback outputs still normalize into the repo’s `outputs/evals/...` and/or `results/runs/...` layout.
- Existing E1/E2 eval commands still work.
- `uv run pytest -q tests scripts` passes, or all relevant tests pass if there is no `tests scripts` subset.

---

## Issue 03 — [SV-Bench v0.1 03/17] Add canonical run-card manifest and artifact validator

Suggested labels: `type:infra`, `area:reporting`, `milestone:svbench-v0.1`

### Goal
Every training, eval, comparator, and ablation run should produce a machine-readable run card and pass a validation command before it is used in reports.

### Context
SV-Bench needs reproducibility more than vibes. Results should be traceable by git SHA, environment version, dataset revision, model ID, reward configuration, seed, budget, hosted/local mode, and run artifacts.

### Implementation notes
Add:

- `sv_shared/run_manifest.py` or `bench/run_manifest.py`
- JSON schema: `bench/schemas/run_manifest.schema.json`
- CLI entrypoint, for example: `uv run svbench_manifest validate <path>`
- helper to write manifests from eval/training scripts
- tests for valid/invalid manifests

Required fields:

```text
run_id
git_sha
timestamp_utc
environment_id
environment_version
dataset_id
dataset_revision
split
model_id
model_revision_or_digest
sampling_params
reward_config_id
reward_config_hash
seed
platform_mode: local|hosted|fallback-hosted
trainer: none|grpo|gdpo|distillation|other
max_steps
rollouts_per_example
max_tokens
max_turns
tool_budget
input_artifacts
output_artifacts
metrics_summary_path
results_jsonl_path
metadata_json_path
notes
```

Hosted-only fields should be optional but validated when `platform_mode=hosted`:

```text
prime_run_id
team
compute_profile
platform_image
adapter_id
```

### Acceptance criteria
- `svbench_manifest validate` succeeds on at least one checked-in fixture for E1 and E2.
- Invalid or missing required fields produce useful error messages.
- E1/E2 report generation can optionally consume a run manifest.
- `make eval-e1 ...` and `make eval-e2 ...` either generate manifests or document why a follow-up issue is required.
- Tests cover schema validation and hosted/local field differences.

---

## Issue 04 — [SV-Bench v0.1 04/17] Add renderer-backed transcript stability tests for tool and multi-turn rollouts

Suggested labels: `type:infra`, `area:renderers`, `area:multi-turn`, `milestone:svbench-v0.1`

### Goal
Prevent token/template drift in tool-using and multi-turn environments before scaling E2/E3/E5/E6 training. Add renderer-backed tests that verify transcript replay, tool-call parsing, and prefix continuity.

### Context
Tool and multi-turn RL can silently fail when a sampled assistant message is parsed, normalized, then re-rendered differently in the next turn. This is especially risky for Qwen-family hosted training and for tool calls that contain JSON, booleans, whitespace, or special tokens.

### Implementation notes
Add `renderers` as an optional/dev dependency if it is not already present.

Suggested files:

```text
sv_shared/rendering.py
tests/test_renderers_prefix_continuity.py
tests/test_tool_call_roundtrip.py
tests/test_multiturn_rollout_replay.py
tests/test_hosted_local_transcript_equivalence.py
```

Test fixtures should include safe examples only:

- JSON tool call with boolean/string parameters
- assistant text before JSON
- Qwen-style text-before-JSON output
- truncated completion fallback
- tool result appended as next environment message

Do not require live hosted inference. These should be deterministic unit tests using a local tokenizer fixture or mocked renderer where needed.

### Acceptance criteria
- Tests fail if a prior sampled assistant turn is reconstructed from normalized parsed content instead of preserved bytes/tokens.
- Tests cover at least one Qwen-family renderer or a mocked equivalent with Qwen-like edge cases.
- E2 can use the new helper in dry-run or test mode without changing reward semantics.
- No production path is forced to depend on `renderers` unless the dependency is available; fallback is documented.

---

## Issue 05 — [SV-Bench v0.1 05/17] Add sandbox-backed tool runner abstraction for E2 and E3

Suggested labels: `type:infra`, `area:sandboxes`, `area:tools`, `milestone:svbench-v0.1`

### Goal
Move tool execution toward reproducible sandbox images so E2 config verification and E3 code repair do not depend on whatever happens to be installed on a developer laptop or hosted runner.

### Context
E2 relies on OPA/Rego, KubeLinter, Semgrep, and patch checks. E3 will rely on static analysis and tests. These are exactly the kinds of tool runs that should be isolated, reproducible, and safe.

### Implementation notes
Add:

```text
sandboxes/e2-policy/Dockerfile
sandboxes/e2-policy/README.md
sandboxes/e3-code/Dockerfile
sandboxes/e3-code/README.md
sv_shared/tool_runner.py
sv_shared/sandbox_runner.py
```

The runner should support three modes:

1. local direct execution for development;
2. local container execution if Docker is available;
3. Prime Sandbox execution, feature-gated by environment/config.

E2 image should include or document installation of:

```text
opa
conftest
kube-linter
semgrep
yq
jq
python validation utilities
```

E3 image should include or document installation of:

```text
python
pytest
bandit
semgrep
ruff
```

### Acceptance criteria
- E2 tool-only baseline can run through the new runner in local mode.
- Sandbox mode can be dry-run tested without requiring Prime credentials.
- Tool results include timing, exit code, stdout/stderr snippets, tool version, and normalized findings.
- Runner never logs secrets.
- Docs explain how to build and run each sandbox image.
- Tests include mocked command execution and at least one real lightweight local command if available.

---

## Issue 06 — [SV-Bench v0.1 06/17] Clean E1 baseline rerun and add reward/metric ablation configs

Suggested labels: `type:benchmark`, `area:e1-network-logs`, `milestone:svbench-v0.1`

### Goal
Create a clean E1 baseline and ablation foundation before running hosted RL comparisons.

### Context
E1 is the lowest-complexity signal path for SV-Bench v0.1. It should report operational SOC-style metrics, not just raw accuracy: TPR, FPR, FNR, expected cost, calibration, Brier score, abstention rate, and risk/coverage behavior.

### Implementation notes
Add or update:

```text
configs/eval/e1_baseline.toml
configs/eval/e1_ood.toml
configs/ablations/e1_no_abstention.toml
configs/ablations/e1_no_calibration.toml
configs/ablations/e1_cost_sensitivity_sweep.toml
bench/metrics/METRICS_E1.md
bench/scoreboards/e1_scoreboard.md
```

Make sure E1 output schema supports:

```json
{
  "label": "benign|malicious|abstain",
  "confidence": 0.0,
  "evidence": ["short signal summary"]
}
```

If the current parser supports a different schema, document the compatibility layer instead of breaking existing tests.

### Acceptance criteria
- `make baseline-e1 MODEL=<model>` runs on the public mini set and updates/produces an artifact-backed scoreboard.
- Report output includes all E1 v0.1 metrics.
- Ablation configs are checked in and documented.
- Invalid or non-JSON E1 completions receive zero or documented degraded reward.
- Tests cover abstention, calibration scoring, and asymmetric cost behavior.

---

## Issue 07 — [SV-Bench v0.1 07/17] Implement E1 hosted RL run recipes and reward-source comparator configs

Suggested labels: `type:experiment`, `area:e1-network-logs`, `area:prime-lab`, `milestone:svbench-v0.1`

Depends on: Issues 02, 03, 06

### Goal
Create the runnable E1 experiment matrix needed to compare executable verifier rewards against LLM-judge and hybrid rewards at matched budget.

### Context
The v0.1 research wedge is not just that E1 can be evaluated. It is whether executable rewards produce more reliable behavior than judge-only rewards. E1 should be the required comparator because it is simple enough to run cheaply and analyze cleanly.

### Implementation notes
Add:

```text
configs/rl/e1_executable_reward.toml
configs/rl/e1_llm_judge_reward.toml
configs/rl/e1_hybrid_reward.toml
configs/rl/e1_matched_budget_base.toml
research/e1_reward_source_plan.md
```

Each config should hold constant:

```text
base model
LoRA settings
max_steps
batch size
rollouts per example
max tokens
sampling params
dataset split
seed or seed plan
eval harness
```

Reward variants:

- executable: existing deterministic label/calibration/cost/abstention reward;
- LLM judge: judge score only, with strict output validation;
- hybrid: executable reward primary, LLM judge low-weight tie-breaker or explanation quality scorer.

### Acceptance criteria
- `make lab-run-e1 REWARD_SOURCE=executable` resolves to the executable config or documents exact CLI command.
- Equivalent commands/configs exist for `llm_judge` and `hybrid`.
- All three configs validate through `make lab-check` or a config validation command.
- Run-card metadata clearly records reward source and budget fields.
- The issue does not require actually spending hosted-training budget, but must make the run launchable and reproducible.

---

## Issue 08 — [SV-Bench v0.1 08/17] Harden E2 sandboxed config auditing metrics and patch verifier

Suggested labels: `type:benchmark`, `area:e2-config-verification`, `area:sandboxes`, `milestone:svbench-v0.1`

Depends on: Issues 03, 05

### Goal
Make E2 benchmark-grade for hosted RL by ensuring tool-grounded config findings and patches are scored consistently, with sandbox-compatible tool execution and patch-aware metrics.

### Context
E2 is the higher-signal v0.1 task because it involves tool use and patch validation. Its reward should be machine-checked: policy violations found, severity weighted, patches validated, hallucinated findings penalized, unnecessary changes tracked.

### Implementation notes
Review and update:

```text
environments/sv-env-config-verification/
sv_shared/tool_runner.py
bench/metrics/METRICS_E2.md
configs/eval/e2_baseline.toml
configs/eval/e2_tool_only.toml
bench/scoreboards/e2_scoreboard.md
```

E2 metrics should include:

```text
violation precision/recall/F1
severity-weighted score
patch success rate
clean-pass rate
false-positive rate on clean configs
hallucinated finding count
unnecessary-change rate
patch delta size
tool calls per episode
tool runtime per episode
```

Patch verification should reject:

- deletion-only fixes that remove required functionality;
- patches that introduce new high-severity findings;
- claims unsupported by tool output or ground truth;
- malformed output schemas.

### Acceptance criteria
- `make baseline-e2 MODEL=<model> INCLUDE_TOOLS=true` runs on the public mini set.
- E2 report includes all required metrics above.
- Tool-only baseline and model-with-tools baseline are distinguishable in metadata.
- Tests cover clean configs, known-violation configs, hallucinated findings, and patch over-fix risk.
- Sandbox runner can be selected without changing reward semantics.

---

## Issue 09 — [SV-Bench v0.1 09/17] Implement E2 hosted RL run recipes and reward-source comparator configs

Suggested labels: `type:experiment`, `area:e2-config-verification`, `area:prime-lab`, `milestone:svbench-v0.1`

Depends on: Issues 02, 03, 05, 08

### Goal
Create the E2 hosted RL and reward-source comparison configs needed for v0.1, with executable reward, LLM-judge reward, and hybrid reward variants.

### Context
E2 is preferred for the full comparator because it tests tool-using behavior, patch verification, and hallucination risk. Even if E2 comparator results are deferred from the strict v0.1 release, the configs should be ready and documented.

### Implementation notes
Add:

```text
configs/rl/e2_executable_reward.toml
configs/rl/e2_llm_judge_reward.toml
configs/rl/e2_hybrid_reward.toml
configs/rl/e2_matched_budget_base.toml
research/e2_reward_source_plan.md
```

Reward variants:

- executable: OPA/KubeLinter/Semgrep/patch verifier primary;
- LLM judge: judge-only final answer scoring, still requiring output schema validation;
- hybrid: executable reward primary, judge used only for explanation quality/severity tie-breaks.

Multi-turn/tool settings must be explicit:

```text
max_turns
tool budget
timeout per tool
timeout per episode
allowed tools
sandbox mode
failure handling
```

### Acceptance criteria
- Configs are validated by the same config validation command used in Issue 07.
- Run-card metadata records tool budget, sandbox mode, reward source, and patch verifier version.
- `make lab-run-e2 REWARD_SOURCE=executable` and equivalents for judge/hybrid resolve to documented commands.
- No raw secrets or local-only paths are required.
- Tests or dry-run checks prove config parsing works.

---

## Issue 10 — [SV-Bench v0.1 10/17] Add unified reward-source comparator report generator

Suggested labels: `type:reporting`, `area:research`, `milestone:svbench-v0.1`

Depends on: Issues 03, 07, 09

### Goal
Create a report generator that compares executable, LLM-judge, and hybrid reward-source runs across E1 and E2 using matched-budget run manifests.

### Context
The research claim should be falsifiable: executable verifiers should be compared to judge-only rewards under matched training/eval budgets and reported across operational metrics, not only scalar reward.

### Implementation notes
Add:

```text
bench/compare_rewards.py
bench/schemas/reward_comparison.schema.json
research/reward_source_comparison.md
results/ablations/reward_source/.gitkeep
```

Suggested CLI:

```bash
uv run svbench_compare_rewards \
  --env e1 \
  --executable results/runs/<id>/run_manifest.json \
  --judge results/runs/<id>/run_manifest.json \
  --hybrid results/runs/<id>/run_manifest.json \
  --out results/ablations/reward_source/e1_comparison.md
```

Report fields:

```text
matched-budget validation table
metric delta table
confidence intervals where possible
reward distribution summary
calibration/risk-coverage deltas for E1
patch/tool-economy deltas for E2
representative trace links
failure-mode notes
```

### Acceptance criteria
- Comparator refuses to run if budget parity fields do not match, unless `--allow-unmatched` is explicitly provided and documented.
- Comparator produces both Markdown and JSON summary outputs.
- Fixture tests cover matched, unmatched, missing-field, and multi-seed cases.
- `research/reward_source_comparison.md` includes a template ready for real run artifacts.

---

## Issue 11 — [SV-Bench v0.1 11/17] Add multi-reward RL stability ablation matrix

Suggested labels: `type:experiment`, `area:research`, `milestone:svbench-v0.1`

Depends on: Issues 03, 06, 08, 10

### Goal
Prepare the ablation matrix for multi-objective security rewards: scalar summed reward, per-component normalization, GDPO-style decoupled normalization, and teacher/distillation baseline.

### Context
Security rewards are inherently multi-objective: correctness, calibration, abstention, false-negative cost, tool economy, patch success, hallucination penalties, and over-fix risk. This issue makes the ablation setup concrete even if full execution lands after the initial v0.1 release package.

### Implementation notes
Add:

```text
configs/ablations/e1_grpo_scalar.toml
configs/ablations/e1_component_normalized.toml
configs/ablations/e1_gdpo_style.toml
configs/ablations/e1_distillation.toml
configs/ablations/e2_grpo_scalar.toml
configs/ablations/e2_component_normalized.toml
configs/ablations/e2_gdpo_style.toml
configs/ablations/e2_distillation.toml
research/ablation_grpo_vs_gdpo.md
```

If exact GDPO support does not exist, implement a clearly named “GDPO-style / decoupled-normalization placeholder” config and document the missing runtime feature instead of pretending it is done.

### Acceptance criteria
- Ablation configs validate or clearly fail with a documented unsupported-feature message.
- `research/ablation_grpo_vs_gdpo.md` explains hypothesis, metrics, expected artifacts, and run commands.
- Component reward weights are explicit and traceable.
- The issue does not block v0.1 if hosted RL/comparator work is not yet complete.

---

## Issue 12 — [SV-Bench v0.1 12/17] Build SV-Bench v0.1 release package and technical report

Suggested labels: `type:release`, `area:docs`, `milestone:svbench-v0.1`

Depends on: Issues 01, 03, 06, 08, 10

### Goal
Create the release package structure for `sv-bench-v0.1`, including docs, result summaries, changelog, benchmark manifest, leaderboard files, and a short technical report.

### Context
The release should be credible even if the first results are modest. It should make the benchmark easy to run, make claims narrow, expose limitations, and distinguish public mini sets from heldout/gated data.

### Implementation notes
Add or update:

```text
SVBENCH.md
bench/changelog.md
results/v0.1_baselines.md
results/v0.1_training.md
reports/SVBENCH_v0.1_technical_report.md
bench/leaderboard/v0.1.json
bench/leaderboard/v0.1.schema.json
datasets/HELDOUT_POLICY.md
```

Report outline:

```text
1. What SV-Bench measures
2. Why executable rewards for security
3. Environments included in v0.1: E1 and E2
4. Datasets and public/gated split
5. Metrics
6. Baselines
7. Hosted RL runs
8. Reward-source comparator
9. Failure modes and limitations
10. Reproduction commands
```

Add a release checklist:

```bash
make svbench-v0.1-check
```

The check should validate docs, public mini datasets, configs, scoreboards, run manifests, report files, and absence of secrets.

### Acceptance criteria
- `make svbench-v0.1-check` exists and passes in a clean checkout.
- The report can be generated or updated from stored artifacts.
- `bench/leaderboard/v0.1.json` validates against its schema.
- Docs clearly state what is public, what is gated, and what is not yet included.
- Release docs do not overclaim E3-E6 readiness.

---

## Issue 13 — [Suite Beta 13/17] Graduate E3 code vulnerability repair to a sandboxed beta slice

Suggested labels: `type:environment`, `area:e3-code-vulnerability`, `area:sandboxes`, `milestone:suite-beta`

Depends on: Issues 04, 05, 12

### Goal
Move E3 from alpha/preview to a narrow beta slice with deterministic, defensive verification: vulnerable snippet → tool-assisted analysis → patch → tests/static checks pass.

### Context
E3 should not try to solve arbitrary repo-scale vulnerability repair yet. The beta slice should focus on small, safe, self-contained snippets with unit tests and static-analysis checks.

### Implementation notes
Add or update:

```text
environments/sv-env-code-vulnerability/
datasets/public_mini/e3.jsonl
configs/eval/e3_beta.toml
configs/rl/e3_beta.toml
bench/metrics/METRICS_E3.md
docs/sv-env-code-vulnerability.md
```

Verification components:

```text
pytest/unit tests pass
Bandit/Semgrep finding removed or reduced
no new high-severity findings
required function signature preserved
minimal diff / patch delta measured
no deletion-only “fixes”
```

Data safety requirements:

- Use defensive toy examples or sanitized known-vulnerability examples.
- Do not include exploit instructions or weaponized payloads.
- Avoid network access during tests.

### Acceptance criteria
- `make eval-e3 N=10` or documented equivalent runs on public mini set.
- E3 beta report includes patch success, static finding delta, test pass rate, and patch delta.
- Sandbox runner is used or supported by config.
- Tests cover valid patch, no-op patch, deletion-only patch, and patch introducing a new finding.

---

## Issue 14 — [Suite Beta 14/17] Graduate E4 phishing detection to beta with abstention and evidence

Suggested labels: `type:environment`, `area:e4-phishing`, `milestone:suite-beta`

Depends on: Issues 03, 12

### Goal
Move E4 from alpha/preview to a beta single-turn classification environment: `phishing | legitimate | abstain`, with confidence and evidence extraction.

### Context
E4 should mirror E1’s calibrated classification pattern but use email-specific signals: sender mismatch, suspicious URL, credential request, urgency, attachment cue, and social-engineering language. Live URL browsing should not be required for beta.

### Implementation notes
Add or update:

```text
environments/sv-env-phishing-detection/
datasets/public_mini/e4.jsonl
configs/eval/e4_beta.toml
configs/rl/e4_beta.toml
bench/metrics/METRICS_E4.md
docs/sv-env-phishing-detection.md
```

Suggested output schema:

```json
{
  "label": "phishing|legitimate|abstain",
  "confidence": 0.0,
  "evidence": [
    {"type": "sender|url|urgency|credential_request|attachment|other", "text": "short evidence"}
  ]
}
```

Metrics:

```text
precision/recall/F1
false-negative rate
false-positive rate
calibration / Brier score
abstention rate
risk-coverage
evidence precision on annotated evidence where available
```

### Acceptance criteria
- `make eval-e4 N=10` or documented equivalent runs on public mini set.
- Invalid format receives zero or documented degraded reward.
- Evidence is scored only against safe text snippets; no live malicious URL access is required.
- Tests cover phishing, legitimate, abstain, invalid schema, and evidence normalization.

---

## Issue 15 — [Suite Beta 15/17] Build safe beta slice for E5 red-team attack simulator

Suggested labels: `type:environment`, `area:e5-redteam-attack`, `area:safety`, `milestone:suite-beta`

Depends on: Issues 04, 12

### Goal
Create a safe, publishable beta slice for E5 where an attacker agent probes a simulated target for policy weaknesses, while the repo avoids publishing raw harmful corpora or operational misuse content.

### Context
E5’s purpose is defensive evaluation and adversarial training support, not public release of dangerous jailbreak material. The beta slice should use sanitized categories, harmless placeholders, and aggregate metrics.

### Implementation notes
Add or update:

```text
environments/sv-env-redteam-attack/
datasets/public_mini/e5_sanitized.jsonl
configs/eval/e5_beta.toml
bench/metrics/METRICS_E5.md
docs/sv-env-redteam-attack.md
docs/redteam-data-publication-policy.md
```

Environment behavior:

- Multi-turn attacker attempts to elicit a simulated unsafe target response.
- Attacker is penalized for producing disallowed content directly.
- Success is judged by safety classifier/rules against the target response.
- Public examples must be sanitized and non-operational.

Metrics:

```text
attack success rate on sanitized simulator
steps to success
unsafe attacker-output rate
category coverage
target refusal robustness
representative sanitized traces
```

### Acceptance criteria
- Public mini set contains only sanitized, non-operational examples.
- Tests prove unsafe attacker output is penalized.
- Renderer-backed replay test covers at least one E5 transcript.
- Docs include publication filter rules and heldout-data handling.
- No raw harmful prompt corpus is committed.

---

## Issue 16 — [Suite Beta 16/17] Build E6 adversarial alignment defender beta with helpfulness/harmlessness balance

Suggested labels: `type:environment`, `area:e6-redteam-defense`, `area:safety`, `milestone:suite-beta`

Depends on: Issues 04, 12, 15

### Goal
Create a beta E6 defender environment where the assistant faces a mix of benign and adversarial turns and is rewarded for safe refusal, safe helpfulness, and avoiding over-refusal.

### Context
E6 should complement E5. The defender should not simply refuse everything. It must preserve helpfulness on benign requests while refusing unsafe requests under adversarial pressure.

### Implementation notes
Add or update:

```text
environments/sv-env-redteam-defense/
datasets/public_mini/e6_sanitized.jsonl
configs/eval/e6_beta.toml
configs/rl/e6_beta.toml
bench/metrics/METRICS_E6.md
docs/sv-env-redteam-defense.md
```

Reward components:

```text
unsafe compliance penalty
safe refusal reward
benign helpfulness reward
over-refusal penalty
multi-turn consistency
refusal quality/style low-weight tie-breaker
```

Safety gates:

- Use classifier/rule checks before any judge score.
- Keep LLM judges as tie-breakers or explanatory labels, not sole safety source.
- Public traces must be sanitized.

### Acceptance criteria
- `make eval-e6 N=10` or documented equivalent runs on public mini set.
- Metrics include unsafe compliance rate, benign helpfulness, over-refusal, and adversarial robustness.
- Tests cover benign request, unsafe request, adversarial follow-up, over-refusal, and unsafe compliance.
- Renderer-backed replay test covers at least one E6 transcript.

---

## Issue 17 — [Suite v1.0 17/17] Add suite-wide Hub publication and v1.0 completion checklist

Suggested labels: `type:release`, `area:hub`, `milestone:suite-v1.0`

Depends on: Issues 12-16

### Goal
Define and automate the completion gate for Security Verifiers Suite v1.0: all six environments installable, runnable, documented, safely publishable, and ready for Environments Hub publication.

### Context
SV-Bench v0.1 is the benchmark nucleus. Suite v1.0 is the broader program: six installable security/alignment environments sharing schemas, tools, evaluation methods, reproducible baselines, and responsible publication practices.

### Implementation notes
Add:

```text
SUITE_V1_CHECKLIST.md
scripts/check_suite_v1.py
docs/environments-hub-publication.md
bench/leaderboard/suite_v1.schema.json
```

Completion checks:

```text
all six environments import successfully
all six public mini sets exist
all six eval configs exist
E1/E2 hosted training configs exist
E3-E6 beta configs exist
metrics docs exist for E1-E6
README/docs link every environment
Hub IDs documented
public/gated/restricted data policy documented
no secrets or unsafe corpora committed
CI smoke test covers every environment
```

Suggested Make target:

```bash
make suite-v1-check
```

### Acceptance criteria
- `make suite-v1-check` exists and validates all completion criteria above.
- `SUITE_V1_CHECKLIST.md` has a human-readable status table.
- Docs explain how to publish or update each environment on the Environments Hub.
- The checklist explicitly distinguishes production, beta, alpha, and gated/restricted components.
- CI includes at least smoke tests for each environment package.
