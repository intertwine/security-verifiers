# Datasets Guide

Security Verifiers uses a multi-tier dataset loading system that supports local files, HuggingFace Hub, and synthetic fallbacks.

## Dataset Access

### Gated Datasets

E1 and E2 datasets are hosted on HuggingFace with **gated access** to prevent training contamination:

- **intertwine-ai/security-verifiers-e1-private**: E1 network logs dataset
- **intertwine-ai/security-verifiers-e2-private**: E2 configuration verification dataset

To access:
1. Request access on the HuggingFace dataset page
2. Set `HF_TOKEN` in your environment
3. Datasets load automatically when running evaluations

### Public Mini Sets (Committed)

Small public mini sets are committed to the repo for quick baselines:

- `datasets/public_mini/e1.jsonl` (E1, 100 items)
- `datasets/public_mini/e2.jsonl` (E2, 100 items)

Regenerate with:
```bash
make data-public-mini
```

Use them in evals:
```bash
make eval-e1 MODELS="gpt-5-mini" N=100 DATASET="datasets/public_mini/e1.jsonl"
make eval-e2 MODELS="gpt-5-mini" N=100 DATASET="datasets/public_mini/e2.jsonl"
```

### Dataset Loading Modes

All environments support the `dataset_source` parameter:

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` (default) | Try local → hub → synthetic | Standard usage |
| `local` | Require local JSONL files | Offline/custom datasets |
| `hub` | Load from HuggingFace | Production evaluations |
| `synthetic` | Use test fixtures | Quick testing |

```python
import verifiers as vf

# Auto mode (recommended)
env = vf.load_environment("sv-env-network-logs")

# Explicit hub loading
env = vf.load_environment("sv-env-network-logs", dataset_source="hub")

# Synthetic for testing
env = vf.load_environment("sv-env-network-logs", dataset_source="synthetic")
```

## Building Your Own Datasets

### E1: Network Logs

```bash
# Build full IoT-23 dataset
make data-e1

# Build OOD test sets
make data-e1-ood
```

Datasets are written to `environments/sv-env-network-logs/data/`:
- `iot23-train-dev-test-v1.jsonl` (1800 examples)
- `cic-ids-2017-ood-v1.jsonl` (600 examples)
- `unsw-nb15-ood-v1.jsonl` (600 examples)

### E2: Configuration Verification

```bash
# Clone source repositories
make clone-e2-sources

# Build from cloned sources
make data-e2-local
```

Datasets are written to `environments/sv-env-config-verification/data/`:
- `k8s-labeled-v1.jsonl` (Kubernetes configs)
- `terraform-labeled-v1.jsonl` (Terraform configs)

## Pushing to Your Own HuggingFace Repo

If you want to host datasets on your own HF organization:

```bash
# Configure your HF repo
export HF_TOKEN=hf_your_token_here
export E1_HF_REPO=your-org/security-verifiers-e1
export E2_HF_REPO=your-org/security-verifiers-e2

# Validate datasets
make validate-data

# Push to HuggingFace
make hf-e1p-push-canonical HF_ORG=your-org
make hf-e2p-push-canonical HF_ORG=your-org
```

See [user-dataset-guide.md](user-dataset-guide.md) for detailed instructions.

## Dataset Schema

### E1 Schema

```json
{
  "question": "NetFlow log entry to classify...",
  "answer": "Malicious|Benign|Abstain",
  "metadata": {
    "source": "iot23",
    "flow_id": "..."
  }
}
```

### E2 Schema

```json
{
  "question": "Configuration file content...",
  "answer": "{\"violations\": [...], \"severity\": \"...\"}",
  "metadata": {
    "file_type": "kubernetes|terraform",
    "expected_tools": ["kubelinter", "opa"]
  }
}
```

## Dataset License

All Security Verifiers datasets are licensed for **evaluation only**:

- **Permitted**: Evaluation, benchmarking, research analysis
- **Not Permitted**: Model training, fine-tuning, redistribution

This prevents test set contamination and maintains benchmark integrity.

## Troubleshooting

### "Gated dataset requires access"

1. Visit the HuggingFace dataset page
2. Click "Request access"
3. Wait for approval
4. Set `HF_TOKEN` and retry

### "Dataset not found"

```bash
# Build datasets locally
make data-e1
make clone-e2-sources && make data-e2-local
```

### "Invalid schema"

```bash
# Validate your datasets
make validate-data
```
