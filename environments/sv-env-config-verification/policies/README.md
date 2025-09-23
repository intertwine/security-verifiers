# OPA Policies for Configuration Auditing

This directory contains example Open Policy Agent (OPA) Rego policies for security auditing of Kubernetes and Terraform configurations.

## Policy Files

### `kubernetes_security.rego`

Main policy file for Kubernetes resource security checks. Includes checks for:

- **K8S_001**: Insecure capabilities (SYS_ADMIN, NET_ADMIN)
- **K8S_002**: Privileged containers
- **K8S_003**: HostPath volume usage
- **K8S_004**: Exposed sensitive ports (SSH, RDP)
- **K8S_005**: ConfigMaps with potential sensitive data
- **GEN_001**: Missing resource limits
- **GEN_002**: Use of default namespace

### `lib.rego`

Library functions for Kubernetes-specific checks and validations.

### `terraform_security.rego`

Policy file for Terraform configuration security checks. Includes checks for:

- **TF_001**: S3 bucket encryption
- **TF_002**: S3 bucket versioning
- **TF_003**: S3 bucket public access
- **TF_004**: RDS encryption
- **TF_005**: RDS weak password policies
- **TF_006**: Security groups allowing all traffic
- **TF_007**: Hardcoded secrets in variables

### `terraform_lib.rego`

Library functions for Terraform-specific checks and validations.

## Usage

To use these policies with the OPA adapter:

```python
from adapters.opa_adapter import opa_eval

# For Kubernetes YAML
findings = opa_eval(
    input_data=k8s_yaml_content,
    policy_paths=[
        "policies/lib.rego",
        "policies/kubernetes_security.rego"
    ],
    query="data.security.deny"
)

# For Terraform JSON
findings = opa_eval(
    input_data=terraform_json,
    policy_paths=[
        "policies/terraform_lib.rego",
        "policies/terraform_security.rego"
    ],
    query="data.security.deny"
)
```

## Policy Structure

Each policy violation returns an object with:

- `id`: Unique identifier for the violation
- `message`: Human-readable description
- `severity`: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- `file`: Source file name
- `category`: Violation category (security, encryption, access-control, etc.)

## Customization

To add new policies:

1. Create new `.rego` files in this directory
2. Follow the naming convention `{domain}_{type}.rego`
3. Use the `deny[msg]` rule format
4. Include appropriate library functions in `lib/` subdirectory
5. Update this README with new violation IDs

## Testing

Test policies using OPA CLI:

```bash
opa eval --data policies/lib.rego --data policies/kubernetes_security.rego \
         --input input.json --format=json "data.security.deny"
```
