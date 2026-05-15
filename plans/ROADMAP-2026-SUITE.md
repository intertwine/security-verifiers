# Security Verifiers Roadmap 2026

## SV-Bench v0.1

Scope: E1 and E2 only.

| Milestone | Outcome |
|---|---|
| Status docs | README, `SVBENCH_STATUS.md`, and `SVBENCH.md` explain the E1/E2 boundary. |
| Prime Lab GA path | Baseline eval, hosted training configs, hosted eval/fallback eval docs, and normalization. |
| Run manifests | Every reportable run has a validated machine-readable manifest. |
| Baselines | Public mini-set E1/E2 scoreboards and operational metrics. |
| Reward comparator | Executable vs LLM-judge vs hybrid comparison with matched-budget enforcement. |
| Release package | Technical report, leaderboard, heldout policy, and `make svbench-v0.1-check`. |

## Security Verifiers Suite v1.0

Scope: all six environments, after SV-Bench v0.1 proof.

| Environment | Target for Suite v1.0 |
|---|---|
| E1 network logs | Production benchmark environment. |
| E2 config verification | Production tool-use benchmark environment. |
| E3 code vulnerability | Sandboxed defensive beta slice. |
| E4 phishing detection | Calibrated beta classifier with evidence. |
| E5 red-team attack | Sanitized simulator; no raw harmful prompt corpus. |
| E6 red-team defense | Helpfulness/harmlessness beta with adversarial turns. |

Suite v1.0 requires `make suite-v1-check` to pass and must distinguish production, beta, alpha, gated, and restricted components.
