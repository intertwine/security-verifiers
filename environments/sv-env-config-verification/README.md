# sv-env-config-verification

Security Verifiers RL environment for **Security Policy Verification for Configurations** - a ToolEnv implementation where models audit security configuration files to identify misconfigurations or policy violations.

## Overview

This environment implements PRD Environment #2: An interactive setting using ToolEnv where the model audits security configuration files (system configs, cloud policies, etc.) to identify misconfigurations or policy violations. The model can invoke analysis tools to parse or test the config and produce either a compliance verdict (secure/insecure) or a list of detected issues.

## Task Description

- **Input**: Security configuration files (SSH configs, firewall rules, cloud IAM policies, etc.)
- **Output**: Compliance verdict or list of detected security issues
- **Environment Type**: ToolEnv (model can call analysis tools)
- **Reward**: Based on accuracy of issue detection and avoiding false positives

## Example

```text
Prompt: "Audit this SSH configuration: PermitRootLogin yes, PasswordAuthentication yes"
Model uses tools to analyze config
Expected Output: "Found issues: Root login is enabled; Password authentication allows brute force attacks"
```

## Implementation

Uses the Verifiers framework with:

- Dataset: Security configuration files with known vulnerabilities
- Tools: Configuration analysis functions (e.g., SSH config parser, firewall rule analyzer)
- Rubric: Compares detected issues against ground truth vulnerabilities
- Reward function: +1 for each correctly identified issue, penalty for false positives

## Why This Task is Useful

- **DevSecOps**: Misconfigurations are a top cause of security breaches (90% of applications have some misconfiguration)
- **Automation**: Helps catch human errors early in configuration management
- **Policy Compliance**: Trains models to serve as policy compliance auditors following security benchmarks (OWASP, CIS hardening guides)
- **Practical Application**: Can tirelessly scan configurations for vulnerabilities, providing a second line of defense

## Structure

- `sv_env_config_verification.py`: Main implementation file
- `sv_env_config_verification_test.py`: Test suite

## Local install (editable)

From repo root after creating a uv venv:

```bash
uv pip install -e environments/sv-env-config-verification
```
