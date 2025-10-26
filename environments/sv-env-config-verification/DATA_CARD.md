# E2 — Security Config Verification (tool-labeled corpus + patch-verified subset)

- **Owner:** intertwine
- **Env:** `sv-env-config-verification`
- **Version:** v1

## Sources

- **Kubernetes YAML:** OSS manifests/Helm charts (curated), scanned via **OPA/Rego (primary oracle)** + **KubeLinter** + **Semgrep-k8s**
- **Terraform HCL:** OSS modules (AWS/Azure/GCP primitives), scanned via **Semgrep-tf** + **OPA policies**

Why: E2 rewards **tool-grounded detection** and **patch validity (re-scan)**; OPA acts as primary oracle per environment design.

## Construction

- **Script:** `scripts/data/build_e2_k8s_tf.py`
- **Emitted files:**
  - `k8s-labeled-v1.jsonl` — YAML with `info.violations[]` from tools
  - `terraform-labeled-v1.jsonl` — HCL with `info.violations[]`
  - `tools-versions.json` — Exact tool versions used for scanning
  - `sampling-e2-v1.json` — Sampling metadata (scan stats, tool versions)
  - `k8s-patch-verified-v1.jsonl` — optional subset where minimal patches remove OPA violations upon re-scan
- **Schema:** one JSONL item per file:

  ```json
  {
    "prompt": "<raw config>",
    "info": {
      "violations": [
        {
          "tool": "...",
          "rule_id": "...",
          "severity": "...",
          "msg": "...",
          "loc": "..."
        }
      ],
      "patch": "<unified diff or JSON patch | null>"
    },
    "meta": { "lang": "k8s|tf", "source": "<path>", "hash": "<sha256-short>" }
  }
  ```

## Dataset Access

### ⚠️ Important: Training Contamination Prevention

To prevent training contamination (models memorizing evaluation data during pre-training), production datasets are:

- **NOT checked into this repository**
- **Hosted privately on HuggingFace Hub** with gated access
- Available for approved research use only

### Public Metadata

**Browse dataset information, tool versions, and composition:**

- <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata>

The public metadata repo includes:

- Sampling metadata showing how datasets were constructed
- Tools versions (KubeLinter, Semgrep, OPA) for reproducibility
- Model cards explaining the privacy rationale and dataset composition
- Multi-turn performance metrics (models achieve ~0.93 reward with tool calling vs ~0.62 without)
- Instructions for requesting access to full datasets

### For Users: Request Access to Full Datasets

**To access the full private datasets:**

