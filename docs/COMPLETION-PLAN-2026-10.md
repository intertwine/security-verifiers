# SV-Bench v0.1 completion plan — October 2026

## Goal and scope

Finish the original E1/E2 research proof and produce a reproducible release candidate. The goal is an evidence-backed answer to whether executable security rewards change useful defensive behavior, not a favorable result selected after seeing the data.

The source of this goal is [the Q1 research roadmap](../plans/ROADMAP-Q1-2026.md), together with [the current release boundary](../SVBENCH_STATUS.md) and [suite roadmap](../plans/ROADMAP-2026-SUITE.md). E1/E2 are the entire v0.1 scope. E3–E6 expansion, framework integrations, outreach targets, local trainer parity, and GRPO/GDPO/distillation ablations do not block this completion path.

## What counts as complete

| Deliverable | Acceptance criteria |
|---|---|
| Preservation | Original personal/team exports retained privately with checksums; hosted record counts reconciled; curated samples compared against source archives; adapters identified by run and digest. Missing data and export limitations remain explicit. |
| Reproduction | Public-mini baseline commands, report generation, real run-manifest validation and offline package checks pass from a clean checkout. Fixture manifests are never counted as experiment results. |
| E1 training proof | An open-weight base model and its trained adapter evaluated on the same independent, train-excluded cases using a common evaluator; learning curves and operational deltas reported with uncertainty. |
| E2 training proof | The same before/after contract, with finding/patch/tool metrics and backend provenance; semantic patch preservation checked. One completed training step is a compatibility pilot, not learning/convergence proof. |
| Reward-source answer | E1 executable and judge training share immutable model/environment/data identity and matched budgets. Compare their outputs using the same operational evaluator, not their different training reward scales. Hybrid and E2 comparison are useful extensions, not required extra arms. |
| Research report | Hypotheses, methods, counts, curves, operational deltas, uncertainty, concrete failure traces and limitations are backed by artifacts. A negative or inconclusive hypothesis result is an acceptable scientific conclusion; it does not become evidence of improvement. |
| Release candidate | Scope, status, scoreboard and technical report agree; no private exports or restricted corpora enter public artifacts; package and empirical evidence gates are reported separately. Tagging/publication is a later action. |

The roadmap's desired training improvement must remain marked unproven if no operational improvement is measured. Honest completion of analysis can establish that a hypothesis was unsupported; it cannot satisfy the original improvement claim by relabeling a pilot.

## Evidence available after preservation

The October preservation audit found 43 personal training records plus 2 evaluations, and 27 team training records plus 170 evaluations. The six curated May 15 run records have matching shared fields for all 123 samples previously committed; archived E1 sample coverage is larger than the collector's single latest-step page. Ten adapters were downloaded: the six curated runs and four older completed runs. These are private preservation facts, not additional benchmark results.

The older E1 run `kvyp3sz2afit54dv3apgoozp` is documented as completed at 200 steps in the Q1 roadmap and confirmed in the preserved account evidence. Its recorded debugging/version history must accompany any analysis; recovery of a final adapter alone does not establish a clean before/after experiment.

Every exported evaluation object and sample was inspected. The 170 team objects preserve E1/E2 dataset-like snapshots without model outputs, model identity, linked runs or evaluation configuration; split provenance is unknown. The two personal objects contain E5/E6 Claude evaluations outside v0.1. No usable held-out E1/E2 policy comparison was recovered from these objects. Private per-object inventories retain version joins, fingerprints and source candidates for recovering original data provenance.

Current May evidence has specific limits:

- E1 judge uses a different hosted environment/version from executable and hybrid. It remains exploratory unless a controlled comparison is recovered elsewhere.
- E2 has a matched one-step hosted pilot, but reward-source-specific `avg@1` values are not a common measure of security quality.
- Historical E2 scanner fallback provenance is incomplete. Do not infer actual binary execution from a successful tool observation.
- A downloaded adapter still needs architecture/base-revision/config compatibility checks before serving. A historical `prime-hosted` model revision is not an immutable digest.
- Historical baseline scoreboards are an index to evidence, not replacements for raw rollouts and exact dataset/model metadata.

