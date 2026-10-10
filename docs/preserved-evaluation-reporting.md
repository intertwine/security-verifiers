# Common reporting for preserved-policy evaluations

Run the bounded evaluator first, then report its actual retained outputs:

```bash
python3 scripts/report_preserved_evaluation.py \
  --run-dir outputs/evals/preserved-primary-20261010 \
  --output outputs/completion_20261010/paired_report \
  --loss-weights /path/to/frozen-e1-loss-weights.json \
  --e2-verification /path/to/e2-verification.jsonl
```

The output is `summary.json` and `report.md`. This script makes no API calls and never writes an empirical completion index. Offline test fixtures do not represent experiments.

## Inputs and denominators

The runner's `packet.json` names each frozen dataset. Each policy folder contains `metadata.json` and `results.jsonl`; result rows must match the exact frozen `case_id`, prompt and reference answer. Duplicate/unexpected case identities and mismatched packet, dataset, policy or limits metadata are rejected. Missing results, including interrupted attempts, remain missing against the frozen case denominator. Request failures, caps and malformed outputs remain explicit outcomes. E1 labels must use the exact common-schema enum `Benign`, `Malicious`, or `Abstain`. The runner's frozen source fingerprints are included when available. Outputs are parsed from the final content channel only: whole JSON or a whole JSON fence, never salvaged nested objects or reasoning text.

E1's primary reporting convention uses FN=10, FP=1, abstention=1, invalid/failure/missing=10, correct=0, averaged over all planned cases. Supply a frozen `fn`/`fp`/`abstain`/`invalid` JSON weight object before generating outputs and retain it with the launch packet. These abstention and failure losses are explicit evaluation decisions, not recovered historical rewards. They prevent selective nonresponses from appearing as free operational improvements. A report created after selecting weights is descriptive and must not be presented as preregistered. Per-case confidence/correctness and outcome counts are retained for supporting calibration and coverage analysis.

Pairing uses the same independent case IDs for base and each trained policy. Only cases with actual observed outputs for both policies and known primary scores enter paired differences. Missing pairs remain counted and excluded explicitly; reported all-case means and observed paired effects can therefore differ. A completed failed episode contributes its declared failure loss rather than disappearing. The fixed seed is 20261010; 10,000 percentile bootstrap draws resample case pairs. Deltas are policy minus base: negative favors E1 cost, positive favors E2 success. Case hashes identify inputs but cannot prove statistical independence. The report carries the packet's explicit independence status; intervals should not be interpreted as generalization evidence without reviewing it. Observed-pair intervals exclude missing cases and may be biased when missingness differs by policy; use complete paired runs for confirmatory claims.

## E2 verification contract

A valid E2 JSON response alone has unknown primary patch success. A scanner passing after resource deletion or an unexamined functional change does not establish security success. Attach separate verification JSONL rows:

```json
{
  "policy_role": "exec",
  "case_id": "actual-frozen-case-id",
  "completion_sha256": "sha256-of-the-exact-final-content-UTF8",
  "patch_sha256": "sha256-of-the-exact-JSON-patch-string-UTF8",
  "scanner_success": true,
  "structure_preserved": true,
  "semantic_preserved": true,
  "tool_versions": {"opa": "actual-version-output"},
  "evidence_path": "verification/actual-case.json",
  "evidence_sha256": "sha256-of-the-evidence-file"
}
```

The linked evidence JSON must repeat the exact completion and patch digests, scanner/structure/semantic outcomes and tool versions. Its checksum is verified; disagreement or absent evidence fails reporting. The witness must retain real scanner outputs and functional checks supporting semantic preservation. The reporter checks linkage and consistency, not the truth of an arbitrary attestation; scientific review remains necessary. Structural guards alone cannot justify `semantic_preserved: true`.

Verified success is one only when all three explicit outcomes pass. Malformed, failed or missing model episodes are unsuccessful outcomes. Valid outputs without verification remain unknown, and the full primary mean remains null until every planned case has a known score. The separate observed-subset mean and paired denominator expose partial verification. Vulnerable cases require a nonempty patch; even an all-positive attestation cannot credit an empty patch. Clean cases require `verification_protocol: "clean-no-regression-v1"` and an explicit boolean `clean_no_regression_success` in both the sidecar and witness. Clean/vulnerable case counts remain separate supporting denominators. Do not count an empty patch on a vulnerable case as success merely because output JSON is valid.

Neither paired intervals, scanner checks nor this report fulfill the missing matched-training and authentic provenance requirements automatically. Run the separate research gate only once its required artifacts exist.

The supporting E2 finding metric is unweighted unique-ID F1, labeled explicitly, with the common evaluator's primary tool filter: kube-linter for Kubernetes and semgrep for Terraform when tool-style IDs are present. It is not a weighted training reward.
