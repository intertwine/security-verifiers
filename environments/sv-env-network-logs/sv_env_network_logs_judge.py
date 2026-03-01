"""sv_env_network_logs_judge: LLM-judge reward variant of Network Log environment.

This module implements a JudgeRubric-based variant of PRD Environment #1 (WP3c).
It reuses the same dataset, prompt, and parsing as the executable-verifier variant,
but replaces the multi-component reward functions (accuracy, calibration, cost) with
a single LLM-judge binary assessment.

Purpose: Compare structured executable rewards vs simpler LLM-judge rewards for RL
training, answering the key WP3c question of whether multi-component reward
decomposition outperforms holistic LLM judgment.

The judge prompt evaluates correctness, calibration, and format in a single pass,
returning a binary yes/no verdict that maps to reward 1.0/0.0.
"""

from __future__ import annotations

from pathlib import Path

try:
    # Try importing from installed package first
    from sv_shared import weave_init  # type: ignore  # noqa: F401
except ImportError:
    # Fall back to local development import
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from sv_shared import weave_init  # type: ignore  # noqa: F401

import logging as _logging
import os

import verifiers as vf
from datasets import Dataset

try:
    from sv_shared import (
        DatasetSource,
        JsonClassificationParser,
        RolloutLogger,
        load_dataset_with_fallback,
    )
except ImportError:
    # Fall back to local development import
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from sv_shared import (  # type: ignore
        DatasetSource,
        JsonClassificationParser,
        RolloutLogger,
        load_dataset_with_fallback,
    )


# ---------------------------------------------------------------------------
# Judge prompt: security-domain-specific evaluation
# ---------------------------------------------------------------------------
# The judge prompt is designed to holistically evaluate the same dimensions
# that the executable verifier decomposes into separate reward functions:
#   - Accuracy: Is the label correct?
#   - Calibration: Is the confidence appropriate given correctness?
#   - Format: Is the JSON schema valid?
#
# The judge returns "yes" or "no" — a binary signal vs the multi-component
# weighted reward from the executable verifier variant.
# ---------------------------------------------------------------------------
JUDGE_PROMPT = """\
You are evaluating a network security classification model's response.

The model was given a network log entry and asked to classify it as \
"Benign", "Malicious", or "Abstain" with a confidence score (0.0-1.0) \
in JSON format: {{"label": "...", "confidence": 0.0-1.0, "rationale": "..."}}.

Network log entry:
```
{question}
```

Correct classification: {answer}

Model's parsed response: {response}

Evaluate whether the model's response is acceptable by checking ALL of:
1. The label matches the correct classification (case-insensitive)
2. The response is valid JSON with required fields (label, confidence)
3. The confidence is reasonable (high if correct, low if uncertain)

Respond "yes" if the response is correct and well-formed, or "no" otherwise.\
"""


# ---------------------------------------------------------------------------
# Judge reward function
# ---------------------------------------------------------------------------
async def judge_reward(prompt, completion, answer, state, judge, **kwargs):
    """Binary reward from LLM judge evaluation.

    Calls the JudgeRubric's judge method which formats the judge prompt,
    sends it to the judge model, and returns the text response.
    Returns 1.0 for "yes", 0.0 for "no" or any other response.
    """
    result = await judge(prompt, completion, answer, state)
    return 1.0 if result.strip().lower().startswith("yes") else 0.0


class NetworkLogParser(JsonClassificationParser):
    """Parser for network log classification outputs (shared with executable variant)."""

    def __init__(self) -> None:
        super().__init__(allowed_labels=["Benign", "Malicious", "Abstain"])


