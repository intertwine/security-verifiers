# Security Configuration Auditing (Work in Progress)

Security Verifiers RL environment for **Tool-Using Security Configuration Auditing** - implementing Environment E2 from the [PRD](../../PRD.md).

## Overview

This environment (currently in development) will implement advanced configuration auditing where models use professional security tools to prove violations and propose patches. Unlike traditional approaches, rewards are based on machine-verified outcomes using OPA/Rego policies, KubeLinter, and Semgrep.

## Planned Features (Per PRD Specification)

### Input/Output Schema

- **Input**: K8s manifests, Terraform configs, cloud IAM policies, etc.
- **Output Schema**:

```json
{
  "violations": [
    {"id": "string", "severity": "low|med|high"}
  ],
  "patch": "string|diff",
  "confidence": 0.0..1.0
}
```

### Tool Integration

The model will have access to:

- **OPA/Rego**: Policy-as-code engine for declarative security rules
- **KubeLinter**: Kubernetes manifest static analysis
- **Semgrep**: Semantic code analysis for infrastructure-as-code

### Reward Structure

- Weighted true violations found/fixed (severity-based scoring)
- Penalties for false claims
- Format compliance bonuses
- Extra reward for minimal, correct patches

## Key Innovations

1. **Executable Verification**: Uses actual security tools as ground truth, not LLM judgments

2. **Tool-Use Learning**: Model learns when and how to invoke different tools for different config types

3. **Patch Generation**: Goes beyond detection to propose minimal fixes that satisfy policies

4. **Severity-Aware Scoring**: Critical violations worth more than informational findings

## Current Status

This environment is a work in progress. The current implementation provides basic configuration checking as a foundation. Future development will add:

- Full OPA/Rego integration for declarative policy checking
- KubeLinter and Semgrep tool wrappers
- Patch generation and validation
- Multi-turn refinement of fixes

See [PRD.md](../../PRD.md) Environment E2 for full specifications.

## Example Workflow (Target Implementation)

```text
Input: K8s deployment with privileged container
Model → calls kubelinter_yaml() tool
Tool → returns security violations
Model → calls opa_check() for policy validation
Model → generates patch removing privileged flag
Output: {"violations": [{"id": "privileged-container", "severity": "high"}],
         "patch": "...", "confidence": 0.95}
```

## Structure

- `sv_env_config_verification.py`: Main implementation file
- `sv_env_config_verification_test.py`: Test suite

## Local Install (editable)

From repo root after creating a uv venv:

```bash
uv pip install -e environments/sv-env-config-verification
```

## Related Work

This environment is part of the Open Security Verifiers suite. For the complete vision, see:

- [EXECUTIVE_SUMMARY.md](../../EXECUTIVE_SUMMARY.md) - Project overview
- [PRD.md](../../PRD.md) - Detailed specifications for all six environments
