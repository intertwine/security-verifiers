"""sv_netlogs_judge_impl: LLM-judge reward variant of Network Log environment.

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

import json
import logging as _logging
import os
import sys
from pathlib import Path

import verifiers as vf
from datasets import Dataset
from openai import APIError, APITimeoutError, RateLimitError
from verifiers.utils.async_utils import maybe_await

REPO_ROOT = str(Path(__file__).resolve().parents[2])

try:
    # Try importing from installed package first
    from sv_shared import weave_init  # type: ignore  # noqa: F401
except ImportError:
    # Fall back to local development import
    if REPO_ROOT not in sys.path:
        sys.path.append(REPO_ROOT)
    from sv_shared import weave_init  # type: ignore  # noqa: F401

try:
    from sv_shared import (
        DatasetSource,
        JsonClassificationParser,
        RolloutLogger,
        get_response_text,
        load_dataset_with_fallback,
    )
except ImportError:
    # Fall back to local development import
    if REPO_ROOT not in sys.path:
        sys.path.append(REPO_ROOT)
    from sv_shared import (  # type: ignore
        DatasetSource,
        JsonClassificationParser,
        RolloutLogger,
        get_response_text,
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


def format_completion_for_judge(parser: NetworkLogParser, completion) -> str:
    """Format a completion for judge prompts with full structured context.

    JudgeRubric normally passes parser.parse_answer(completion) into the judge
    prompt, which only yields the label (for example "Benign"). That erased the
    confidence/format information the judge prompt explicitly asks about, causing
    the judge to reject otherwise-correct responses as not valid JSON.

    We instead pass a canonical JSON rendering of the parsed response so the
    judge can evaluate label, confidence, and structure together. If parsing
    fails, fall back to the raw response text for debugging resilience.
    """
    data = parser._parse_json(completion)
    if data:
        canonical = {key: data[key] for key in ("label", "confidence", "rationale") if key in data}
        if canonical:
            return json.dumps(canonical, sort_keys=True)
    return get_response_text(completion)


class _JudgePromptParser:
    """Thin parser wrapper used only when rendering the judge prompt."""

    def __init__(self, base_parser: NetworkLogParser) -> None:
        self.base_parser = base_parser

    def parse_answer(self, completion) -> str:
        return format_completion_for_judge(self.base_parser, completion)

    def __getattr__(self, name: str):
        return getattr(self.base_parser, name)


class StructuredResponseJudgeRubric(vf.JudgeRubric):
    """JudgeRubric that feeds structured JSON to the judge prompt.

    Upstream JudgeRubric calls parser.parse_answer(completion), which is too
    lossy for this environment because the judge prompt evaluates JSON validity
    and confidence as well as the label. We compute the structured response
    directly inside judge() so concurrent scoring cannot mutate shared rubric
    state.
    """

    def __init__(self, parser: NetworkLogParser, **kwargs) -> None:
        super().__init__(parser=parser, **kwargs)
        self._prompt_parser = _JudgePromptParser(parser)

    async def judge(self, prompt, completion, answer, state=None) -> str:
        if isinstance(prompt, list):
            last_msg = prompt[-1]
            if isinstance(last_msg, dict) and "content" in last_msg:
                question = str(last_msg["content"])
            else:
                question = ""
        else:
            question = str(prompt)

        response = self._prompt_parser.parse_answer(completion)
        judge_prompt = self.judge_prompt.format(question=question, answer=answer, response=response)
        cached = state.get("judge_response") if state else None
        if isinstance(cached, dict) and judge_prompt in cached:
            return cached[judge_prompt]

        judge_args = dict(self.judge_sampling_args or {})
        if "max_tokens" in judge_args:
            if judge_args["max_tokens"] is None:
                judge_args.pop("max_tokens")
            else:
                judge_args["max_completion_tokens"] = judge_args.pop("max_tokens")
        if "max_completion_tokens" in judge_args and judge_args["max_completion_tokens"] is None:
            judge_args.pop("max_completion_tokens")
        judge_args = {k: v for k, v in judge_args.items() if v is not None}

        try:
            judge_response = await maybe_await(
                self.judge_client.chat.completions.create,
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                **judge_args,
            )
            judge_response = str(judge_response.choices[0].message.content)
        except RateLimitError as e:
            self.logger.warning(
                f"Rate limit exceeded when calling judge model '{self.judge_model}'. "
                f"Try reducing concurrency or waiting before retrying. Error: {str(e)}"
            )
            raise RuntimeError(
                f"Judge model rate limit exceeded. Try reducing concurrency or waiting before retrying. "
                f"Model: {self.judge_model}, Error: {str(e)}"
            ) from e
        except APITimeoutError as e:
            self.logger.warning(
                f"Timeout when calling judge model '{self.judge_model}'. "
                f"Increase timeout in judge_sampling_args or check model responsiveness. Error: {str(e)}"
            )
            raise RuntimeError(
                f"Judge model timeout. Increase timeout in judge_sampling_args or check model responsiveness. "
                f"Model: {self.judge_model}, Error: {str(e)}"
            ) from e
        except APIError as e:
            self.logger.warning(
                f"API error when calling judge model '{self.judge_model}'. "
                f"Check model availability and API key. Error: {str(e)}"
            )
            raise RuntimeError(
                f"Judge model API error. Check model availability and API key. "
                f"Model: {self.judge_model}, Error: {str(e)}"
            ) from e
        except Exception as e:
            self.logger.warning(f"Unexpected error when calling judge model '{self.judge_model}'. Error: {str(e)}")
            raise RuntimeError(
                f"Unexpected error when calling judge model '{self.judge_model}'. Error: {str(e)}"
            ) from e

        if state:
            if not isinstance(cached, dict):
                cached = {}
            cached[judge_prompt] = judge_response
            state["judge_response"] = cached
        return judge_response


DEFAULT_ENV_NAME = "sv-env-network-logs-judge"


def load_environment(
    dataset_name: str = "iot23-train-dev-test-v1.jsonl",
    dataset_source: DatasetSource = "auto",
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
    judge_model: str = "gpt-4.1-nano",
    env_name: str = DEFAULT_ENV_NAME,
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
        env_name: Environment name/env_id to expose and log for this loader.

    Returns:
        A Verifiers SingleTurnEnv configured with JudgeRubric reward.

    Notes:
        The judge model default (gpt-4.1-nano) is chosen to keep per-step costs
        comparable to the executable verifier variant. The judge is called once per
        rollout, producing a binary 0/1 reward signal.

        For the matched-budget experiment (WP3c), use the same training config
        parameters (max_steps, batch_size, rollouts_per_example) as e1.toml.
    """
    _log = _logging.getLogger("sv_netlogs_judge_impl")
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
            "judge_model=%r, env_name=%r, logger=%s, extra_kwargs=%s, HF_TOKEN=%s",
            dataset_name,
            dataset_source,
            max_examples,
            judge_model,
            env_name,
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
    rubric = StructuredResponseJudgeRubric(
        parser=parser,
        judge_model=judge_model,
        judge_prompt=JUDGE_PROMPT,
        judge_sampling_args={"max_tokens": 16, "temperature": 0.0},
    )
    # Add the judge_reward function that interprets the LLM judge's yes/no response
    rubric.add_reward_func(judge_reward, weight=1.0)

    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name=env_name,
            dataset_name=dataset_name,
            total_examples=len(dataset) if dataset is not None else None,
            metadata={
                "max_examples": max_examples,
                "judge_model": judge_model,
                "reward_type": "llm-judge",
            },
        )

    return vf.SingleTurnEnv(
        name=env_name,
        env_id=env_name,
        description=(
            "Classify network logs as 'Malicious', 'Benign', or 'Abstain' "
            "(LLM-judge reward variant for WP3c comparison)."
        ),
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=(
            "You are a network security analyst. Analyze the provided network log entry and "
            "respond with a JSON object: {\"label\": 'Benign|Malicious|Abstain', "
            '"confidence": 0.0-1.0, "rationale": optional}.'
        ),
    )
