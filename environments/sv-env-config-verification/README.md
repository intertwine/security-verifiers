Security Verifiers environment for **Configuration Auditing** (PRD Environment E2).

This environment wraps the `e2_config_auditing` package which runs real
security linters against configuration files and computes executable rewards.
It exposes Kubernetes and Terraform fixtures with precomputed oracle outputs.

## Input / Output

**Input:** raw configuration text (YAML or HCL).

**Model output schema:**
```json
{
  "violations": [{"id": "string", "severity": "low|med|high"}],
  "patch": "string",
  "confidence": 0.0
}
```

## Tools

The environment exposes deterministic wrappers around pinned tools:
- `kubelinter_lint` – Kubernetes static analysis with file and line range metadata
- `semgrep_scan` – Terraform / generic pattern scanning
Tool versions are pinned in `e2_config_auditing/ci/versions.txt` to ensure reproducibility.

## Reward

Rewards are computed with `e2_config_auditing.reward.final_reward`, combining
severity-weighted F1 with credit for violations removed after applying a
proposed patch and re-running the tools.

## Usage

```python
from sv_env_config_verification import load_environment

env = load_environment()
sample = env.dataset[0]
print(sample["question"])  # config text
print(sample["answer"]["oracle"])  # oracle violations
```

Install in editable mode:
```bash
uv pip install -e environments/sv-env-config-verification
```

Run tests for just this environment:
```bash
make test-env E=config-verification
```

Regenerate oracle labels if fixtures or tool versions change (run from repository root):

```bash
make e2-regenerate-oracle
```
