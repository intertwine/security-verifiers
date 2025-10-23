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

# Allow importing shared components when running from source
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Initialize Weave before importing verifiers for automatic tracing
from sv_shared import weave_init  # type: ignore  # noqa: F401, E402

import verifiers as vf
from datasets import Dataset

from sv_shared import (  # type: ignore  # pylint: disable=wrong-import-position
    DatasetSource,
    JsonClassificationParser,
    RolloutLogger,
    load_dataset_with_fallback,
    reward_accuracy,
    reward_calibration,
    reward_asymmetric_cost,
)


class NetworkLogParser(JsonClassificationParser):
    """Parser for network log classification outputs."""

    def __init__(self) -> None:
        super().__init__(allowed_labels=["Benign", "Malicious", "Abstain"])


def load_environment(
    dataset_name: str = "iot23-train-dev-test-v1.jsonl",
    dataset_source: DatasetSource = "auto",
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
) -> vf.SingleTurnEnv:
    """Load the Network Logs Anomaly Detection environment.

    This environment is a single-turn classification task where the model
    inspects a network log entry and determines whether it is malicious or benign.

    Args:
        dataset_name: Dataset to load. Available options:
                     - "iot23-train-dev-test-v1.jsonl" (primary, N=1800)
                     - "cic-ids-2017-ood-v1.jsonl" (OOD, N=600)
                     - "unsw-nb15-ood-v1.jsonl" (OOD, N=600)
                     - "synthetic" (for testing without data dependencies)
                     - Or any local .jsonl file path (absolute or relative to env/data/)
        dataset_source: Where to load the dataset from. Options:
                       - "auto" (default): Try local → hub → synthetic
                       - "local": Only load from local JSONL files
                       - "hub": Only load from HuggingFace Hub (requires HF_TOKEN)
                       - "synthetic": Use synthetic test fixtures
        max_examples: Maximum number of examples to use from the dataset.
        logger: Optional rollout logger for instrumenting environment metadata.

    Environment Variables:
        HF_TOKEN: HuggingFace API token (required for Hub datasets)
        E1_HF_REPO: Custom HF repo for E1 datasets (default: intertwine-ai/security-verifiers-e1-private)

    Returns:
        A Verifiers SingleTurnEnv configured for the task.

    Examples:
        # Use auto-loading (local → hub → synthetic fallback)
        env = load_environment()

        # Load from local dataset (requires 'make data-e1')
        env = load_environment(dataset_source="local")

        # Load from HuggingFace Hub (requires HF_TOKEN)
        env = load_environment(dataset_source="hub")

        # Use synthetic dataset for quick testing
        env = load_environment(dataset_source="synthetic")

        # Load from user's own HF repo
        import os
        os.environ["E1_HF_REPO"] = "my-org/my-security-verifiers-e1"
        env = load_environment(dataset_source="hub")
    """
    env_root = Path(__file__).parent

    def _create_synthetic_dataset():
        """Create a synthetic dataset for testing purposes."""
        # Generate 10 synthetic network log entries with various patterns
        # pylint: disable=line-too-long
        log_patterns = [
            # Benign examples
            {
                "question": ("2024-01-15 10:23:45 SRC=192.168.1.105 DST=192.168.1.1 PROTO=HTTPS PORT=443 STATUS=OK"),
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
                "question": ("2024-01-15 10:27:15 SRC=10.0.0.99 DST=185.220.101.45 PROTO=TOR PORT=9001 BYTES=50000"),
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
                "question": ("2024-01-15 10:29:03 SRC=192.168.1.50 DST=8.8.8.8 PROTO=ICMP TYPE=ECHO_REQUEST STATUS=OK"),
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
        return Dataset.from_list(log_patterns)

    # Load dataset using shared multi-tiered loader
    # Field mapping: build scripts use "prompt", environment expects "question"
    dataset, resolved_name = load_dataset_with_fallback(
        dataset_name=dataset_name,
        env_root=env_root,
        dataset_source=dataset_source,
        max_examples=max_examples,
        field_mapping={"prompt": "question"},
        synthetic_generator=_create_synthetic_dataset,
    )
    dataset_name = resolved_name

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
