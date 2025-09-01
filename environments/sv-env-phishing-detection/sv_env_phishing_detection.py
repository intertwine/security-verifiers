"""sv_env_phishing_detection: Security Verifiers environment for Phishing Email Detection.

This package implements PRD Environment #4: A SingleTurnEnv where models classify
emails as phishing attempts or legitimate emails. The environment provides email text
as prompts and expects classification labels as outputs.
"""

from __future__ import annotations

import verifiers as vf
from datasets import Dataset, load_dataset


class PhishingEmailParser(vf.Parser):
    """Parser to extract classification label from model responses."""

    def parse_answer(self, completion: str) -> str:
        """Extract 'Phishing' or 'Legitimate' from the response.

        Args:
            completion: The raw model completion/response.

        Returns:
            The extracted classification label in standard format.
        """
        # Clean and normalize the response
        cleaned = completion.strip().lower()

        # Look for the classification labels
        # Check for "not phishing" before "phishing"
        if "not phishing" in cleaned:
            return "Legitimate"

        if "phishing" in cleaned:
            return "Phishing"

        if "legitimate" in cleaned or "safe" in cleaned:
            return "Legitimate"

        # Return original if no clear label found
        return completion.strip()

    def get_format_reward_func(self):
        """Return a format reward function that checks for proper classification format."""

        def format_reward(
            completion,
            answer="",  # pylint: disable=unused-argument
            **kwargs,  # pylint: disable=unused-argument
        ):
            """Reward proper classification format (single word: Phishing or Legitimate)."""
            # Extract response text from completion
            if isinstance(completion, list):
                response = completion[-1]["content"] if completion else ""
            else:
                response = str(completion)

            # Check if response is a single classification word
            cleaned = response.strip().lower()

            # Perfect format: exactly "phishing" or "legitimate" (case insensitive)
            if cleaned in ["phishing", "legitimate"]:
                return 1.0

            # Good format: contains the word but has extra text
            if "phishing" in cleaned or "legitimate" in cleaned:
                return 0.5

            # Poor format: doesn't contain expected classification
            return 0.0

        return format_reward


def reward_correct_classification(
    completion,
    answer: str = "",
    parser: vf.Parser | None = None,
    **kwargs,  # pylint: disable=unused-argument
) -> float:
    """Reward function that checks if the parsed classification matches the expected label.

    Args:
        completion: The model's response (predicted classification).
        answer: The ground truth answer from the dataset.
        parser: The parser instance to extract the classification.
        **kwargs: Additional arguments (prompt, state, etc).

    Returns:
        1.0 if the prediction matches the ground truth, 0.0 otherwise.
    """
    # Extract the response text from completion
    if isinstance(completion, list):
        response = completion[-1]["content"] if completion else ""
    else:
        response = str(completion)

    # Use parser to extract classification if available
    if parser:
        predicted = parser.parse_answer(response)
    else:
        predicted = response.strip()

    # Case-insensitive comparison
    if not predicted or not answer:
        return 0.0
    return 1.0 if predicted.lower() == answer.strip().lower() else 0.0


def transform_dataset(raw_dataset: Dataset, max_examples: int | None) -> Dataset:
    """Transform raw dataset to SingleTurnEnv format."""

    def transform_example(example):
        # Transform the phishing dataset into prompt format
        # Expecting columns like 'text' or 'email' and 'label'
        email_text = example.get("text") or example.get("email") or example.get("body", "")
        subject = example.get("subject", "")
        sender = example.get("sender", "")

        # Construct the email prompt
        if subject or sender:
            prompt_parts = []
            if sender:
                prompt_parts.append(f"From: {sender}")
            if subject:
                prompt_parts.append(f"Subject: {subject}")
            prompt_parts.append(f"\n{email_text}")
            prompt_text = "\n".join(prompt_parts)
        else:
            prompt_text = f"Email: {email_text}"

        # Map labels to standard format
        label = example.get("label", "")
        if isinstance(label, int):
            # Binary classification: 0=legitimate, 1=phishing
            label = "Phishing" if label == 1 else "Legitimate"
        elif isinstance(label, str):
            label_lower = label.lower()
            if "phish" in label_lower or "spam" in label_lower or "malicious" in label_lower:
                label = "Phishing"
            else:
                label = "Legitimate"

        return {
            "question": prompt_text,
            "answer": label,
        }

    transformed = raw_dataset.map(transform_example)

    if max_examples and len(transformed) > max_examples:
        transformed = transformed.select(range(max_examples))

    return transformed


