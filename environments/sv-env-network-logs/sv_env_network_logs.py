"""sv_env_network_logs: Network log anomaly detection environment.

This module implements PRD Environment #1. The model receives a textual
representation of a network flow and must return a JSON object of the form:

```
{"label": "Benign|Malicious|Abstain", "confidence": 0.0..1.0, "rationale": "str"}
```

Rewards combine classification accuracy, strict schema adherence, calibration,
and asymmetric cost penalties for missed attacks.
"""

from __future__ import annotations

from pathlib import Path
import sys

import verifiers as vf
from datasets import Dataset, load_dataset

# Allow importing shared components when running from source
sys.path.append(str(Path(__file__).resolve().parents[2]))
from sv_shared import (  # type: ignore  # pylint: disable=wrong-import-position
    JsonClassificationParser,
    RolloutLogger,
    reward_accuracy,
    reward_calibration,
    reward_asymmetric_cost,
)


class NetworkLogParser(JsonClassificationParser):
    """Parser for network log classification outputs."""

    def __init__(self) -> None:
        super().__init__(allowed_labels=["Benign", "Malicious", "Abstain"])


def transform_dataset(raw_dataset: Dataset, max_examples: int | None) -> Dataset:
    """Transform raw dataset to SingleTurnEnv format."""

    def transform_example(example):
        # The IoT-23 dataset has many columns. We'll create a simple
        # string representation of the most relevant ones for the prompt.
        # This can be refined to be more descriptive.
        prompt_text = (
            f"Log Entry: id.orig_h={example.get('id.orig_h')}, "
            f"id.orig_p={example.get('id.orig_p')}, "
            f"id.resp_h={example.get('id.resp_h')}, "
            f"id.resp_p={example.get('id.resp_p')}, "
            f"proto={example.get('proto')}, "
            f"service={example.get('service')}, "
            f"detailed-label={example.get('detailed-label')}"
        )

        # The 'label' column is 'Malicious' or 'Benign'
        return {
            "question": prompt_text,
            "answer": example.get("label", "Benign"),
        }

    transformed = raw_dataset.map(transform_example)

    if max_examples and len(transformed) > max_examples:
        transformed = transformed.select(range(max_examples))

    return transformed


def load_environment(
    dataset_name: str = "19kmunz/iot-23-preprocessed-minimumcolumns",
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
) -> vf.SingleTurnEnv:
    """Load the Network Logs Anomaly Detection environment.

    This environment is a single-turn classification task where the model
    inspects a network log entry and determines whether it is malicious or benign.

    Args:
        dataset_name: HuggingFace dataset name for network logs.
        max_examples: Maximum number of examples to use from the dataset.
        logger: Optional rollout logger for instrumenting environment metadata.

    Returns:
        A Verifiers SingleTurnEnv configured for the task.
    """
    try:
        # The `load_dataset` function with a `split` argument returns a `Dataset` object.
        # We assert the type to satisfy the linter and ensure correctness.
        dataset = load_dataset(dataset_name, split="train")
        assert isinstance(dataset, Dataset), "Loaded dataset is not of type Dataset"
        dataset = transform_dataset(dataset, max_examples)
    except (
        FileNotFoundError,
        ConnectionError,
        ValueError,
        ImportError,
        AssertionError,
    ) as e:
        print(f"Failed to load dataset '{dataset_name}': {e}")
        print("Falling back to a synthetic dataset.")

        def _create_synthetic_dataset():
            """Create a synthetic dataset for testing purposes."""
            examples = []

            # Generate 10 synthetic network log entries with various patterns
            # pylint: disable=line-too-long
            log_patterns = [
                # Benign examples
                {
                    "question": (
                        "2024-01-15 10:23:45 SRC=192.168.1.105 DST=192.168.1.1 PROTO=HTTPS PORT=443 STATUS=OK"
                    ),
                    "answer": "Benign",
                },
                {
                    "question": (
                        "2024-01-15 10:24:12 SRC=10.0.0.15 DST=10.0.0.1 PROTO=DNS PORT=53 QUERY=google.com STATUS=OK"
                    ),
                    "answer": "Benign",
                },
                {
                    "question": (
                        "2024-01-15 10:25:33 SRC=172.16.0.100 DST=172.16.0.10 PROTO=SSH PORT=22 STATUS=AUTH_SUCCESS"
                    ),
                    "answer": "Benign",
                },
                # Malicious examples
                {
                    "question": (
                        "2024-01-15 10:26:01 SRC=192.168.1.105 DST=192.168.1.1 "
                        "PROTO=SSH PORT=22 STATUS=AUTH_FAILED ATTEMPTS=50"
                    ),
                    "answer": "Malicious",
                },
                {
                    "question": (
                        "2024-01-15 10:27:15 SRC=10.0.0.99 DST=185.220.101.45 PROTO=TOR PORT=9001 BYTES=50000"
                    ),
                    "answer": "Malicious",
                },
                {
                    "question": (
                        "2024-01-15 10:28:42 SRC=172.16.0.200 DST=MULTIPLE PROTO=SCAN PORTS=1-65535 STATUS=SYN_SCAN"
                    ),
                    "answer": "Malicious",
                },
                # More examples
                {
                    "question": (
                        "2024-01-15 10:29:03 SRC=192.168.1.50 DST=8.8.8.8 PROTO=ICMP TYPE=ECHO_REQUEST STATUS=OK"
                    ),
                    "answer": "Benign",
                },
                {
                    "question": (
                        "2024-01-15 10:30:21 SRC=10.0.0.77 DST=198.51.100.23 PROTO=HTTPS PORT=443 CERT=SELF_SIGNED"
                    ),
                    "answer": "Malicious",
                },
                {
                    "question": (
                        "2024-01-15 10:31:55 SRC=172.16.0.150 DST=172.16.0.1 PROTO=HTTP PORT=80 STATUS=OK METHOD=GET"
                    ),
                    "answer": "Benign",
                },
                {
                    "question": (
                        "2024-01-15 10:32:18 SRC=192.168.1.200 DST=91.92.109.43 PROTO=UDP PORT=4444 PATTERN=C2_BEACON"
                    ),
                    "answer": "Malicious",
                },
            ]
            # pylint: enable=line-too-long

            examples.extend(log_patterns)
            return Dataset.from_list(examples)

        dataset = _create_synthetic_dataset()
        dataset_name = f"synthetic::{dataset_name}"

    parser = NetworkLogParser()

    rubric = vf.Rubric(
        funcs=[
            reward_accuracy,
            parser.get_format_reward_func(),
            reward_calibration,
            reward_asymmetric_cost,
        ],
        weights=[1.0, 0.1, 0.2, 0.5],
    )

    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name="sv-env-network-logs",
            dataset_name=dataset_name,
            total_examples=len(dataset) if dataset is not None else None,
            metadata={"max_examples": max_examples},
        )

    return vf.SingleTurnEnv(
        name="sv-env-network-logs",
        description="Classify network logs as 'Malicious', 'Benign', or 'Abstain'.",
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=(
            "You are a network security analyst. Analyze the provided network log entry and "
            "respond with a JSON object: {\"label\": 'Benign|Malicious|Abstain', "
            '"confidence": 0.0-1.0, "rationale": optional}.'
        ),
    )
