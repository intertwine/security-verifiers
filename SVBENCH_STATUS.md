# SV-Bench Status

This is the canonical contributor map for the current benchmark push.

## Release Boundary

SV-Bench v0.1 is scoped to E1 and E2 only:

- E1 `sv-env-network-logs`: production benchmark environment.
- E2 `sv-env-config-verification`: production benchmark environment.

E3-E6 remain suite beta or preview work until the v0.1 empirical proof is complete. Do not expand E3-E6 public corpora or treat them as v0.1 release criteria.

## Environment Status

| ID | Environment | Status | v0.1 Included | Notes |
|---|---|---|---|---|
| E1 | `sv-env-network-logs` | Production | Yes | Calibrated network-log classification with abstention and asymmetric cost. |
| E2 | `sv-env-config-verification` | Production | Yes | Tool-grounded configuration audit and patch verification. |
| E3 | `sv-env-code-vulnerability` | Beta slice | No | Defensive toy repair tasks only; suite beta after v0.1. |
| E4 | `sv-env-phishing-detection` | Beta slice | No | Calibrated email classification with safe evidence snippets. |
| E5 | `sv-env-redteam-attack` | Preview/beta safety slice | No | Sanitized simulator only; no raw harmful corpus. |
| E6 | `sv-env-redteam-defense` | Preview/beta safety slice | No | Safe helpfulness/harmlessness balance tests. |

E5/E6 offensive or adversarial corpora must not be expanded or publicly released for SV-Bench v0.1. Public examples must remain sanitized, non-operational, and suitable for defensive evaluation.

## Completed Work Packages

| Package | Status | Evidence |
|---|---|---|
| WP0 | Complete | Benchmark integrity hardening and public/gated split foundations. |
| WP1 | Complete | E1/E2 report generator, summary schema, and scoreboards. |
| WP2 | Complete | Public mini sets and baseline wrappers. |
| WP2.5 | Complete | Prime Lab integration scaffolding and hosted-run configs. |
| WP2.5a | Complete | Hosted-style fallback normalization and Prime compatibility checks. |

## Open Work Packages

| Package | Status | Required Outcome |
|---|---|---|
| WP3a | Training recovered; held-out proof pending | Completed E1 runs and adapters preserved; establish independent before/after operational deltas. |
| WP3b | Pilot and older training recovered; held-out proof pending | Preserve E2 tool/backend limitations; establish verified before/after task performance. |
| WP3c | Exploratory pilots recovered | E1 judge environment differs; controlled common-evaluator comparison remains required. |
| WP4 | Planned | Multi-reward stability ablations. |
| WP5 | In progress | SV-Bench v0.1 release package and technical report. |

## Definition of Done for v0.1

- E1/E2 public mini sets run through baseline commands.
- E1/E2 run manifests validate with `uv run svbench_manifest validate`.
- Reward-source comparison refuses unmatched budgets by default.
- `make svbench-v0.1-check` passes in a clean checkout.
- README, `SVBENCH.md`, status, roadmap, scoreboards, and technical report all state that v0.1 includes E1/E2 only.
- E5/E6 unsafe or offensive corpora are absent from public release artifacts.

These packaging checks do not establish the original empirical proof. Research completion also requires E1/E2 learning evidence, independent held-out operational improvement and a matched E1 executable/judge comparison with common evaluator, immutable provenance and audited disjoint splits. `scripts/check_svbench_v01.py --research-complete` checks that evidence separately; it currently fails because authentic completion evidence has not yet been assembled. See [the completion plan](docs/COMPLETION-PLAN-2026-10.md).

## October 2026 Preservation and Completion

Both Prime legacy workspace exports were downloaded before the November 6 retirement. They preserve 70 training records and 172 evaluation datasets. All 123 committed curated samples match the exported shared fields; each curated E1 run has 160 archived samples across five steps. Ten model adapters were saved separately because sample exports exclude model weights. Raw exports and reconstructed records remain private, outside tracked release artifacts.

The offline importer preserves repeated historical IDs with member/row provenance. Recovered training samples and source-specific reward curves remain training diagnostics, not independent evaluations. E2 duplicate-finding reward inflation and structural deletion bypasses now have focused guards and regression coverage; these guards do not prove functional equivalence, and historical results retain their original scorer behavior.

## Known Blockers and Unknowns

- Hosted training has occurred; preserved results still lack sufficient immutable provenance and common held-out evidence for the original research claims.
- GDPO support is represented as a clearly named decoupled-normalization placeholder until runtime support is confirmed.
- Prime Lab CLI naming can drift; `make lab-check` is the compatibility gate before live hosted runs.
- E2 semantic patch preservation is the highest-risk scoring area and must be re-reviewed before using results in a paper claim.

## Guardrail

Do not expand E3-E6 before SV-Bench v0.1. E3-E6 work may add beta smoke tests, safety policies, public mini fixtures, docs, and suite-v1 checklists, but v0.1 claims and release artifacts must remain E1/E2-only.
