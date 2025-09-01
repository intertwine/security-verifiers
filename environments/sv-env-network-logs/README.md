# sv-env-network-logs

Security Verifiers RL environment for **Anomaly Detection in Network Logs** - a `SingleTurnEnv` implementation where models classify network log entries as malicious or benign.

## Overview

This environment implements the task of single-turn classification where a model inspects a network log entry and determines whether it is malicious or benign. The environment provides log data from the IoT-23 dataset as the prompt, and the agent must output a label indicating if the log is an anomaly (attack) or normal.

## Task Description

- **Input**: A string representation of a network log entry.
- **Output**: A classification label: "Malicious" or "Benign".
- **Environment Type**: `verifiers.SingleTurnEnv` (one prompt → one response).
- **Reward**: Multi-criteria scoring with classification accuracy (weight 1.0) and format quality (weight 0.2).

## Example

```text
Prompt: "Log Entry: id.orig_h=None, id.orig_p=None, id.resp_h=None, id.resp_p=8081, proto=tcp, service=None, detailed-label=None"
Expected Output: "Malicious"
```

## Performance

Recent evaluation results with gpt-4.1-mini on 100 examples:

- **Overall Score**: 80.3% (weighted combination of accuracy and format)
- **Classification Accuracy**: 60.3% (correct malicious/benign predictions)
- **Format Quality**: 100% (models consistently respond with single classification words)

The environment successfully encourages both accurate classification and proper response formatting.

## Implementation

The environment is implemented in `sv_env_network_logs.py` and is loaded via the `load_environment` function.

It uses the Verifiers framework with:

- **Dataset**: `19kmunz/iot-23-preprocessed-minimumcolumns` from Hugging Face. A synthetic dataset with 10 examples is used as a fallback if the download fails.
- **Parser**: `NetworkLogParser` extracts classification labels from model responses and provides format validation.
- **Rubric**: Multi-criteria evaluation with two reward functions:
  - `reward_correct_classification`: Binary reward (1.0 for correct classification, 0.0 otherwise)
  - `format_reward`: Rewards proper response format (1.0 for exact "Malicious"/"Benign", 0.5 for containing the word, 0.0 otherwise)
- **System Prompt**: Guides the model to act as a network security analyst and respond only with the classification label.

## Structure

- `sv_env_network_logs.py`: Contains the environment implementation with:
  - `NetworkLogParser`: Extracts and validates classification responses
  - `reward_correct_classification`: Evaluates classification accuracy
  - `load_environment`: Entry point that creates the SingleTurnEnv with multi-criteria rubric
- `sv_env_network_logs_test.py`: Test suite for the environment and reward functions
- `pyproject.toml`: Project configuration with 120-character line length and all dependencies

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
vf-eval sv-env-network-logs --model gpt-4.1-mini --num-examples 3
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
  set -a && source .env && set +a && vf-eval sv-env-network-logs --model gpt-4.1-mini --num-examples 3
  ```

- **Hugging Face Authentication**: Loading the `19kmunz/iot-23-preprocessed-minimumcolumns` dataset requires authentication. If you see a `401 Unauthorized` error, you need to log in to Hugging Face or set the `HF_TOKEN` environment variable:

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
