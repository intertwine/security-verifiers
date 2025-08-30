# sv-env-network-logs

Security Verifiers RL environment for **Anomaly Detection in Network Logs** - a SingleTurnEnv implementation where models classify network log entries as malicious or benign.

## Overview

This environment implements PRD Environment #1: A single-turn classification task where the model inspects a network log entry and determines whether it is malicious or benign. The environment provides log data (e.g., firewall or IoT network logs) as the prompt, and the agent must output a label indicating if the log is an anomaly (attack) or normal.

## Task Description

- **Input**: Network log entries (firewall logs, IoT traffic, etc.)
- **Output**: Classification label ("Malicious" or "Benign")
- **Environment Type**: SingleTurnEnv (one prompt → one response)
- **Reward**: Binary reward based on correct classification

## Example

```
Prompt: "TCP connection from 10.0.0.5:445 to 192.168.1.10:80, flags [S], unusual port scanning pattern detected"
Expected Output: "Malicious"
```

## Implementation

Uses the Verifiers framework with:
- Dataset: IoT-23 network logs or similar labeled datasets
- Rubric: Exact match verification against ground truth labels
- Reward function: 1.0 for correct classification, 0.0 for incorrect

## Why This Task is Useful

- **Cybersecurity**: Anomaly detection is critical for identifying intrusions and malware in real-time
- **RL Training**: Encourages models to recognize subtle patterns in log data that signify attacks
- **Practical Application**: Can enhance IDS (Intrusion Detection System) accuracy by leveraging LLM text understanding

## Structure
- `src/sv_env_network_logs/`: Package sources
- `tests/`: Test suite

## Local install (editable)
From repo root after creating a uv venv:
```bash
uv pip install -e environments/sv-env-network-logs
```