### Offline recovered evidence, October 2026

Rebuild the descriptive analysis without model calls or tool execution:

```bash
python3 scripts/analyze_prime_legacy.py \
  --input outputs/prime_legacy --output outputs/prime_legacy_analysis
```

The private generated report, JSON and CSV cover the six curated and four older completed runs. They preserve logged per-step curves without interpolation and separate content-only parsing from reasoning-channel salvage diagnostics. Twelve focused tests cover invalid output handling, explicit denominators, abstention/cost behavior, channel separation, colliding sample IDs and rejection of valid nested predictions inside malformed outer JSON. This is not an alternative held-out report.

| Recovered block | Samples | Diagnostic distinct prompt/answer pairs | Interpretation |
|---|---:|---:|---|
| May E1 executable | 160 | 10 | Reasoning-fallback correct fraction on non-abstained retained samples rises from 26/32 at step 0 to 32/32 at step 40; cases differ across steps. |
| May E1 judge | 160 | 19 | Content-only prediction text is absent; reasoning-fallback accuracy is 16/31 then 15/31 on those endpoint subsets. Environment identity differs. |
| May E1 hybrid | 160 | 8 | Reasoning-fallback endpoint accuracy is 32/32 then 31/32; the initial subset contains only malicious labels. |
| May E2, each of three arms | 16 | 1 each | One retained training step and one diagnostic case identity per arm; cannot support general patch-quality or convergence conclusions. |
| Older E1 executable `kvyp3...` | 160 | 58 | Last retained step has 3/8 correct; learning curve and bug/version history must be interpreted together. |
| Older E1 executable `me9...` | 160 | 58 | Last retained eight predictions all abstain; zero accepted predictions is not perfect detection or zero-risk success. |
| Older E1 judge `pi7...` | 160 | 63 | Last retained eight predictions are false negatives; subsets are not matched across steps. |
| Older E2 `covn...` | 200 | 2 | Archived training/eval scalar reward stays zero; no patch verification is inferred from it. |

Diagnostic pair hashes count distinct serialized prompt/answer combinations, not independently sampled benchmark cases. Historical problem IDs collide (the older records frequently use `0`), and all sample rows are retained. The salvaged E1 predictions are useful for failure investigation, but the historical content-only harness cannot be silently replaced by reasoning extraction when making training claims. E1 operational metrics are conditional on valid non-abstained parsed outputs; abstained/unparseable counts are reported separately. The recovered evidence supports investigation and experiment prioritization, not a positive completion verdict.

## Parallel work and integration order

| Work lane | Concrete output | Boundary |
|---|---|---|
| Recovery | Run/step/sample inventory, normalized report inputs, adapter digest map, provenance/gap ledger | Keep raw archives private; never invent absent fields. |
| Analysis | Recomputed E1/E2 operational metrics, learning curves and supported comparison tables | Distinguish training samples, repeated examples and held-out evaluations. |
| Harness/gates | Focused ingestion/comparison fixes and an explicit empirical-completion gate | Offline package success remains distinct from empirical proof. |
| E2 integrity | Tests and review of no-op, semantic regression, over-fix and backend handling | Surgical source changes, no new public corpora. |
| Report/release | Updated artifact indices, status, narrow technical report and reproducible commands | Claims follow results; no publication during preparation. |

Integrate in this order: establish normalized evidence contracts; run offline reconstruction and focused tests; update report claims; evaluate preserved adapters if the quoted cost is accepted; add only experiments still needed. Agents should own separate files and share the manifest/report contract before changing it.

## Controlled experiment plan: evaluate first

