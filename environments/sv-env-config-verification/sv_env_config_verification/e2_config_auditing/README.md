# E2 Configuration Auditing

Lightweight reference implementation using real tool adapters (OPA, KubeLinter, Semgrep) with
severity-normalized violations and patch-aware rewards. Kubernetes and Terraform fixtures live
under `dataset/fixtures/` with corresponding oracle outputs in `dataset/oracle/`. Tool versions
are pinned in `ci/versions.txt` to ensure deterministic results.

## Tests

```bash
make e2-test
```

## Oracle Regeneration

Rebuild oracle labels after updating fixtures or tool versions:

```bash
make e2-regenerate-oracle
```

## Baseline

```bash
make e2-baseline-tools
```

The baseline emits the oracle findings as the model prediction for quick sanity checks.
