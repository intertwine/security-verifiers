# Configuration Auditing Environment

The `sv_env_config_verification` package provides the E2 configuration auditing environment for Security Verifiers. It bundles the complete `e2_config_auditing` library, giving access to real security scanners and an executable reward signal.

## Module Layout

```
sv_env_config_verification/
  __init__.py                 # environment entry points
  e2_config_auditing/
    adapters/                 # KubeLinter, Semgrep, OPA wrappers
    baselines/                # example tooling baselines
    dataset/                  # fixtures and oracle labels
    mapping.py
    patching.py
    reward.py
    schema.py
```

Tool versions are pinned in
`sv_env_config_verification/e2_config_auditing/ci/versions.txt` to ensure
reproducible results.

## Input / Output

**Input:** Kubernetes YAML or Terraform HCL as plain text.

**Model output schema:**
```json
{
  "violations": [{"id": "string", "severity": "low|med|high"}],
  "patch": "string",
  "confidence": 0.0
}
```

## Rewards and Tools

`sv_env_config_verification.e2_config_auditing.reward.final_reward` combines
severity‑weighted F1 with credit for violations removed after applying a patch.
The environment exposes two deterministic tool functions:

- `run_kubelinter` – Kubernetes static analysis with file and line metadata
- `run_semgrep` – Terraform or generic pattern scanning

## Installation & Testing

```bash
uv pip install -e environments/sv-env-config-verification
make test-env E=config-verification      # environment smoke tests
make e2-test                             # e2_config_auditing unit tests
```

Run the tools‑only baseline:
```bash
make e2-baseline-tools FIXTURE=path/to/file TYPE=k8s|tf
```

## Basic Usage

```python
from sv_env_config_verification import load_environment, reward_config_auditing

env = load_environment(max_examples=1)
sample = env.dataset[0]
completion = '{"violations": [], "patch": "", "confidence": 0.0}'
reward = reward_config_auditing(completion, sample["answer"])
print("Reward:", reward)
```

## Fine‑Tuning Examples

### Supervised Fine‑Tuning

```python
from sv_env_config_verification import load_environment
from datasets import Dataset
import json

env = load_environment()

def format_example(ex):
    return {
        "input_text": ex["question"],
        "target_text": json.dumps({
            "violations": ex["answer"]["oracle"],
            "patch": "",
            "confidence": 1.0,
        })
    }

train_ds: Dataset = env.dataset.map(format_example)
# feed `train_ds` into your favourite HF Trainer for SFT
```

### Reinforcement Learning / Reward Modeling

```python
from sv_env_config_verification import load_environment, reward_config_auditing

env = load_environment()
for sample in env.dataset:
    completion = model.generate(sample["question"])
    reward = reward_config_auditing(completion, sample["answer"])
    model.update(completion, reward)  # pseudo-code for RL update
```

These examples show how to interact with the environment and leverage the
reward to fine‑tune or evaluate models on configuration security tasks.