def load_environment(
    dataset_name: str = "iot23-train-dev-test-v1.jsonl",
    dataset_source: DatasetSource = "auto",
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
    judge_model: str = "gpt-4.1-nano",
    **extra_kwargs,  # Accept and log unknown kwargs for debugging
) -> vf.SingleTurnEnv:
    """Load the Network Logs environment with LLM-judge rewards (WP3c variant).

    This environment is identical to sv-env-network-logs in dataset, prompt, and
    parsing, but uses a JudgeRubric with a single LLM-judge binary reward instead
    of multi-component executable reward functions.

    Args:
        dataset_name: Dataset to load (same options as sv-env-network-logs).
        dataset_source: Where to load the dataset from ("auto", "local", "hub", "synthetic").
        max_examples: Maximum number of examples to use from the dataset.
        logger: Optional rollout logger for instrumenting environment metadata.
        judge_model: LLM model to use as judge (default: gpt-4.1-nano for cost parity).

    Returns:
        A Verifiers SingleTurnEnv configured with JudgeRubric reward.

    Notes:
        The judge model default (gpt-4.1-nano) is chosen to keep per-step costs
        comparable to the executable verifier variant. The judge is called once per
        rollout, producing a binary 0/1 reward signal.

        For the matched-budget experiment (WP3c), use the same training config
        parameters (max_steps, batch_size, rollouts_per_example) as e1.toml.
    """
    _log = _logging.getLogger("sv_env_network_logs_judge")
    _debug = os.environ.get("SV_DEBUG", "")

    if extra_kwargs:
        _log.warning(
            "[SV_DEBUG] load_environment (judge) received unexpected kwargs: %s "
            "(these are being IGNORED but may indicate config mismatch)",
            extra_kwargs,
        )

    if _debug:
        _log.warning(
            "[SV_DEBUG] load_environment (judge) called with: "
            "dataset_name=%r, dataset_source=%r, max_examples=%r, "
            "judge_model=%r, logger=%s, extra_kwargs=%s, HF_TOKEN=%s",
            dataset_name,
            dataset_source,
            max_examples,
            judge_model,
            "present" if logger else "None",
            extra_kwargs or "none",
            "set" if os.environ.get("HF_TOKEN") else "NOT SET",
        )

    env_root = Path(__file__).parent

    def _create_synthetic_dataset():
        """Create a synthetic dataset for testing purposes (shared with executable variant)."""
        # Same synthetic data as the executable variant for controlled comparison
        log_patterns = [
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
        return Dataset.from_list(log_patterns)

    # Load dataset using shared multi-tiered loader (same as executable variant)
    dataset, resolved_name = load_dataset_with_fallback(
        dataset_name=dataset_name,
        env_root=env_root,
        dataset_source=dataset_source,
        max_examples=max_examples,
        field_mapping=None,
        synthetic_generator=_create_synthetic_dataset,
    )
    dataset_name = resolved_name

    if _debug and dataset is not None:
        _log.warning(
            "[SV_DEBUG] Dataset loaded (judge variant): name=%s, len=%d, columns=%s",
            dataset_name,
            len(dataset),
            dataset.column_names,
        )

    parser = NetworkLogParser()

    # Use JudgeRubric instead of executable Rubric
    # The judge_reward function uses the judge callable injected by JudgeRubric
    rubric = vf.JudgeRubric(
        parser=parser,
        judge_model=judge_model,
        judge_prompt=JUDGE_PROMPT,
        judge_sampling_args={"max_tokens": 16, "temperature": 0.0},
    )
    # Add the judge_reward function that interprets the LLM judge's yes/no response
    rubric.add_reward_func(judge_reward, weight=1.0)

    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name="sv-env-network-logs-judge",
            dataset_name=dataset_name,
            total_examples=len(dataset) if dataset is not None else None,
            metadata={
                "max_examples": max_examples,
                "judge_model": judge_model,
                "reward_type": "llm-judge",
            },
        )

    return vf.SingleTurnEnv(
        name="sv-env-network-logs-judge",
        description=(
            "Classify network logs as 'Malicious', 'Benign', or 'Abstain' "
            "(LLM-judge reward variant for WP3c comparison)."
        ),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=(
            "You are a network security analyst. Analyze the provided network log entry and "
            'respond with a JSON object: {"label": \'Benign|Malicious|Abstain\', '
            '"confidence": 0.0-1.0, "rationale": optional}.'
        ),
    )
