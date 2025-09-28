"""Phishing detection environment with abstention, calibration, and evidence rewards."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re
import sys
from typing import Any

import verifiers as vf
from datasets import Dataset, load_dataset

# Enable importing shared components when running from source.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sv_shared import (  # type: ignore  # pylint: disable=wrong-import-position
    JsonClassificationParser,
    RolloutLogger,
)
from sv_shared.rewards import reward_accuracy, reward_calibration  # type: ignore  # pylint: disable=wrong-import-position


_URL_PATTERN = re.compile(r"https?://[^\s>]+", re.IGNORECASE)
_SUSPICIOUS_KEYWORDS = {
    "verify",
    "reset",
    "urgent",
    "credentials",
    "bank",
    "login",
    "password",
    "account",
    "invoice",
    "refund",
    "wire",
    "bitcoin",
}


class PhishingEmailParser(JsonClassificationParser):
    """Parse JSON phishing classifications with evidence lists."""

    def __init__(self) -> None:
        super().__init__(allowed_labels=["Phishing", "Legitimate", "Abstain"])
        self._label_lookup = {label.lower(): label for label in self.allowed_labels}

    def parse_answer(self, completion: Any) -> str:  # type: ignore[override]
        data = self._parse_json(completion)
        label = data.get("label")
        if isinstance(label, str):
            canonical = self._label_lookup.get(label.strip().lower())
            if canonical:
                return canonical
        return ""

    def parse_evidence(self, completion: Any) -> list[str]:  # noqa: D401
        """Return evidence strings if provided."""

        data = self._parse_json(completion)
        evidence = data.get("evidence")
        if evidence is None:
            return []
        if isinstance(evidence, Iterable) and not isinstance(evidence, (str, bytes)):
            items: list[str] = []
            for item in evidence:
                if isinstance(item, str) and item.strip():
                    items.append(item.strip())
            return items
        return []

    def get_format_reward_func(self):  # type: ignore[override]
        parser = self

        def format_reward(completion: Any, **kwargs: Any) -> float:  # noqa: ANN401
            data = parser._parse_json(completion)
            if not data:
                return 0.0

            label = parser.parse_answer(completion)
            if not label:
                return 0.0

            if "confidence" not in data:
                return 0.0
            try:
                confidence_value = float(data["confidence"])
            except (TypeError, ValueError):
                return 0.0
            if not 0.0 <= confidence_value <= 1.0:
                return 0.0

            if "evidence" in data:
                evidence = parser.parse_evidence(completion)
                if data["evidence"] not in ([], None) and not evidence:
                    return 0.0

            return 1.0

        return format_reward


def _extract_email_text(example: dict[str, Any]) -> str:
    return example.get("text") or example.get("email") or example.get("body") or example.get("content") or ""


def _normalize_label(raw_label: Any) -> str:
    if isinstance(raw_label, int):
        return "Phishing" if raw_label == 1 else "Legitimate"
    if isinstance(raw_label, str):
        lowered = raw_label.strip().lower()
        if lowered in {"phishing", "spam", "malicious", "fraud"}:
            return "Phishing"
        if lowered == "abstain":
            return "Abstain"
    return "Legitimate"


def _extract_phishing_indicators(
    *,
    email_text: str,
    subject: str,
    sender: str,
) -> list[str]:
    indicators: list[str] = []
    lowered = email_text.lower()

    indicators.extend(_URL_PATTERN.findall(email_text))

    for keyword in _SUSPICIOUS_KEYWORDS:
        if keyword in lowered:
            indicators.append(keyword)

    if sender and any(char in sender for char in {"0", "1", "-", "@"}):
        suspicious_sender = sender.lower()
        if any(token in suspicious_sender for token in {"amaz0n", "paypai", "support", "alert"}):
            indicators.append(sender)

    if subject and any(term in subject.lower() for term in {"urgent", "action required", "verify"}):
        indicators.append(subject)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for item in indicators:
        normalized = item.lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(item)
    return deduped


def transform_dataset(raw_dataset: Dataset, max_examples: int | None) -> Dataset:
    """Transform raw phishing datasets into SingleTurnEnv format."""

    def transform_example(example: dict[str, Any]) -> dict[str, Any]:
        email_text = _extract_email_text(example)
        subject = example.get("subject", "")
        sender = example.get("sender", "")

        prompt_lines: list[str] = []
        if sender:
            prompt_lines.append(f"From: {sender}")
        if subject:
            prompt_lines.append(f"Subject: {subject}")
        if prompt_lines:
            prompt_lines.append("")
            prompt_lines.append(email_text)
        else:
            prompt_lines.append(f"Email: {email_text}")
        prompt_text = "\n".join(prompt_lines)

        label = _normalize_label(example.get("label"))
        indicators = _extract_phishing_indicators(
            email_text=email_text,
            subject=subject,
            sender=sender,
        )

        return {
            "question": prompt_text.strip(),
            "answer": label,
            "metadata": {"phishing_indicators": indicators},
        }

    transformed = raw_dataset.map(transform_example, remove_columns=raw_dataset.column_names)

    if max_examples and len(transformed) > max_examples:
        transformed = transformed.select(range(max_examples))

    return transformed


def reward_phishing_asymmetric_cost(
    *,
    completion: Any,
    answer: str,
    parser: PhishingEmailParser,
    **kwargs: Any,
) -> float:
    """Penalize missed phishing more than cautious behaviour."""

    prediction = parser.parse_answer(completion)
    if not prediction or not answer:
        return 0.0

    predicted = prediction.lower()
    actual = answer.lower()

    if predicted == actual:
        return 1.0

    if actual == "phishing":
        if predicted == "legitimate":
            return -1.0
        if predicted == "abstain":
            return 0.3
        return -0.5

    if actual == "legitimate":
        if predicted == "phishing":
            return -0.2
        if predicted == "abstain":
            return 0.5

    if actual == "abstain":
        if predicted == "phishing":
            return 0.3
        if predicted == "legitimate":
            return 0.3

    return 0.0


def reward_evidence_alignment(
    *,
    completion: Any,
    answer: str,
    parser: PhishingEmailParser,
    state: dict[str, Any] | None = None,
    prompt: str | None = None,
    **kwargs: Any,
) -> float:
    """Reward evidence that matches known phishing indicators."""

    if answer.lower() != "phishing":
        return 0.0

    evidence = parser.parse_evidence(completion)
    if not evidence:
        return 0.0

    indicators: list[str] = []
    if state and isinstance(state, dict):
        metadata = state.get("metadata")
        if isinstance(metadata, dict):
            raw_indicators = metadata.get("phishing_indicators", [])
            if isinstance(raw_indicators, list):
                indicators = [str(item).strip() for item in raw_indicators if str(item).strip()]

    prompt_text = prompt or (state.get("question") if state else "") or ""
    prompt_lower = prompt_text.lower()

    matches = 0.0
    for item in evidence:
        normalized = item.strip().lower()
        if not normalized:
            continue
        if any(
            normalized == indicator.lower() or indicator.lower() in normalized or normalized in indicator.lower()
            for indicator in indicators
        ):
            matches += 1.0
            continue
        if normalized in prompt_lower:
            matches += 0.5

    return min(1.0, matches / len(evidence))


def load_environment(
    dataset_name: str = "zefang-liu/phishing-email-dataset",
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
) -> vf.SingleTurnEnv:
    """Load the Phishing Email Detection environment."""

    try:
        dataset = load_dataset(dataset_name, split="train")
        assert isinstance(dataset, Dataset), "Loaded dataset is not of type Dataset"
        dataset = transform_dataset(dataset, max_examples)
    except (
        FileNotFoundError,
        ConnectionError,
        ValueError,
        ImportError,
        AssertionError,
    ) as exc:  # pragma: no cover - exercised via tests with monkeypatch
        print(f"Failed to load dataset '{dataset_name}': {exc}")
        print("Falling back to a synthetic dataset.")

        dataset = Dataset.from_list(
            [
                {
                    "question": (
                        "From: security@amaz0n-account.com\n"
                        "Subject: Urgent: Your Account Will Be Suspended!\n\n"
                        "Dear Customer,\n\n"
                        "We detected suspicious activity on your account. Click here immediately to verify your identity: "
                        "http://bit.ly/verify-acc0unt\n\n"
                        "If you don't act within 24 hours, your account will be permanently suspended.\n\n"
                        "Amazon Security Team"
                    ),
                    "answer": "Phishing",
                    "metadata": {
                        "phishing_indicators": [
                            "security@amaz0n-account.com",
                            "urgent",
                            "http://bit.ly/verify-acc0unt",
                        ]
                    },
                },
                {
                    "question": (
                        "Subject: You've Won $1,000,000!!!\n\n"
                        "Congratulations! You are our lucky winner! To claim your prize, please provide:\n"
                        "- Full name\n- Social Security Number\n- Bank account details\n\n"
                        "Reply immediately or lose this opportunity!"
                    ),
                    "answer": "Phishing",
                    "metadata": {
                        "phishing_indicators": [
                            "You've Won $1,000,000!!!",
                            "Social Security Number",
                            "bank account",
                        ]
                    },
                },
                {
                    "question": (
                        "From: IT-Support@yourcompany.co\n"
                        "Subject: Password Expiration Notice\n\n"
                        "Your password will expire in 1 hour. Click below to reset:\n"
                        "http://suspicious-site.ru/password-reset\n\n"
                        "Failure to update will result in account lockout."
                    ),
                    "answer": "Phishing",
                    "metadata": {
                        "phishing_indicators": [
                            "Password Expiration Notice",
                            "http://suspicious-site.ru/password-reset",
                            "account lockout",
                        ]
                    },
                },
                {
                    "question": (
                        "From: noreply@paypaI.com\n"
                        "Subject: Suspicious Transaction Alert\n\n"
                        "We noticed a $500 transaction from your account. If this wasn't you, click here:\n"
                        "www.paypaI-security.tk/dispute\n\n"
                        "Act fast to protect your funds!"
                    ),
                    "answer": "Phishing",
                    "metadata": {
                        "phishing_indicators": [
                            "noreply@paypaI.com",
                            "Suspicious Transaction Alert",
                            "www.paypaI-security.tk/dispute",
                        ]
                    },
                },
                {
                    "question": (
                        "Subject: IRS Tax Refund - Action Required\n\n"
                        "You have a pending tax refund of $3,458.00. To receive your refund, verify your information at: "
                        "irs-refunds.website/claim\n\n"
                        "This offer expires in 48 hours."
                    ),
                    "answer": "Phishing",
                    "metadata": {
                        "phishing_indicators": [
                            "IRS Tax Refund - Action Required",
                            "irs-refunds.website/claim",
                            "expires in 48 hours",
                        ]
                    },
                },
                {
                    "question": (
                        "From: threat-hunter@corpsec.io\n"
                        "Subject: Credential harvesting simulation\n\n"
                        "Security exercise: please forward any suspicious emails to phishing@corpsec.io."
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: notifications@github.com\n"
                        "Subject: [GitHub] Your deployment is live\n\n"
                        "Your recent push to main branch has been successfully deployed to production.\n\n"
                        "View deployment: https://github.com/yourrepo/deployments\n\n"
                        "Happy coding!\nThe GitHub Team"
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: calendar-notification@google.com\n"
                        "Subject: Reminder: Team Meeting at 2:00 PM\n\n"
                        "This is a reminder that you have 'Weekly Team Sync' starting in 30 minutes.\n\n"
                        "Location: Conference Room B\n"
                        "Time: 2:00 PM - 3:00 PM EST"
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: no-reply@linkedin.com\n"
                        "Subject: You have a new connection request\n\n"
                        "Hi John,\n\n"
                        "Sarah Smith wants to connect with you on LinkedIn.\n\n"
                        "View profile: https://www.linkedin.com/in/sarah-smith\n\n"
                        "LinkedIn Corporation"
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: receipts@uber.com\n"
                        "Subject: Your Tuesday trip with Uber\n\n"
                        "Total: $12.45\n"
                        "Trip time: 15 minutes\n"
                        "Distance: 3.2 miles\n\n"
                        "Thank you for riding with Uber!"
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: team@slack.com\n"
                        "Subject: Your workspace invite is ready\n\n"
                        "You've been invited to join the 'Engineering Team' workspace on Slack.\n\n"
                        "Join here: https://slack.com/signin/workspaces\n\n"
                        "Questions? Contact your workspace admin."
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
                {
                    "question": (
                        "From: peopleops@company.com\n"
                        "Subject: Benefits enrollment window\n\n"
                        "Reminder: benefits enrollment is open until Friday. Visit the HR portal to review your selections."
                    ),
                    "answer": "Legitimate",
                    "metadata": {"phishing_indicators": []},
                },
            ]
        )
        dataset_name = f"synthetic::{dataset_name}"

    parser = PhishingEmailParser()

    rubric = vf.Rubric(
        funcs=[
            reward_accuracy,
            parser.get_format_reward_func(),
            reward_calibration,
            reward_phishing_asymmetric_cost,
            reward_evidence_alignment,
        ],
        weights=[1.0, 0.2, 0.2, 0.4, 0.2],
        parser=parser,
    )

    if logger and logger.enabled:
        logger.log_environment_init(
            environment_name="sv-env-phishing-detection",
            dataset_name=dataset_name,
            total_examples=len(dataset) if dataset is not None else None,
            metadata={"max_examples": max_examples},
        )

    return vf.SingleTurnEnv(
        name="sv-env-phishing-detection",
        description="Detect phishing emails with calibrated confidence and supporting evidence.",
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=(
            "You are an email security analyst. Review the message and respond with a JSON object containing a "
            "'label' (Phishing, Legitimate, or Abstain), a 'confidence' value between 0 and 1, and optional "
            "'evidence' strings referencing indicators in the email."
        ),
    )