No paid runs are authorized or launched by this plan. The table specifies a bounded candidate matrix for review after recovery has exhausted existing evidence. Exact compute/inference prices, available serving APIs and model compatibility must be checked before execution; no dollar estimate is asserted here.

### Stage A — offline recovery, zero new hosted experiment spend

1. Inspect all archived E1/E2 evaluations for exact source/model/adapter identity, train-excluded splits and usable raw observations.
2. Recompute operational metrics from compatible stored outputs. Record partial/unknown provenance rather than making it pass a completion gate.
3. Identify which preserved adapters can be loaded with an exact base revision and which learning curves have usable checkpoint/version attribution.
4. Freeze a train-excluded evaluation split, its hash, primary metrics and analysis before generating new outputs. Public-mini smoke sets remain labeled as such. Do not train on the frozen cases.

### Stage B — serve recovered adapters before retraining

Proposed minimum: E1 200 independent evaluation cases; E2 100. These are pilot sample budgets, not power guarantees. Verify actual dataset sizes, permissions and contamination status first. Use the same ordered cases for the base and trained policies; deterministic sampling where possible; record every invalid output, timeout and abstention.

| Evaluation block | Policies | Episodes | Generated-token planning bound |
|---|---:|---:|---:|
| E1 primary | Base + executable adapter + compatible judge adapter | 600 | 1,228,800 at 2,048 generated tokens/episode |
| E1 optional hybrid | One adapter | 200 | 409,600 |
| E2 primary | Base + executable adapter | 200 | 819,200 at 4,096 generated tokens/episode |
| E2 optional judge/hybrid | Two adapters | 200 | 819,200 |

The primary block totals 800 episodes and at most 2,048,000 generated tokens under these proposed caps. Optional arms bring it to 1,200 episodes and 3,276,800 generated tokens. These are output-token caps, not provider bill estimates: prompts, tool observations, repeated turns, retries and adapter serving compute also cost resources. For E2, enforce 4,096 as an aggregate episode cap or revise the bound if the platform applies it per turn. Proposed E2 caps: five turns, three tool calls, 30 seconds/tool and 120 seconds/episode, matching the existing template's envelope.

Pre-register E1 expected cost as the primary operational measure, with accuracy, ECE/Brier and risk–coverage as supporting metrics. Pre-register E2 verified patch success without semantic regression as primary, with finding F1, clean-case false positives, over-fix and tool economy supporting it. Use paired bootstrap intervals over independent cases; report effective sample counts and do not present multiple sampled completions of one case as independent cases. Single-seed policy comparisons remain pilot evidence about those trained policies, not robust training-seed conclusions.

A light defensive shift slice can test H3 after the primary block: freeze transformations and preserve case pairing, report degradation with uncertainty. Failure trace review can test H2 descriptively; a few examples do not establish a rate reduction. Do not add new E3–E6 data for either task.

### Stage C — only the missing training evidence

