# Plan for `sv-env-network-logs` Implementation

This document outlines the plan to implement the `sv-env-network-logs` verifier environment, aligning it with the goals specified in `docs/prd-verifiers.md`.

## 1. Codebase Cleanup

The existing files `src/sv_env_network_logs/interfaces.py` and `src/sv_env_network_logs/skeletons.py` are placeholders and their logic is not aligned with the PRD's goal of training an LLM for classification. They will be removed.

- [x] Delete `environments/sv-env-network-logs/src/sv_env_network_logs/interfaces.py`
- [x] Delete `environments/sv-env-network-logs/src/sv_env_network_logs/skeletons.py`

## 2. Create the Verifier Environment

A new file, `environments/sv-env-network-logs/src/sv_env_network_logs/main.py`, has been created. This file contains the core logic for the environment, following the simple implementation outlined in the PRD.

### `main.py` Implementation Details

- **`load_environment()` function**: The main entry point for the `verifiers` framework, which instantiates and returns the `SingleTurnEnv`.
- **Dataset Loading**:
  - Uses `datasets.load_dataset` to load `"19kmunz/iot-23-preprocessed-minimumcolumns"`.
  - A transformation function maps the dataset's columns to the `prompt` and `answer` format required by `SingleTurnEnv`.
- **Reward Function (`Rubric`)**:
  - A simple `reward_label_match` function performs a case-insensitive string comparison between the model's completion and the ground-truth answer.
  - This function is wrapped in a `verifiers.Rubric`.
- **Environment Instantiation**:
  - A `verifiers.SingleTurnEnv` is created, passing the dataset, rubric, and a system prompt that instructs the LLM to output only 'Malicious' or 'Benign'.

## 3. Update Project Configuration

The `pyproject.toml` file has been updated to correctly point to the new `load_environment` function in `main.py` as the entry point for this verifier environment.

- [x] Verify and update `environments/sv-env-network-logs/pyproject.toml` entry point.

## 4. Update README

The `README.md` has been updated to reflect the new implementation, removing references to the old `skeletons` and `interfaces` and explaining how the new `main.py` works.

- [x] Update `environments/sv-env-network-logs/README.md`.

## 5. Validate with Tests

The environment has been validated with a new test suite that mocks external dependencies.

- [x] Delete outdated test files.
- [x] Create new tests in `tests/test_main.py`.
- [x] Run tests and ensure they pass.
