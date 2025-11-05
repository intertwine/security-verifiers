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
  - text-classification
language:
  - en
tags:
  - security
  - network-intrusion-detection
  - iot
  - cybersecurity
  - gated
  - evaluation
pretty_name: Security Verifiers E1 (Private) - Network Log Anomaly Detection
size_categories:
  - 1K<n<10K
---

# E1 — Network Log Anomaly Detection (Private Gated Dataset)

**Owner:** intertwine • **Env:** `sv-env-network-logs` • **Version:** v1

## ⚠️ Gated Access

This repository hosts the **private canonical dataset** for E1 (Network Log Anomaly Detection) used by the `sv-env-network-logs` environment.

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

- **Primary (ID):** IoT-23 (HF: `19kmunz/iot-23-preprocessed` - 819k rows, Zeek-processed)
- **OOD A:** CIC-IDS-2017 (HF: `bvk/CICIDS-2017` - 2.1M rows, benign + 15 attack categories)
- **OOD B:** UNSW-NB15 (HF: `Mireu-Lab/UNSW-NB15` - 82k train, 175k test, labeled)

Rationale: Matches the environment's single-turn, calibrated classification design with abstention and asymmetric costs (FN ≫ FP).

## Dataset Splits

This repository contains the following splits:

| Split      | Description                                  | Size           |
| ---------- | -------------------------------------------- | -------------- |
| `train`    | IoT-23 primary dataset (70/15/15 stratified) | ~1800 examples |
| `cic_ood`  | CIC-IDS-2017 out-of-distribution             | ~600 examples  |
| `unsw_ood` | UNSW-NB15 out-of-distribution                | ~600 examples  |

## Using This Dataset

Once approved, load datasets with:

```python
from datasets import load_dataset

# Load primary dataset
dataset = load_dataset(
    "intertwine-ai/security-verifiers-e1",
    split="train",
    token="hf_your_token_here"  # or set HF_TOKEN env var
)

# Load OOD datasets
cic_ood = load_dataset("intertwine-ai/security-verifiers-e1", split="cic_ood", token="hf_...")
unsw_ood = load_dataset("intertwine-ai/security-verifiers-e1", split="unsw_ood", token="hf_...")
```

### With Security Verifiers Environment

```python
import verifiers as vf
import os

# Set environment variables
os.environ["HF_TOKEN"] = "hf_your_token_here"
os.environ["E1_HF_REPO"] = "intertwine-ai/security-verifiers-e1"

# Load environment (auto-detects Hub dataset)
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")

# Or with evaluation script
# make eval-e1 MODELS="gpt-5-mini" N=100
```

## Dataset Construction

- **Scripts:**
  - `scripts/data/build_e1_iot23.py` (IoT-23 primary dataset)
  - `scripts/data/build_e1_ood.py` (CIC-IDS-2017 & UNSW-NB15 OOD datasets)
- **Prompt format:** concise natural-language summary of key flow features (proto/ports/bytes/duration/flags + device)
  - Example: `Device unknown-device observed tcp 23381→81, duration ?, bytes ?, flags [S]. Decide: Malicious or Benign (you may Abstain if unsure).`
- **Label:** `Malicious` or `Benign` (gold); model may output `Abstain` which is scored by the environment's calibration/abstention reward
- **Sampling seed:** 42; `sampling-iot23-v1.json` and `sampling-e1-ood-v1.json` record counts and seed

## Quality & Leakage Controls

- **Stratified splitting** within scenario:label groups to reduce train/test leakage while maintaining proper split ratios
- **Deduplication:**
  - **IoT-23:** SHA-256 of `(src,dst,sport,dport,proto)` 5-tuple
  - **OOD datasets:** Content-based SHA-256 of `(src,dst,sport,dport,proto,bytes,duration,state,service)` to reduce false duplicates
- **Balance:** ±5% class balance per split to stabilize ECE/FN rate
- **CIC-IDS-2017:** Fetches 10-30x samples to overcome temporal clustering (attacks appear late in dataset); stratified to ensure 50/50 malicious/benign
- **UNSW-NB15:** Fetches 3x samples for deduplication; maintains natural label distribution with 9+ attack categories
- **Borderline tags:** ambiguous low-traffic/partial scans retained to probe abstention

## Public Metadata Repository

**Browse dataset information without access:**

- <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata>

The public metadata repo includes:

- Sampling metadata showing how datasets were constructed
- Model cards explaining the privacy rationale and dataset composition
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
