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
| WP3a | Ready to run | Hosted RL proof for E1 executable reward. |
| WP3b | Ready to run | Hosted RL proof for E2 executable reward. |
| WP3c | Configured | Reward-source comparator for executable, LLM-judge, and hybrid rewards. |
| WP4 | Planned | Multi-reward stability ablations. |
| WP5 | In progress | SV-Bench v0.1 release package and technical report. |

## Definition of Done for v0.1

- E1/E2 public mini sets run through baseline commands.
- E1/E2 run manifests validate with `uv run svbench_manifest validate`.
- Reward-source comparison refuses unmatched budgets by default.
- `make svbench-v0.1-check` passes in a clean checkout.
- README, `SVBENCH.md`, status, roadmap, scoreboards, and technical report all state that v0.1 includes E1/E2 only.
- E5/E6 unsafe or offensive corpora are absent from public release artifacts.

## Known Blockers and Unknowns

- Hosted training budget/results are not included until runs are actually launched and manifests are attached.
- GDPO support is represented as a clearly named decoupled-normalization placeholder until runtime support is confirmed.
- Prime Lab CLI naming can drift; `make lab-check` is the compatibility gate before live hosted runs.
- E2 semantic patch preservation is the highest-risk scoring area and must be re-reviewed before using results in a paper claim.

## Guardrail

Do not expand E3-E6 before SV-Bench v0.1. E3-E6 work may add beta smoke tests, safety policies, public mini fixtures, docs, and suite-v1 checklists, but v0.1 claims and release artifacts must remain E1/E2-only.
