# sv-env-network-logs

Security Verifiers RL environment for **Anomaly Detection in Network Logs** - a `SingleTurnEnv` implementation where models classify network log entries as malicious or benign.

## Overview

This environment implements the task of single-turn classification where a model inspects a network log entry and determines whether it is malicious or benign. The environment provides log data from the IoT-23 dataset as the prompt, and the agent must output a label indicating if the log is an anomaly (attack) or normal.

## Task Description

- **Input**: A string representation of a network log entry.
- **Output**: A classification label: "Malicious" or "Benign".
- **Environment Type**: `verifiers.SingleTurnEnv` (one prompt → one response).
- **Reward**: Binary reward (1.0 for correct classification, 0.0 otherwise).

## Example

```text
Prompt: "Log Entry: id.orig_h=192.168.1.104, id.orig_p=37356, id.resp_h=192.168.1.1, id.resp_p=80, proto=tcp, service=http, detailed-label=Attack"
Expected Output: "Malicious"
```

## Implementation

The environment is implemented in `src/sv_env_network_logs/main.py` and is loaded via the `load_environment` function.

It uses the Verifiers framework with:

- **Dataset**: `19kmunz/iot-23-preprocessed-minimumcolumns` from Hugging Face. A small synthetic dataset is used as a fallback if the download fails.
- **Rubric**: An exact, case-insensitive match verification against the ground truth labels ("Malicious" or "Benign").
- **Reward Function**: `reward_label_match` provides a reward of 1.0 for a correct classification and 0.0 for an incorrect one.
- **System Prompt**: Guides the model to act as a network security analyst and respond only with the classification label.

## Structure

- `src/sv_env_network_logs/main.py`: Contains the environment implementation, including the `load_environment` entry point.
- `tests/`: Test suite for the environment.
- `pyproject.toml`: Project configuration, including dependencies and the entry point for the `verifiers` framework.

## Local Development Setup

To set up the environment for local development and testing, install it in editable mode with the `dev` dependencies. From the repository root, after creating and activating a virtual environment:

```bash
# Install the package and development dependencies
uv pip install -e 'environments/sv-env-network-logs[dev]'
```

This will install all necessary dependencies for running the environment and its tests, including `verifiers[dev]`.

## Local Development and Testing

To test the environment locally, you can use the `vf-eval` command from the `verifiers` library. This will load the environment and run a few examples using a specified model.

```bash
# Evaluate the environment with a small model
vf-eval sv-env-network-logs --model gpt-4o-mini --num-examples 3
```

**Note on Configuration**:

- **API Keys**: The evaluation requires API keys to be set as environment variables. Create a `.env` file in the project root with:

  ```bash
  OPENAI_API_KEY=your-openai-api-key-here
  HF_TOKEN=your-huggingface-token-here  # Optional, for dataset access
  ```

  Then load the environment variables before running `vf-eval`:

  ```bash
  # Load .env file and run evaluation
  set -a && source .env && set +a && vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3
  ```

- **Hugging Face Authentication**: The `19kmunz/iot-23-preprocessed-minimumcolumns` dataset is private. If you see a `401 Unauthorized` error, you need to log in to Hugging Face or set the `HF_TOKEN` environment variable:

  ```bash
  huggingface-cli login
  ```

- **Model Endpoint**: If you see a `No local endpoint registry found` message, this is expected. The tool will use the default OpenAI endpoint with your API key. For custom endpoints, refer to the Prime Intellect documentation.

## Publishing to the Environments Hub

Once the environment is tested, you can publish it to the Prime Intellect Environments Hub to make it accessible for cloud training and community use.

1. **Login to the Prime CLI**:

   ```bash
   prime login
   ```

2. **Build the environment wheel**:

   ```bash
   # From the environments/sv-env-network-logs directory
   uv pip wheel . -w dist/
   ```

3. **Upload the wheel to the Hub**:

   ```bash
   prime env upload dist/*.whl
   ```

## Cloud Training with Prime RL

After publishing, you can use the environment in a Prime RL training workflow on the Prime Intellect cloud.

In your `prime-rl` orchestrator configuration file (e.g., `orchestrator.toml`), specify the environment ID:

```toml
[environment]
id = "<your-username>/sv-env-network-logs"
```

Then, you can launch the training job using the `rl` command:

```bash
uv run rl \
 --trainer.model.name "Qwen/Qwen-7B" \
 --orchestrator.environment.id "<your-username>/sv-env-network-logs" \
 --trainer.steps 1000
```