**Current platform constraint:** [Prime's hosted training model/pricing documentation](https://docs.primeintellect.ai/hosted-training/models-and-pricing) states new shared LoRA runs ended October 8, 2026, and dedicated training is in closed beta. Historical shared-run templates and rates cannot be treated as an available launch path. Verify dedicated access, compatible configs and a current dedicated compute quote before proposing any new hosted training. If unavailable, prepare an explicitly quoted local-trainer path rather than assuming old shared hosting can be relaunched. [Adapter deployment documentation](https://docs.primeintellect.ai/inference/adapter-deployments) says existing adapters remain deployable until further notice; verify current availability and compatibility when preparing Stage B.

If Stage A/B cannot recover a controlled E1 comparator, prepare a two-arm executable/judge run against the same immutable environment package. Use the existing E1 matched template as a planning starting point, not a promise of current platform compatibility: same model revision, LoRA parameters, trainer, seed, rollout settings, dataset hashes and evaluation schedule. Both arms must reach the same planned step/token envelope. Fix thresholds and completion/error rules before launch; no arm-specific extension selected from interim results.

If E2 still lacks genuine before/after training proof, prepare one executable-reward run with real scanner binaries and emitted backend provenance. Use a stable open-weight model that passes the tool-output smoke test; do not copy an unverified historical model revision. E2 judge/hybrid retraining is optional.

Historical templates specify E1 200 steps/batch 32/eight rollouts and E2 250 steps/batch 16/eight rollouts. The current CLI's batch semantics must be confirmed before estimating token volume: the meaning of batch size may already include rollouts. Choose a shorter bounded pilot only with an explicit rationale and stop budget; one-step compatibility success cannot fulfill the learning requirement. At least three training seeds would strengthen a general reward-source conclusion, but are a separately quoted extension rather than a silent expansion of the minimum pilot.

Before any paid launch, the review packet must include exact configs, source and data revisions, available compute, per-unit pricing, worst-case compute/inference/tool/storage totals, hard spend cap, stopping rules, and recovery/export settings. Stop when the envelope is exhausted or a predeclared infrastructure integrity rule fails; retain failed-run evidence.

## Preservation for new work

Retain authoritative local configs, manifests, raw rollouts, tool observations, metrics, model/adapter digests and package revisions. Keep account-level Prime read access while archival/SDK reads are needed. Prime Traces upload defaults and workspace settings should be documented in each launch packet; opt-out is not a substitute for deleting already stored traces.

[Prime's trace settings documentation](https://docs.primeintellect.ai/traces/pricing-and-settings) distinguishes account-level opt-out from per-client initialization, environment and CLI controls. Legacy routing through CLI v0.9.4 is transitional until November 6, not a permanent free tracing path. Keep account reads enabled during recovery and adapter/evaluation work, and verify the exact current per-client control before launch. No trace settings are changed by this plan.

The October notice states $1/GiB ingested plus $0.10/GiB/month stored, with no request or egress fees. Thus an upload of V GiB retained for M months has the stated trace-only cost V + 0.10VM dollars, excluding training/inference compute and any subsequent ingestion. Quote measured trace size and retention separately from experiment compute. Do not re-upload the complete legacy archives merely to retain them.

## Evidence and release checks

Run `make svbench-v0.1-check` for the offline package, and real run-manifest validation for reportable recovered runs. The empirical gate is a separate check: the proposed `results/research_completion.json` is created only from authentic completion evidence, never from a fixture copied into place. Follow its implemented schema and explicit check command; absence means empirical completion remains pending.

```bash
uv run python scripts/check_svbench_v01.py --research-complete
```

The evidence index maps `e1` and `e2` to `baseline_manifest`, `trained_manifest`, `training_manifest`, `metric`, `direction` and `split_provenance`; E1 also names `judge_manifest` and `judge_training_manifest`. Split provenance names train/held-out dataset hashes and ID-list paths; the gate checks that those lists are nonempty, unique and disjoint. Use an allowed common operational task-metric path and its documented improvement direction. Eval manifests require immutable model/source/data/scorer provenance and matching evaluation settings; training manifests identify the trained model digest and zero held-out overlap. E2 records tool backends. The gate checks internal evidence consistency and required improvement; it does not establish statistical significance, semantic patch preservation or independently attest every provenance assertion. Scientific review remains required.

Training manifests also require explicit `training_settings` with positive `batch_size` and nonempty `lora` and `optimizer` objects, plus `learning_curve_path` pointing to observed steps. The curve must include multiple distinct steps through the completed planned budget. E1 arms must share these settings and training source identity; evaluations must share source identity, and E2 must share scanner backend/version provenance. One-step pilots cannot pass.

Update this plan's evidence ledger as work resolves unknowns. Publication-ready claims should identify exact experiment artifacts, independent evaluation counts, common evaluator identity, matched fields, effect estimates and limitations. Ship the reviewable release candidate first; choose release tagging after examining those concrete results.
