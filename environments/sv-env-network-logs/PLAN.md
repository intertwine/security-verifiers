# Plan for `sv-env-network-logs` Implementation

This document outlines the plan to implement the `sv-env-network-logs` verifier environment, aligning it with the goals specified in `docs/prd-verifiers.md`.

## 1. Codebase Cleanup

The existing files `src/sv_env_network_logs/interfaces.py` and `src/sv_env_network_logs/skeletons.py` are placeholders and their logic is not aligned with the PRD's goal of training an LLM for classification. They will be removed.

- [ ] Delete `environments/sv-env-network-logs/src/sv_env_network_logs/interfaces.py`
- [ ] Delete `environments/sv-env-network-logs/src/sv_env_network_logs/skeletons.py`

## 2. Create the Verifier Environment

A new file, `environments/sv-env-network-logs/src/sv_env_network_logs/main.py`, will be created. This file will contain the core logic for the environment, following the simple implementation outlined in the PRD.

### `main.py` Implementation Details

- **`load_environment()` function**: This will be the main entry point for the `verifiers` framework. It will instantiate and return the `SingleTurnEnv`.
- **Dataset Loading**:
  - It will use `datasets.load_dataset` to load `"19kmunz/iot-23-preprocessed-minimumcolumns"`.
  - A transformation function will be applied to map the dataset's columns to the `prompt` and `answer` format required by `SingleTurnEnv`.
- **Reward Function (`Rubric`)**:
  - A simple `reward_label_match` function will be defined. It will perform a case-insensitive string comparison between the model's completion and the ground-truth answer.
  - This function will be wrapped in a `verifiers.Rubric`.
- **Environment Instantiation**:
  - A `verifiers.SingleTurnEnv` will be created, passing the dataset, rubric, and a system prompt that instructs the LLM to output only 'Malicious' or 'Benign'.

## 3. Update Project Configuration

The `pyproject.toml` file will be checked to ensure it correctly points to the new `load_environment` function in `main.py` as the entry point for this verifier environment.

- [ ] Verify and update `environments/sv-env-network-logs/pyproject.toml` entry point.

## 4. Update README

The `README.md` will be updated to reflect the new implementation, removing references to the old `skeletons` and `interfaces` and explaining how the new `main.py` works.

- [ ] Update `environments/sv-env-network-logs/README.md`.
