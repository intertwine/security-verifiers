---
license: other
license_name: security-verifiers-eval-only
license_link: https://github.com/intertwine/security-verifiers/blob/main/docs/DATASET_EVAL_ONLY_LICENSE.md
gated: true
extra_gated_heading: "Request access (evaluation only)"
extra_gated_description: "This dataset is gated for benchmark integrity. Access is granted for evaluation purposes only. Manual approval required."
extra_gated_button_content: "Request evaluation access"
extra_gated_prompt: "You agree to use this dataset for evaluation only (no training/fine-tuning/redistribution)."
extra_gated_fields:
  Affiliation: text
  Intended use:
    type: select
    options: ["Evaluation-only", "Other (explain in Notes)"]
  Contact email: text
  HF username: text
  Brief description of research: text
  I agree to EVAL-ONLY license: checkbox
task_categories:
  - text-generation
language:
  - en
tags:
  - security
  - infrastructure-as-code
  - kubernetes
  - terraform
  - rego
  - cybersecurity
  - gated
  - evaluation
pretty_name: Security Verifiers E2 (Private) - Config Verification
size_categories:
  - n<1K
---

# E2 — Security Config Verification (Private Gated Dataset)

**Owner:** intertwine • **Env:** `sv-env-config-verification` • **Version:** v1

## ⚠️ Gated Access

This repository hosts the **private canonical dataset** for E2 (Config Verification) used by the `sv-env-config-verification` environment.

**Why gated?**

- Prevents training contamination (models memorizing evaluation data)
- Maintains benchmark integrity for research
- Ensures fair model comparisons

**Access is granted for:**

- Evaluation of pre-trained models
- Reporting aggregate metrics in publications
- Research on AI safety and security

**Access is NOT granted for:**

- Training or fine-tuning models
- Including in pre-training corpora
- Commercial use without permission
- Redistribution

## How to Request Access

1. **Click "Request access"** button above
2. **Fill out the gating form** with your research details
3. **Wait for manual approval** (typically within 2-3 business days)
4. **Set HF_TOKEN** once approved:

   ```bash
   export HF_TOKEN=hf_your_token_here
   ```

## Dataset Sources

- **Kubernetes YAML:** OSS manifests/Helm charts (curated), scanned via **OPA/Rego (primary oracle)** + **KubeLinter** + **Semgrep-k8s**
- **Terraform HCL:** OSS modules (AWS/Azure/GCP primitives), scanned via **Semgrep-tf** + **OPA policies**

Why: E2 rewards **tool-grounded detection** and **patch validity (re-scan)**; OPA acts as primary oracle per environment design.

## Dataset Splits

This repository contains the following splits:

| Split       | Description                                       | Size          |
| ----------- | ------------------------------------------------- | ------------- |
| `k8s`       | Kubernetes manifests with tool-labeled violations | ~444 examples |
| `terraform` | Terraform configs with tool-labeled violations    | ~115 examples |
| `train`     | Combined K8s + Terraform dataset                  | ~559 examples |

## Using This Dataset

Once approved, load datasets with:

```python
from datasets import load_dataset

# Load combined dataset
dataset = load_dataset(
    "intertwine-ai/security-verifiers-e2",
    split="train",
    token="hf_your_token_here"  # or set HF_TOKEN env var
)

# Load specific splits
k8s_data = load_dataset("intertwine-ai/security-verifiers-e2", split="k8s", token="hf_...")
tf_data = load_dataset("intertwine-ai/security-verifiers-e2", split="terraform", token="hf_...")
```

### With Security Verifiers Environment

```python
import verifiers as vf
import os

# Set environment variables
os.environ["HF_TOKEN"] = "hf_your_token_here"
os.environ["E2_HF_REPO"] = "intertwine-ai/security-verifiers-e2"

# Load environment (auto-detects Hub dataset)
env = vf.load_environment("sv-env-config-verification", dataset_source="hub")

# Or with evaluation script
# make eval-e2 MODELS="gpt-5-mini" N=50 INCLUDE_TOOLS=true
```

## Dataset Construction

- **Script:** `scripts/data/build_e2_k8s_tf.py`
- **Emitted files:**
  - `k8s-labeled-v1.jsonl` — YAML with `info.violations[]` from tools
  - `terraform-labeled-v1.jsonl` — HCL with `info.violations[]`
  - `tools-versions.json` — Exact tool versions used for scanning
  - `sampling-e2-v1.json` — Sampling metadata (scan stats, tool versions)

### Schema

One JSONL item per file:

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

## Quality Controls

- **Tool versions pinned:** All scanners (OPA, KubeLinter, Semgrep) versions recorded in `tools-versions.json`
- **Reproducible:** Same tools + policies yield same violations
- **Deduplication:** Content-based SHA-256 to prevent duplicate configs
- **Oracle:** OPA/Rego policies act as primary ground truth
- **Validation:** Patch-verified subset ensures minimal patches remove violations

## Tool Configuration

This dataset uses:

- **OPA/Rego policies:** Custom security policies for K8s and Terraform
- **KubeLinter:** Kubernetes best practices and security checks
- **Semgrep:** Pattern-based security scanning (k8s and terraform rules)

All tool versions are pinned and recorded in the dataset metadata.

## Public Metadata Repository

**Browse dataset information without access:**

- <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata>

The public metadata repo includes:

- Sampling metadata showing how datasets were constructed
- Model cards explaining the tool configuration and dataset composition
- Instructions for requesting access

## License

This dataset is licensed under the **Security Verifiers Dataset Evaluation License (EVAL-ONLY)**.

See: [DATASET_EVAL_ONLY_LICENSE.md](https://github.com/intertwine/security-verifiers/blob/main/docs/DATASET_EVAL_ONLY_LICENSE.md)

**Key restrictions:**

- ✅ Evaluation of pre-trained models
- ✅ Reporting aggregate metrics
- ❌ Training or fine-tuning models
- ❌ Including in pre-training data
- ❌ Redistribution

## Citation

When using this dataset, please cite:

```bibtex
@software{security_verifiers_2025,
  title = {Security Verifiers: Open RL Environments for AI Safety and Security},
  author = {Intertwine},
  year = {2025},
  url = {https://github.com/intertwine/security-verifiers}
}
```

## Contact & Support

- **GitHub Issues:** <https://github.com/intertwine/security-verifiers/issues>
- **Repository:** <https://github.com/intertwine/security-verifiers>

For access requests or questions about this dataset, please use GitHub issues or contact the repository maintainers.
