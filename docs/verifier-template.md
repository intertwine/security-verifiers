# Verifier and Environment Implementation Template

This guide shows how to add a new environment package that uses the `verifiers` library for reinforcement learning.

## Scope

- **Environment**: A Python class that wraps a `verifiers` environment (e.g., `vf.SingleTurnEnv`) and prepares a dataset for it.
- **Verifier**: A custom class that implements a specific scoring logic. It can be used within the `verifiers` framework or as a standalone component.

## Where to Add Code

1. **Create a new environment package**: Copy an existing environment directory (e.g., `environments/sv-env-network-logs`) to `environments/sv-env-<your-name>`.
2. **Define interfaces**: In `src/sv_env_<your-name>/interfaces.py`, define the `Protocol` for your verifier and environment.
3. **Implement the verifier**: In `src/sv_env_<your-name>/verifier.py`, create a verifier class that implements the scoring logic.
4. **Implement the environment**: In `src/sv_env_<your-name>/environment.py`, create the main environment class that loads data and configures the `verifiers` environment.

## Add Dependencies

- Edit `environments/sv-env-<your-name>/pyproject.toml` and add any necessary dependencies, including the `verifiers` library.

```toml
dependencies = [
  "verifiers>=0.1.0",
  "datasets",
  # other dependencies
]
```

- Install the new package from the repository root:

```bash
uv pip install -e environments/sv-env-<your-name>
```

## Example: `SingleTurnEnv` for Classification

This example shows how to build an environment for a single-turn classification task, based on `sv-env-network-logs`.

### 1. Define the Verifier Interface (`interfaces.py`)

Create a protocol for your verifier to ensure a consistent API.

```python
from __future__ import annotations
from typing import Any, Mapping, Protocol

class MyVerifier(Protocol):
    """Interface for custom verifier."""
    def score(self, input_text: str, ground_truth: str) -> float:
        ...

    def details(self) -> Mapping[str, Any]:
        ...
```

### 2. Implement the Verifier Logic (`verifier.py`)

This class contains the actual scoring logic.

```python
from .interfaces import MyVerifier as MyVerifierProtocol

class MyVerifierImpl(MyVerifierProtocol):
    """Implements scoring logic for the classification task."""
    def __init__(self):
        self._last_details = {}

    def score(self, input_text: str, ground_truth: str) -> float:
        # In a real scenario, you would classify the input_text
        # and compare it to the ground_truth.
        predicted_label = self.classify(input_text)
        is_correct = predicted_label.lower() == ground_truth.lower()
        self._last_details = {
            'predicted': predicted_label,
            'ground_truth': ground_truth,
            'is_correct': is_correct
        }
        return 1.0 if is_correct else 0.0

    def classify(self, input_text: str) -> str:
        # Dummy classification logic
        if "attack" in input_text.lower():
            return "Malicious"
        return "Benign"

    def details(self) -> Mapping[str, Any]:
        return self._last_details
```

### 3. Implement the Environment (`environment.py`)

This class ties everything together, preparing the dataset and configuring the `verifiers` `SingleTurnEnv`.

```python
import verifiers as vf
from datasets import Dataset, load_dataset
from .verifier import MyVerifierImpl

class MyEnvironment:
    """Wraps the verifiers SingleTurnEnv for a classification task."""

    def __init__(self, dataset_name: str, max_examples: int = 100):
        self._dataset = load_dataset(dataset_name, split='train').select(range(max_examples))
        self._env = self._create_verifiers_env()

    def get_verifiers_env(self) -> vf.SingleTurnEnv:
        return self._env

    def _create_verifiers_env(self) -> vf.SingleTurnEnv:
        """Creates and configures the SingleTurnEnv."""
        # Define a reward function for the rubric
        def reward_label_match(prompt: str, completion: str, answer: str, **kwargs) -> float:
            predicted = completion.strip().lower()
            actual = answer.strip().lower()
            return 1.0 if predicted == actual else 0.0

        rubric = vf.Rubric(
            funcs=[reward_label_match],
            weights=[1.0],
        )

        # The dataset must have 'prompt' and 'answer' columns
        transformed_dataset = self._dataset.map(
            lambda example: {'prompt': example['text'], 'answer': example['label_text']}
        )

        return vf.SingleTurnEnv(
            dataset=transformed_dataset,
            rubric=rubric,
            system_prompt="Classify the following text as 'Malicious' or 'Benign'."
        )
```

## Testing

- Create tests under `environments/<env>/tests/`.
- Test the verifier's scoring logic and the environment's data loading and configuration.

```python
from sv_env_network_logs.verifier import NetworkLogsVerifier

def test_verifier_malicious_classification():
    v = NetworkLogsVerifier()
    score = v.score("log containing port scan", ground_truth="Malicious")
    assert score == 1.0
    details = v.details()
    assert details['predicted'] == 'Malicious'

from sv_env_network_logs.environment import NetworkLogsEnvironment

def test_environment_creation():
    # Using a synthetic dataset for testing is recommended
    env_wrapper = NetworkLogsEnvironment(dataset_name="<your-dummy-dataset>")
    vf_env = env_wrapper.get_verifiers_env()
    assert vf_env is not None
    assert len(vf_env.dataset) > 0
```

## General Guidance

- Use the `verifiers` library (`import verifiers as vf`) as the core framework for RL environments.
- Ensure your dataset is transformed to have `prompt` and `answer` columns for `SingleTurnEnv`.
- Define clear reward functions within a `vf.Rubric`.
- Use type hints and run `ruff` and `pytest` before submitting a PR.
