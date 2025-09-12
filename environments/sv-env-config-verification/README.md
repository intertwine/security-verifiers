# Security Configuration Auditing

Security Verifiers RL environment for **Tool‑Using Security Configuration Auditing** – implementing Environment E2 from the [PRD](../../PRD.md).
Models inspect configuration files, invoke lightweight analysis tools, and
return a structured report of violations with optional patches.

## Input/Output Schema

**Input:** configuration text (SSH, firewall, IAM policy, nginx config,
OPA/Rego policy, Kubernetes config, or code snippet for semgrep-style
rules).

**Expected model output**:

```json
{
  "violations": [{"id": "string", "severity": "low|med|high"}],
  "patch": "string|diff",
  "confidence": 0.0..1.0
}
```

## Tools

The environment exposes deterministic analysis tools used by the model and
for dataset generation:

- `analyze_ssh_config`
- `analyze_firewall_rules`
- `analyze_iam_policy`
- `analyze_nginx_config`
- `analyze_rego_policy`
- `analyze_k8s_config`
- `analyze_semgrep_code`

Each tool returns the schema above, enabling executable rewards and expanded
coverage beyond the initial four config types.

## Reward

Rewards combine:

1. **Analysis accuracy** – weighted match between reported violations and the
   oracle output.
2. **Format bonus** – strict JSON schema adherence.
3. **Tool bonus** – extra credit when any tool is called.
4. **Patch bonus** – small reward if a patch is proposed.

All components are normalized to the `[0.0, 1.0]` range.

## Usage

```python
from sv_env_config_verification import load_environment

env = load_environment(max_examples=2)
print(env.dataset[0]["question"])  # configuration text
print(env.dataset[0]["answer"])     # oracle violations
```

Install locally in editable mode:

```bash
uv pip install -e environments/sv-env-config-verification
```

Run tests for just this environment:

```bash
make test-env E=config-verification
```

## Related Documents

- [EXECUTIVE_SUMMARY.md](../../EXECUTIVE_SUMMARY.md)
- [PRD.md](../../PRD.md)
