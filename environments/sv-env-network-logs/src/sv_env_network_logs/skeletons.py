from __future__ import annotations

import re
from typing import Any, Mapping

import verifiers as vf
from datasets import Dataset, load_dataset

from .interfaces import NetworkLogsEnvironment as NetworkLogsEnvironmentProtocol
from .interfaces import NetworkLogsVerifier as NetworkLogsVerifierProtocol


class NetworkLogsVerifier(NetworkLogsVerifierProtocol):
    """Verifier for network log anomaly detection using pattern-based classification."""

    def __init__(self):
        self._last_details: dict[str, Any] = {}

        # Define patterns that typically indicate malicious activity
        self.malicious_patterns = [
            r"port scan",
            r"unusual port scanning",
            r"failed login attempt",
            r"brute force",
            r"malware",
            r"botnet",
            r"DDoS",
            r"injection",
            r"exploit",
            r"backdoor",
            r"trojan",
            r"suspicious",
            r"anomaly detected",
            r"intrusion",
            r"unauthorized",
            r"blocked connection",
            r"denied access",
        ]

        # Compile patterns for efficiency
        self.malicious_regex = re.compile("|".join(self.malicious_patterns), re.IGNORECASE)

    def score(self, log_entry: str, ground_truth: str) -> float:
        """Score classification accuracy for a network log entry."""
        classification = self.classify(log_entry)

        # Store details for this classification
        self._last_details = {
            "log_entry": log_entry,
            "predicted": classification,
            "ground_truth": ground_truth,
            "matched_patterns": self._get_matched_patterns(log_entry),
            "confidence": self._calculate_confidence(log_entry),
        }

        # Binary scoring: 1.0 for exact match, 0.0 for mismatch
        return 1.0 if classification.lower() == ground_truth.lower() else 0.0

    def classify(self, log_entry: str) -> str:
        """Classify a network log entry as malicious or benign."""
        if self.malicious_regex.search(log_entry):
            return "Malicious"
        return "Benign"

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information from the last verification."""
        return self._last_details.copy()

    def _get_matched_patterns(self, log_entry: str) -> list[str]:
        """Get list of malicious patterns that matched in the log entry."""
        matched = []
        for pattern in self.malicious_patterns:
            if re.search(pattern, log_entry, re.IGNORECASE):
                matched.append(pattern)
        return matched

    def _calculate_confidence(self, log_entry: str) -> float:
        """Calculate confidence score based on number of matched patterns."""
        matches = len(self._get_matched_patterns(log_entry))
        if matches == 0:
            return 0.8  # High confidence for benign (no malicious indicators)
        elif matches == 1:
            return 0.7  # Medium-high confidence for single indicator
        else:
            return 0.9  # Very high confidence for multiple indicators


class NetworkLogsEnvironment(NetworkLogsEnvironmentProtocol):
    """SingleTurnEnv environment for network logs anomaly detection."""

    def __init__(
        self,
        dataset_name: str = "19kmunz/iot-23-preprocessed-minimumcolumns",
        verifier: NetworkLogsVerifier | None = None,
        max_examples: int = 1000,
    ):
        """Initialize the network logs environment.

        Args:
            dataset_name: HuggingFace dataset name for network logs
            verifier: Custom verifier instance (uses default if None)
            max_examples: Maximum number of examples to use from dataset
        """
        self.dataset_name = dataset_name
        self.verifier = verifier or NetworkLogsVerifier()
        self.max_examples = max_examples
        self._dataset: Dataset | None = None

        # Create the Verifiers SingleTurnEnv
        self._env = self._create_verifiers_env()

    def evaluate(self, log_entry: str, model_output: str) -> tuple[float, Mapping[str, Any]]:
        """Evaluate a model's classification of a network log entry."""
        # Extract just the classification from model output (handle verbose responses)
        cleaned_output = self._extract_classification(model_output)

        reward = self.verifier.score(log_entry, cleaned_output)
        info = self.verifier.details()

        return reward, info

    def get_dataset(self) -> Dataset:
        """Get the dataset of network log entries for training/evaluation."""
        if self._dataset is None:
            try:
                # Load the IoT-23 dataset
                raw_dataset = load_dataset(self.dataset_name, split="train")

                # Transform to the expected format for SingleTurnEnv
                self._dataset = self._transform_dataset(raw_dataset)
            except Exception:
                # Fallback to synthetic dataset if loading fails
                self._dataset = self._create_synthetic_dataset()

        return self._dataset

    def _create_verifiers_env(self) -> vf.SingleTurnEnv:
        """Create the underlying Verifiers SingleTurnEnv."""
        dataset = self.get_dataset()

        def reward_classification_match(
            prompt: str, completion: str, answer: str, **kwargs
        ) -> float:
            """Reward function for exact classification match."""
            predicted = self._extract_classification(completion)
            return 1.0 if predicted.lower() == answer.lower() else 0.0

        rubric = vf.Rubric(
            funcs=[reward_classification_match],
            weights=[1.0],
        )

        return vf.SingleTurnEnv(
            dataset=dataset,
            rubric=rubric,
            system_prompt=(
                "You are a network security analyst. Analyze the provided network log entry "
                "and classify it as either 'Malicious' or 'Benign'. Respond with only the "
                "classification label."
            ),
        )

    def _transform_dataset(self, raw_dataset: Dataset) -> Dataset:
        """Transform raw dataset to SingleTurnEnv format."""

        # This would need to be customized based on the actual dataset structure
        # For IoT-23, we'd map the appropriate columns
        def transform_example(example):
            # Assuming the dataset has 'log' and 'label' columns
            # Adapt this based on actual dataset structure
            return {
                "prompt": example.get("log", str(example)),  # Log entry text
                "answer": example.get("label", "Benign"),  # Ground truth label
            }

        transformed = raw_dataset.map(transform_example)

        # Limit to max_examples if specified
        if self.max_examples and len(transformed) > self.max_examples:
            transformed = transformed.select(range(self.max_examples))

        return transformed

    def _create_synthetic_dataset(self) -> Dataset:
        """Create a synthetic dataset for testing purposes."""
        examples = [
            {
                "prompt": (
                    "TCP connection from 10.0.0.5:445 to 192.168.1.10:80, flags [S], "
                    "unusual port scanning pattern detected"
                ),
                "answer": "Malicious",
            },
            {
                "prompt": (
                    "HTTP GET request from 192.168.1.100 to www.example.com, "
                    "normal web browsing activity"
                ),
                "answer": "Benign",
            },
            {
                "prompt": (
                    "Failed SSH login attempt from 203.0.113.0, "
                    "brute force attack pattern identified"
                ),
                "answer": "Malicious",
            },
            {
                "prompt": (
                    "DNS query from 192.168.1.50 for mail.company.com, standard email resolution"
                ),
                "answer": "Benign",
            },
            {
                "prompt": (
                    "Outbound connection blocked to known malware C&C server 198.51.100.1:443"
                ),
                "answer": "Malicious",
            },
            {
                "prompt": (
                    "HTTPS connection to banking.example.com from 192.168.1.25, "
                    "encrypted traffic normal"
                ),
                "answer": "Benign",
            },
            {
                "prompt": (
                    "Multiple failed authentication attempts detected from IP "
                    "203.0.113.5, suspicious activity"
                ),
                "answer": "Malicious",
            },
            {
                "prompt": (
                    "Regular file transfer via SFTP to backup server 10.0.1.100, "
                    "scheduled maintenance"
                ),
                "answer": "Benign",
            },
        ]

        return Dataset.from_list(examples)

    def _extract_classification(self, model_output: str) -> str:
        """Extract classification label from potentially verbose model output."""
        output_lower = model_output.lower().strip()

        # Look for explicit labels first
        if "malicious" in output_lower:
            return "Malicious"
        elif "benign" in output_lower:
            return "Benign"

        # Fallback: return the first word if it matches expected labels
        first_word = output_lower.split()[0] if output_lower.split() else ""
        if first_word in ["malicious", "benign"]:
            return first_word.capitalize()

        # Default fallback
        return "Benign"


def load_environment() -> NetworkLogsEnvironment:
    """Load the Network Logs Anomaly Detection environment for use with Verifiers framework.

    Returns:
        NetworkLogsEnvironment: Configured environment ready for RL training
    """
    return NetworkLogsEnvironment()
