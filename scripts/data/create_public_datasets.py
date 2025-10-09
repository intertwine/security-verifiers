#!/usr/bin/env python3
# ruff: noqa: E501
"""
Create public dataset repositories on HuggingFace with metadata only.

This script creates PUBLIC dataset repos that contain:
- Sampling metadata (how datasets were built)
- Model cards explaining why datasets are private
- Links to request access

Usage:
    python scripts/data/create_public_datasets.py --hf-org your-username
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed. Run: uv add python-dotenv")
    sys.exit(1)

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("Error: huggingface_hub not installed. Run: uv add huggingface_hub")
    sys.exit(1)


def create_e1_model_card() -> str:
    """Generate model card for E1 public dataset."""
    return """---
license: mit
task_categories:
- text-classification
language:
- en
tags:
- security
- rl
- network-security
- anomaly-detection
- verifiers
- metadata-only
pretty_name: "Security Verifiers E1 - Network Log Anomaly Detection (Metadata)"
size_categories:
- n<1K
---

# 🔒 Security Verifiers E1: Network Log Anomaly Detection (Public Metadata)

> **⚠️ This is a PUBLIC metadata-only repository.** The full datasets are hosted privately to prevent training contamination. See below for access instructions.

## Overview

E1 is a network log anomaly detection environment with calibrated classification and abstention. This repository contains **only the sampling metadata** that describes how the private datasets were constructed.

### Why Private Datasets?

**Training contamination** is a critical concern for benchmark integrity. If datasets leak into public training corpora:
- Models can memorize answers instead of learning to reason
- Evaluation metrics become unreliable
- Research reproducibility suffers
- True capabilities become obscured

By keeping evaluation datasets private with gated access, we:
- ✅ Preserve benchmark validity over time
- ✅ Enable fair model comparisons
- ✅ Maintain research integrity
- ✅ Allow controlled access for legitimate research

### Dataset Composition

The private E1 datasets include:

#### Primary Dataset: IoT-23
- **Samples**: 1,800 network flows (train/dev/test splits)
- **Source**: IoT-23 botnet dataset
- **Features**: Network flow statistics, timestamps, protocols
- **Labels**: Benign vs Malicious with confidence scores
- **Sampling**: Stratified by label and split

#### Out-of-Distribution Datasets
- **CIC-IDS-2017**: 600 samples (different attack patterns)
- **UNSW-NB15**: 600 samples (different network environment)
- **Purpose**: Test generalization and OOD detection

### What's in This Repository?

This public repository contains:

1. **Sampling Metadata** (`sampling-*.json`):
   - Dataset versions and sources
   - Sampling strategies and random seeds
   - Label distributions
   - Split ratios
   - Reproducibility parameters

2. **Tools Versions** (referenced in metadata):
   - Exact versions of all preprocessing tools
   - Dataset library versions
   - Python environment specifications

3. **This README**: Instructions for requesting access

### Reward Components

E1 uses composable reward functions:
- **Accuracy**: Correctness of malicious/benign classification
- **Calibration**: Alignment between confidence and actual accuracy
- **Abstention**: Reward for declining on uncertain examples
- **Asymmetric Costs**: Higher penalty for false negatives (security context)

### Requesting Access

🔑 **To access the full private datasets:**