def load_environment(
    dataset_name: str = "zefang-liu/phishing-email-dataset",
    max_examples: int = 1000,
) -> vf.SingleTurnEnv:
    """Load the Phishing Email Detection environment.

    This environment is a single-turn classification task where the model
    inspects an email and determines whether it is a phishing attempt or legitimate.

    Args:
        dataset_name: HuggingFace dataset name for phishing emails.
        max_examples: Maximum number of examples to use from the dataset.

    Returns:
        A Verifiers SingleTurnEnv configured for the task.
    """
    try:
        # Load the dataset from HuggingFace
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

            # Generate synthetic phishing and legitimate emails
            # pylint: disable=line-too-long
            email_patterns = [
                # Phishing examples
                {
                    "question": (
                        "From: security@amaz0n-account.com\n"
                        "Subject: Urgent: Your Account Will Be Suspended!\n\n"
                        "Dear Customer,\n\n"
                        "We detected suspicious activity on your account. Click here immediately to "
                        "verify your identity: http://bit.ly/verify-acc0unt\n\n"
                        "If you don't act within 24 hours, your account will be permanently suspended.\n\n"
                        "Amazon Security Team"
                    ),
                    "answer": "Phishing",
                },
                {
                    "question": (
                        "Subject: You've Won $1,000,000!!!\n\n"
                        "Congratulations! You are our lucky winner! To claim your prize, please provide:\n"
                        "- Full name\n- Social Security Number\n- Bank account details\n\n"
                        "Reply immediately or lose this opportunity!"
                    ),
                    "answer": "Phishing",
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
                },
                {
                    "question": (
                        "Subject: IRS Tax Refund - Action Required\n\n"
                        "You have a pending tax refund of $3,458.00. To receive your refund, verify "
                        "your information at: irs-refunds.website/claim\n\n"
                        "This offer expires in 48 hours."
                    ),
                    "answer": "Phishing",
                },
                # Legitimate examples
                {
                    "question": (
                        "From: notifications@github.com\n"
                        "Subject: [GitHub] Your deployment is live\n\n"
                        "Your recent push to main branch has been successfully deployed to production.\n\n"
                        "View deployment: https://github.com/yourrepo/deployments\n\n"
                        "Happy coding!\nThe GitHub Team"
                    ),
                    "answer": "Legitimate",
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
                },
            ]
            # pylint: enable=line-too-long

            examples.extend(email_patterns)
            return Dataset.from_list(examples)

        dataset = _create_synthetic_dataset()

    parser = PhishingEmailParser()

    rubric = vf.Rubric(
        funcs=[
            reward_correct_classification,
            parser.get_format_reward_func(),
        ],
        weights=[1.0, 0.2],  # Classification accuracy is primary, format is secondary
    )

    return vf.SingleTurnEnv(
        name="sv-env-phishing-detection",
        description="Classify emails as 'Phishing' or 'Legitimate'.",
        dataset=dataset,
        parser=parser,
        rubric=rubric,
        system_prompt=(
            "You are an email security analyst. Analyze the provided email and classify it as either "
            "'Phishing' or 'Legitimate'. Look for signs of deception, suspicious URLs, urgent language, "
            "and requests for sensitive information. Respond with only the classification label."
        ),
    )