1. Open an access request issue: [Security Verifiers Issues](https://github.com/intertwine/security-verifiers/issues)
2. Use the title: "Dataset Access Request: E2"
3. Include: name, affiliation, research purpose, HuggingFace username
4. Commitment to not redistribute or publish the raw data

**Approval criteria:**

- Legitimate research or educational use
- Understanding of contamination concerns
- Agreement to usage terms

We typically respond within 2-3 business days.

### For Approved Researchers: Download Private Datasets

If you have been granted access:

```bash
# Set your HuggingFace token
export HF_TOKEN=your_token_here

# Download datasets from HuggingFace (requires approval)
# Instructions will be provided after access is granted
```

### For Contributors: Build Datasets Locally

If you need to rebuild datasets from scratch:

**Prerequisites:**

- Security tools installed: kube-linter, semgrep, opa
- HuggingFace token (HF_TOKEN) in `.env` for dataset access
- Source K8s YAML and Terraform HCL repositories

**Build Production Datasets** (not committed):

The easiest way to build E2 datasets is using the automated clone script:

```bash
# 1. Clone recommended source repositories (one-time setup)
make clone-e2-sources

# This clones to scripts/data/sources/ (gitignored):
#   - kubernetes/examples (462 YAML files)
#   - GoogleCloudPlatform/microservices-demo
#   - ContainerSolutions/kubernetes-examples
#   - terraform-aws-modules/vpc
#   - terraform-aws-modules/eks
#   - terraform-aws-modules/rds (260 HCL files)

# 2. Build datasets from cloned sources
make data-e2-local
```

**Custom Sources** (Advanced):

If you want to use your own K8s/Terraform repositories:

```bash
# Build from custom paths
make data-e2 K8S_ROOT=/path/to/k8s/manifests TF_ROOT=/path/to/terraform/modules

# With patches (optional)
make data-e2 K8S_ROOT=/path/to/k8s TF_ROOT=/path/to/tf PATCHES_DIR=/path/to/patches
```

**Build Test Fixtures** (checked in for CI):

```bash
# Small datasets for CI testing (requires cloned sources first)
make clone-e2-sources   # One-time setup
make data-e2-test       # Builds *-test.jsonl files
```

### Recommended Source Repositories

The `clone-e2-sources` script automatically clones these repositories:

**Kubernetes (recommended):**

- Official: `github.com/kubernetes/examples` — Canonical K8s examples
- Google Demo: `github.com/GoogleCloudPlatform/microservices-demo` — Production-like microservices
- Container Solutions: `github.com/ContainerSolutions/kubernetes-examples` — Real-world patterns

**Kubernetes (alternative sources):**

- SLI-Kube dataset: 2,039 manifests from `github.com/paser-group/KubeSec` (academic corpus)

**Terraform (recommended):**

- AWS VPC: `github.com/terraform-aws-modules/vpc` — Networking primitives
- AWS EKS: `github.com/terraform-aws-modules/eks` — Kubernetes on AWS
- AWS RDS: `github.com/terraform-aws-modules/rds` — Database configs

**Terraform (alternative sources):**

- Azure modules: `github.com/Azure/terraform-azure-modules`
- GCP foundation: `github.com/terraform-google-modules/terraform-example-foundation`

### Data Structure

The build script generates the following files in `environments/sv-env-config-verification/data/`:

**Primary Datasets:**

- `k8s-labeled-v1.jsonl` — Kubernetes manifests with violation metadata
- `terraform-labeled-v1.jsonl` — Terraform configs with violation metadata

**Metadata Files:**

- `sampling-e2-v1.json` — Build reproducibility metadata (sources, counts, tool versions)
- `tools-versions.json` — Exact security tool versions used for scanning

**Optional:**

- `k8s-patch-verified-v1.jsonl` — Subset where patches fix violations (requires patches dir)

### Example Output

```json
{
  "k8s_root": "/tmp/e2-minimal/k8s",
  "tf_root": "/tmp/e2-minimal/tf",
  "rego_dir": "environments/sv-env-config-verification/policies",
  "datasets": {
    "k8s": {
      "files_scanned": 1,
      "total_items": 1,
      "with_violations": 1
    },
    "terraform": {
      "files_scanned": 1,
      "total_items": 1,
      "with_violations": 1
    }
  },
  "tools": {
    "kube-linter": "0.7.6",
    "semgrep": "1.137.0",
    "opa": "1.8.0"
  }
}
```

## Dataset Statistics

### Kubernetes Dataset (v1.1 - October 2025)

| Metric                     | Value                                                    |
| -------------------------- | -------------------------------------------------------- |
| Total files scanned        | 444 (after validation filtering)                         |
| Files with violations      | 255 (57.4%)                                              |
| Total violations detected  | 1503                                                     |
| Avg violations per file    | 3.4                                                      |
| **Violation breakdown:**   |                                                          |
| KubeLinter                 | 1062 (70.7%)                                             |
| Semgrep                    | 441 (29.3%)                                              |
| **Severity distribution:** |                                                          |
| Medium                     | 1062                                                     |
| WARNING                    | 247                                                      |
| INFO                       | 194                                                      |
| **Content validation**     | 100% valid K8s manifests                                 |
| **Filtering improvements** | Removed 18 non-manifest files (LICENSE, README, scripts) |

### Terraform Dataset (v1.1 - October 2025)

| Metric                     | Value                                                   |
| -------------------------- | ------------------------------------------------------- |
| Total files scanned        | 115 (after validation filtering)                        |
| Files with violations      | 4 (3.5%)                                                |
| Total violations detected  | 4                                                       |
| Avg violations per file    | 0.03                                                    |
| **Violation breakdown:**   |                                                         |
| Semgrep                    | 4 (100%)                                                |
| **Severity distribution:** |                                                         |
| WARNING                    | 4                                                       |
| **Content validation**     | 0 empty files, all valid HCL                            |
| **Filtering improvements** | Removed 145 invalid files (empty vars, non-HCL content) |

**Quality Improvements (v1.1 - October 2025):**

- ✅ **K8s filtering:** Added content validation for K8s API markers (apiVersion, kind, metadata, spec)

  - Filtered 462 → 444 files (removed 18 non-manifests)
  - 100% valid K8s YAML (was 96.3%)

- ✅ **Terraform filtering:** Added HCL content validation before scanning

  - Filtered 260 → 115 files (removed 145 empty/invalid files)
  - 0 empty prompts (was 39 empty files)
  - All files contain valid HCL blocks (resource, module, data, variable, output, provider)

- ✅ **Tool versions:** Pinned and documented for reproducibility
  - kube-linter: 0.7.6
  - semgrep: 1.137.0
  - opa: 1.8.0

**Note on Terraform violation rate:** The low violation rate (3.5%) reflects high-quality source repositories (terraform-aws-modules). This is expected for production-grade modules. For more violations, consider:

- Adding custom OPA policies for organization-specific rules
- Using `tflint` or `checkov` in addition to Semgrep
- Sourcing from less mature repositories