1. **Open an access request issue**: [Security Verifiers Issues](https://github.com/intertwine/security-verifiers/issues)
2. **Use the title**: "Dataset Access Request: E1"
3. **Include**:
   - Your name and affiliation
   - Research purpose / use case
   - HuggingFace username
   - Commitment to not redistribute or publish the raw data

**Approval criteria:**
- Legitimate research or educational use
- Understanding of contamination concerns
- Agreement to usage terms

We typically respond within 2-3 business days.

### Citation

If you use this environment or metadata in your research:

```bibtex
@misc{security-verifiers-2025,
  title={Open Security Verifiers: Composable RL Environments for AI Safety},
  author={intertwine},
  year={2025},
  url={https://github.com/intertwine/security-verifiers},
  note={E1: Network Log Anomaly Detection}
}
```

### Related Resources

- **GitHub Repository**: [intertwine/security-verifiers](https://github.com/intertwine/security-verifiers)
- **Documentation**: See `EXECUTIVE_SUMMARY.md` and `PRD.md` in the repo
- **Framework**: Built on [Prime Intellect Verifiers](https://github.com/PrimeIntellect-ai/verifiers)
- **Other Environments**: E2 (Config Verification), E3-E6 (in development)

### License

MIT License - See repository for full terms.

### Contact

- **Issues**: [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)
- **Discussions**: [GitHub Discussions](https://github.com/intertwine/security-verifiers/discussions)

---

**Built with ❤️ for the AI safety research community**
"""


def create_e2_model_card() -> str:
    """Generate model card for E2 public dataset."""
    return """---
license: mit
task_categories:
- text-classification
- token-classification
language:
- en
tags:
- security
- rl
- kubernetes
- terraform
- config-verification
- verifiers
- metadata-only
pretty_name: "Security Verifiers E2 - Config Verification (Metadata)"
size_categories:
- n<1K
---

# 🔒 Security Verifiers E2: Security Configuration Verification (Public Metadata)

> **⚠️ This is a PUBLIC metadata-only repository.** The full datasets are hosted privately to prevent training contamination. See below for access instructions.

## Overview

E2 is a tool-grounded configuration auditing environment for Kubernetes and Terraform. This repository contains **only the sampling metadata** that describes how the private datasets were constructed.

### Why Private Datasets?

**Training contamination** is a critical concern for benchmark integrity. If datasets leak into public training corpora:
- Models can memorize answers instead of learning to reason
- Evaluation metrics become unreliable
- Research reproducibility suffers
- True capabilities become obscured

By keeping evaluation datasets private with gated access, we:
- ✅ Preserve benchmark validity over time
- ✅ Enable fair model comparisons
- ✅ Maintain research integrity
- ✅ Allow controlled access for legitimate research

### Dataset Composition

The private E2 datasets include:

#### Kubernetes Configurations
- **Source**: Real-world K8s manifests from popular open-source projects
- **Scans**: KubeLinter, Semgrep, OPA/Rego policies
- **Violations**: Security misconfigurations, best practice violations
- **Severity**: Categorized (high/medium/low) based on tool outputs

#### Terraform Configurations
- **Source**: Infrastructure-as-code from real projects
- **Scans**: Semgrep, OPA/Rego policies, custom rules
- **Violations**: Security risks, compliance issues
- **Severity**: Weighted scoring for reward computation

### What's in This Repository?

This public repository contains:

1. **Sampling Metadata** (`sampling-*.json`):
   - Source repository information
   - File selection criteria
   - Scan configurations
   - Label distributions
   - Reproducibility parameters

2. **Tools Versions** (`tools-versions.json`):
   - KubeLinter version (pinned)
   - Semgrep version (pinned)
   - OPA version (pinned)
   - Ensures reproducible scanning

3. **This README**: Instructions for requesting access

### Reward Components

E2 uses tool-grounded reward functions:
- **Detection Precision/Recall/F1**: Against ground-truth violations
- **Severity Weighting**: Higher reward for catching critical issues
- **Patch Delta**: Reward for proposed fixes that eliminate violations
- **Re-scan Verification**: Patches must pass tool validation

**Multi-turn performance**: Models achieve ~0.93 reward with tool calling vs ~0.62 without tools.

### Requesting Access

🔑 **To access the full private datasets:**

1. **Open an access request issue**: [Security Verifiers Issues](https://github.com/intertwine/security-verifiers/issues)
2. **Use the title**: "Dataset Access Request: E2"
3. **Include**:
   - Your name and affiliation
   - Research purpose / use case
   - HuggingFace username
   - Commitment to not redistribute or publish the raw data

**Approval criteria:**
- Legitimate research or educational use
- Understanding of contamination concerns
- Agreement to usage terms

We typically respond within 2-3 business days.

### Citation

If you use this environment or metadata in your research:

```bibtex
@misc{security-verifiers-2025,
  title={Open Security Verifiers: Composable RL Environments for AI Safety},
  author={intertwine},
  year={2025},
  url={https://github.com/intertwine/security-verifiers},
  note={E2: Security Configuration Verification}
}
```

### Related Resources

- **GitHub Repository**: [intertwine/security-verifiers](https://github.com/intertwine/security-verifiers)
- **Documentation**: See `EXECUTIVE_SUMMARY.md` and `PRD.md` in the repo
- **Framework**: Built on [Prime Intellect Verifiers](https://github.com/PrimeIntellect-ai/verifiers)
- **Other Environments**: E1 (Network Logs), E3-E6 (in development)

### Tools

The following security tools are used for ground-truth generation:
- **KubeLinter**: Kubernetes YAML linting and security checks
- **Semgrep**: Pattern-based static analysis for K8s and Terraform
- **OPA**: Policy-as-code validation with Rego

### License

MIT License - See repository for full terms.

### Contact

- **Issues**: [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)
- **Discussions**: [GitHub Discussions](https://github.com/intertwine/security-verifiers/discussions)

---

**Built with ❤️ for the AI safety research community**
"""


def upload_public_dataset(
    dataset_name: str, hf_org: str, metadata_files: dict[str, Path], card_content: str, token: str
) -> str:
    """Upload public metadata-only dataset to HuggingFace Hub."""
    repo_id = f"{hf_org}/{dataset_name}"
    print(f"\n=== Creating public dataset: {repo_id} ===")

    api = HfApi(token=token)

    # Check if repo exists
    repo_exists = False
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset", token=token)
        print(f"✓ Found existing repo: {repo_id}")
        repo_exists = True
    except Exception:
        # Create as PUBLIC dataset
        try:
            create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=False, exist_ok=True)
            print(f"✓ Created new PUBLIC repo: {repo_id}")
            repo_exists = True
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "don't have the rights" in error_msg.lower():
                username = None
                try:
                    user_info = api.whoami(token=token)
                    username = user_info.get("name")
                except Exception:
                    pass

                print(f"\n❌ ERROR: Permission denied to create repo under '{hf_org}'")
                print(f"   You don't have write access to the '{hf_org}' organization.")
                print("\nOptions:")
                print(f"   1. Ask an admin of '{hf_org}' to add you as a member")
                print("   2. Create the repo manually at: https://huggingface.co/new-dataset")
                if username:
                    print(f"   3. Use your personal account: --hf-org {username}")
                else:
                    print("   3. Use your personal account: --hf-org <your-username>")
                raise RuntimeError(f"Cannot create repo under '{hf_org}' - permission denied")
            else:
                print(f"❌ ERROR: Could not create repo: {e}")
                raise RuntimeError(f"Failed to create repo: {e}")

    if not repo_exists:
        raise RuntimeError(f"Repository {repo_id} does not exist and could not be created")

    # Upload metadata files
    for name, path in metadata_files.items():
        if not path.exists():
            print(f"Warning: Skipping {name} (file not found: {path})")
            continue

        try:
            api.upload_file(
                path_or_fileobj=str(path),
                path_in_repo=path.name,
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
            )
            print(f"  ✓ Uploaded {path.name}")
        except Exception as e:
            print(f"  ✗ Failed to upload {path.name}: {e}")

    # Upload README (model card)
    readme_path = Path("/tmp/README.md")
    readme_path.write_text(card_content)

    try:
        api.upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
        )
        print("  ✓ Uploaded README.md")
    except Exception as e:
        print(f"  ✗ Failed to upload README.md: {e}")

    return f"https://huggingface.co/datasets/{repo_id}"


def main():
    ap = argparse.ArgumentParser(description="Create public metadata-only datasets on HuggingFace")
    ap.add_argument(
        "--hf-org",
        required=True,
        help="HuggingFace organization or username",
    )
    ap.add_argument(
        "--dataset-name-prefix",
        default="security-verifiers",
        help="Base dataset name prefix (default: security-verifiers)",
    )
    ap.add_argument(
        "--e1-only",
        action="store_true",
        help="Only create E1 public dataset",
    )
    ap.add_argument(
        "--e2-only",
        action="store_true",
        help="Only create E2 public dataset",
    )
    args = ap.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Check for HF_TOKEN
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN not found in .env file or environment")
        print("Please add it to .env: HF_TOKEN=your_token_here")
        print("Or set it with: export HF_TOKEN=your_token_here")
        sys.exit(1)

    print(f"\n🌐 Creating PUBLIC metadata-only datasets under '{args.hf_org}'")
    print("These repos will be visible to everyone and contain sampling metadata only.\n")

    try:
        # Create E1 public dataset
        if not args.e2_only:
            e1_data_dir = Path("environments/sv-env-network-logs/data")
            e1_metadata = {
                "sampling-iot23": e1_data_dir / "sampling-iot23-v1.json",
                "sampling-e1-ood": e1_data_dir / "sampling-e1-ood-v1.json",
            }

            # Check if metadata files exist
            missing = [name for name, path in e1_metadata.items() if not path.exists()]
            if missing:
                print(f"\n⚠️  E1 metadata files not found: {', '.join(missing)}")
                print("Run: make data-e1 data-e1-ood")
                if not args.e1_only:
                    print("Skipping E1...\n")
            else:
                e1_url = upload_public_dataset(
                    dataset_name=f"{args.dataset_name_prefix}-e1-metadata",
                    hf_org=args.hf_org,
                    metadata_files=e1_metadata,
                    card_content=create_e1_model_card(),
                    token=token,
                )
                print(f"\n✓ E1 public metadata uploaded: {e1_url}")

        # Create E2 public dataset
        if not args.e1_only:
            e2_data_dir = Path("environments/sv-env-config-verification/data")
            e2_metadata = {
                "sampling-e2": e2_data_dir / "sampling-e2-v1.json",
                "tools-versions": e2_data_dir / "tools-versions.json",
            }

            # Check if metadata files exist
            missing = [name for name, path in e2_metadata.items() if not path.exists()]
            if missing:
                print(f"\n⚠️  E2 metadata files not found: {', '.join(missing)}")
                print("Run: make data-e2-local")
                if not args.e2_only:
                    print("Skipping E2...\n")
            else:
                e2_url = upload_public_dataset(
                    dataset_name=f"{args.dataset_name_prefix}-e2-metadata",
                    hf_org=args.hf_org,
                    metadata_files=e2_metadata,
                    card_content=create_e2_model_card(),
                    token=token,
                )
                print(f"\n✓ E2 public metadata uploaded: {e2_url}")

        print("\n✅ Public metadata-only datasets created successfully!")
        print(f"\nView datasets at: https://huggingface.co/{args.hf_org}")
        print("\n💡 Remember to create the corresponding PRIVATE datasets for the full data.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
