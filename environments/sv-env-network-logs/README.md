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

## Local install (editable)

From the repository root after creating and activating a virtual environment:

```bash
uv pip install -e environments/sv-env-network-logs
```

## Usage

You can load and use this environment with the `verifiers` CLI:

```bash
verifiers envs run sv_env_network_logs --model <your-model>
```
