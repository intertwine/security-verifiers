# Configuration Auditing Environment

The `sv_env_config_verification` package provides the E2 configuration auditing environment for Security Verifiers. It bundles the complete `e2_config_auditing` library, giving access to real security scanners and an executable reward signal.

**Environment Type**: `ToolEnv` - Multi-turn environment with tool access for configuration analysis.

## Module Layout

```text
sv_env_config_verification/
  __init__.py                 # environment entry points
  e2_config_auditing/
    adapters/                 # KubeLinter, Semgrep, OPA wrappers
    baselines/                # example tooling baselines
    ci/                       # version pinning and CI configuration
    dataset/                  # fixtures and oracle labels
    docker/                   # containerization support
    env.py                    # environment configuration
    mapping.py                # finding normalization
    oracle.py                 # ground truth generation
    patching.py               # patch application logic
    reward.py                 # reward computation
    schema.py                 # input/output validation
    tests/                    # unit tests
```

Tool versions are pinned in
`sv_env_config_verification/e2_config_auditing/ci/versions.txt` to ensure
reproducible results.

## Input / Output

**Input:** Kubernetes YAML or Terraform HCL as plain text.

**Model output schema:**

```json
{
  "violations": [{ "id": "string", "severity": "low|med|high" }],
  "patch": "string",
  "confidence": 0.0
}
```

## Rewards and Tools

`sv_env_config_verification.reward_config_auditing` combines
severity‑weighted F1 with credit for violations removed after applying a patch.
The environment exposes three deterministic tool functions:

- `run_kubelinter` – Kubernetes static analysis with file and line metadata (finds issues like containers running as root, latest tags, missing resource limits)
- `run_semgrep` – Terraform or generic pattern scanning for security vulnerabilities
- `run_opa` – Policy-based security analysis for Kubernetes configurations using Open Policy Agent (checks namespace usage, resource limits, security policies)

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

### API Keys Configuration

This environment may require API keys depending on your configuration. If you encounter authentication errors:

1. **Copy the example environment file** (from the repository root):

   ```bash
   cp ../../../.env.example ../../../.env
   ```

2. **Add your API keys to the `.env` file**:

   ```bash
   # OpenAI API Key (if using OpenAI models)
   OPENAI_API_KEY="your-openai-api-key"

   # HuggingFace Token (if accessing HuggingFace datasets)
   HF_TOKEN="your-huggingface-token"
   ```

3. **Load environment variables before running commands**:

   ```bash
   # Load environment variables from .env file
   set -a && source .env && set +a
   ```

**Security Note**: The `.env` file is already included in `.gitignore` to prevent accidentally committing your API keys. Never commit actual API keys to version control.

## Basic Usage

### Reproducible evaluations (Multi-turn with tool calling)

Run the E2 environment across one or more models with multi-turn tool calling support:

```bash
# Default: Multi-turn evaluation with tools enabled
make eval-e2 MODELS="gpt-4o-mini" N=2 INCLUDE_TOOLS=true

# Without tools (baseline)
make eval-e2 MODELS="gpt-4o-mini" N=2 INCLUDE_TOOLS=false

# Direct script usage with optional parameters
python scripts/eval_config_verification.py \
    --models gpt-4o-mini \
    --num-examples 2 \
    --include-tools true \
    --max-turns 5 \
    --temperature 0.5 \
    --max-tokens 1000
```

The evaluation script:

- Supports multi-turn conversations with up to 5 turns (configurable)
- Enables models to call kube-linter, semgrep, and OPA tools when `INCLUDE_TOOLS=true`
- Creates temporary files for tools to analyze
- Handles tool responses and allows follow-up tool calls
- Tracks all tool interactions in the results

For single-turn evaluation without tool calling (legacy), use:

```bash
python scripts/eval_config_verification_singleturn.py --models gpt-4o-mini --num-examples 2
```

Artifacts are written to:

```text
outputs/
  evals/
    sv-env-config-verification--{model}/{run_id}/
      metadata.json
      results.jsonl
```

- metadata.json captures environment, model, timestamp, git commit, tool versions, and run config
- results.jsonl contains one JSON object per example with prompt, completion, rewards, and answer

```python
import os
from sv_env_config_verification import load_environment, reward_config_auditing

# Load environment variables from .env file (if running in Python script)
# os.environ['OPENAI_API_KEY'] = 'your-openai-api-key'  # Alternative manual setup

env = load_environment(max_examples=1)
sample = env.dataset[0]
completion = '{"violations": [], "patch": "", "confidence": 0.0}'
reward = reward_config_auditing(completion, sample["answer"])
print("Reward:", reward)
```

## Fine‑Tuning Examples

### Supervised Fine‑Tuning

```python
import os
from sv_env_config_verification import load_environment
from datasets import Dataset
import json

# Load environment variables from .env file (if running in Python script)
# os.environ['OPENAI_API_KEY'] = 'your-openai-api-key'  # Alternative manual setup

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
import os
from sv_env_config_verification import load_environment, reward_config_auditing

# Load environment variables from .env file (if running in Python script)
# os.environ['OPENAI_API_KEY'] = 'your-openai-api-key'  # Alternative manual setup

env = load_environment()
for sample in env.dataset:
    completion = model.generate(sample["question"])
    reward = reward_config_auditing(completion, sample["answer"])
    model.update(completion, reward)  # pseudo-code for RL update
```

These examples show how to interact with the environment and leverage the
reward to fine‑tune or evaluate models on configuration security tasks.

## Recent Improvements (2025-09-21)

- **Multi-turn evaluation is now default**: Replaced single-turn eval with multi-turn tool-calling evaluation as the default for `make eval-e2`
- **Full tool integration**: Models can now call kube-linter, semgrep, and OPA tools during evaluation, achieving significantly better results (0.93 vs 0.62 reward)
- **Simplified model parameter handling**: Made temperature and max_tokens optional - only passed to models when explicitly provided, letting models use their defaults
- **Enhanced system prompt**: Added specific violation examples, tool descriptions, and OPA policy violations for better model performance
- **Verified all three tools**: Confirmed kube-linter, semgrep, and OPA are all functional and models successfully use them

## Known Issues

- **Parser/rubric mismatch warning**: The ToolEnv shows a warning about parser and rubric parser being different - this is a known limitation and can be safely ignored
