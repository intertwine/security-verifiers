# Versioning and Reproducibility

This document specifies pinned versions for Security Verifiers to ensure reproducible evaluations and training runs.

## Core Dependencies

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12.x | Required for all environments |
| verifiers | >=0.1.9 | Prime Intellect RL framework |
| security-verifiers-utils | >=0.2.2 | Shared utilities package |

## Security Analysis Tools (E2)

Tool versions are pinned in `environments/sv-env-config-verification/ci/versions.txt`:

| Tool | Version | Purpose |
|------|---------|---------|
| kube-linter | 0.7.6 | Kubernetes manifest analysis |
| OPA | 1.8.0 | Open Policy Agent for Rego policies |
| Semgrep | 1.137.0 | Static analysis for IaC |

These versions are used in CI and should be matched locally for reproducible results:

```bash
# Check local versions
kube-linter version
opa version
semgrep --version
```

## Dataset Versioning

Datasets are versioned by filename convention and content hash:

### E1 (Network Logs)
- `iot23-train-dev-test-v1.jsonl` - Primary IoT-23 dataset (N=1800)
- `cic-ids-2017-ood-v1.jsonl` - OOD evaluation (N=600)
- `unsw-nb15-ood-v1.jsonl` - OOD evaluation (N=600)

### E2 (Config Verification)
- `k8s-labeled-v1.jsonl` - Kubernetes configs (N=444)
- `terraform-labeled-v1.jsonl` - Terraform configs (N=115)
- `combined` - Both datasets (N=559)

Dataset content hashes are recorded in `metadata.json` for each eval run.

## Evaluation Metadata Requirements

Every evaluation run must record in `metadata.json`:

```json
{
  "environment": "sv-env-network-logs",
  "env_version": "0.2.10",
  "model": "gpt-5-mini",
  "effective_model": "gpt-5-mini",
  "dataset": "iot23-train-dev-test-v1.jsonl",
  "dataset_revision": "sha256:abc123...",
  "timestamp": "2026-01-24T12:00:00Z",
  "git_commit": "89f731c",
  "python_version": "3.12.8",
  "verifiers_version": "0.1.9.post3",
  "temperature": 0.2,
  "max_tokens": 2048,
  "seed": 42,
  "tool_versions": {
    "kube_linter": "0.7.6",
    "semgrep": "1.137.0",
    "opa": "1.8.0"
  }
}
```

## Version Bumping

Environment versions follow semantic versioning:
- **Patch** (0.0.x): Bug fixes, no API changes
- **Minor** (0.x.0): New features, backward compatible
- **Major** (x.0.0): Breaking changes

Use Makefile targets:
```bash
make update-version E=network-logs BUMP=patch
make update-version E=config-verification BUMP=minor
```

## CI Version Enforcement

The CI pipeline (`ci.yml`) installs exact versions from `ci/versions.txt` to ensure consistent test results. Local development should match these versions for reproducibility.

## Checking Versions Locally

```bash
# Python
python --version

# verifiers
python -c "import verifiers; print(verifiers.__version__)"

# Environment package versions
python -c "from importlib.metadata import version; print(version('sv-env-network-logs'))"

# Security tools (E2)
source environments/sv-env-config-verification/ci/versions.txt
echo "Expected: kube-linter=$KUBELINTER_VERSION, opa=$OPA_VERSION, semgrep=$SEMGREP_VERSION"
```
