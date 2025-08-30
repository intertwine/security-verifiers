"""NetworkLogsEnvironment implementation for anomaly detection in network logs."""

from __future__ import annotations

import logging
from typing import Any, Mapping

import verifiers as vf
from datasets import Dataset, load_dataset

from .verifier import NetworkLogsVerifier

logger = logging.getLogger(__name__)


class NetworkLogsEnvironment:
    """SingleTurnEnv environment for network logs anomaly detection.

    This environment implements PRD Environment #1: A single-turn classification task
    where the model inspects a network log entry and determines whether it is malicious
    or benign. Uses the Verifiers SingleTurnEnv framework.
    """

    def __init__(
        self,
        dataset_name: str = "19kmunz/iot-23-preprocessed-minimumcolumns",
        verifier: NetworkLogsVerifier | None = None,
        max_examples: int = 1000,
        system_prompt: str | None = None,
    ):
        """Initialize the network logs anomaly detection environment.

        Args:
            dataset_name: HuggingFace dataset name for network logs
            verifier: Custom verifier instance (uses default if None)
            max_examples: Maximum number of examples to use from dataset
            system_prompt: Custom system prompt (uses default if None)
        """
        self.dataset_name = dataset_name
        self.verifier = verifier or NetworkLogsVerifier()
        self.max_examples = max_examples

        self.system_prompt = system_prompt or (
            "You are a network security analyst. Analyze the provided network log entry "
            "and classify it as either 'Malicious' or 'Benign'. Respond with only the "
            "classification label."
        )

        self._dataset: Dataset | None = None
        self._env: vf.SingleTurnEnv | None = None

    def evaluate(self, log_entry: str, model_output: str) -> tuple[float, Mapping[str, Any]]:
        """Evaluate a model's classification of a network log entry.

        Args:
            log_entry: The network log entry that was classified
            model_output: The model's classification response

        Returns:
            tuple: (reward, info) where reward is the RL signal and info contains
                   auxiliary data about the evaluation
        """
        # Extract classification from model output
        predicted_label = self._extract_classification(model_output)

        # Score the prediction
        reward = self.verifier.score(log_entry, predicted_label)
        info = {
            **self.verifier.details(),
            "predicted_label": predicted_label,
            "model_output": model_output,
        }

        return reward, info

    def get_dataset(self) -> Dataset:
        """Get the dataset of network log entries for training/evaluation.

        Returns:
            Dataset containing network log entries with ground truth labels
        """
        if self._dataset is None:
            try:
                logger.info(f"Loading dataset: {self.dataset_name}")
                raw_dataset = load_dataset(self.dataset_name, split="train")
                self._dataset = self._transform_dataset(raw_dataset)
                logger.info(f"Loaded {len(self._dataset)} examples")
            except Exception as e:
                logger.warning(f"Failed to load dataset {self.dataset_name}: {e}")
                logger.info("Falling back to synthetic dataset")
                self._dataset = self._create_synthetic_dataset()

        return self._dataset

    def get_verifiers_env(self) -> vf.SingleTurnEnv:
        """Get the underlying Verifiers SingleTurnEnv for RL training.

        Returns:
            vf.SingleTurnEnv: Configured environment ready for RL training
        """
        if self._env is None:
            self._env = self._create_verifiers_env()
        return self._env

    def _create_verifiers_env(self) -> vf.SingleTurnEnv:
        """Create the underlying Verifiers SingleTurnEnv."""
        dataset = self.get_dataset()

        def reward_classification_match(
            prompt: str, completion: str, answer: str, **kwargs
        ) -> float:
            """Reward function for exact classification match."""
            predicted = self._extract_classification(completion)
            actual = answer.strip().lower()
            return 1.0 if predicted.lower() == actual else 0.0

        rubric = vf.Rubric(
            funcs=[reward_classification_match],
            weights=[1.0],
        )

        return vf.SingleTurnEnv(
            dataset=dataset,
            rubric=rubric,
            system_prompt=self.system_prompt,
        )

    def _transform_dataset(self, raw_dataset: Dataset) -> Dataset:
        """Transform raw dataset to SingleTurnEnv format.

        Args:
            raw_dataset: Raw dataset from HuggingFace

        Returns:
            Dataset in format expected by SingleTurnEnv (prompt/answer columns)
        """
        def transform_example(example):
            # Try to extract log and label from various possible column names
            log_text = self._extract_log_text(example)
            label = self._extract_label(example)

            return {
                "prompt": log_text,
                "answer": label,
            }

        transformed = raw_dataset.map(transform_example)

        # Limit to max_examples if specified
        if self.max_examples and len(transformed) > self.max_examples:
            transformed = transformed.select(range(self.max_examples))

        return transformed

    def _extract_log_text(self, example: dict[str, Any]) -> str:
        """Extract log text from dataset example."""
        # Try common column names for log data
        for key in ["log", "message", "text", "content", "data"]:
            if key in example and example[key]:
                return str(example[key])

        # If no specific log column, concatenate all string values
        text_parts = []
        for key, value in example.items():
            if isinstance(value, str) and value.strip():
                text_parts.append(f"{key}: {value}")

        return " | ".join(text_parts) if text_parts else str(example)

    def _extract_label(self, example: dict[str, Any]) -> str:
        """Extract label from dataset example."""
        # Try common column names for labels
        for key in ["label", "class", "classification", "target", "ground_truth"]:
            if key in example:
                value = example[key]
                # Convert numeric labels to text
                if isinstance(value, (int, float)):
                    return "Malicious" if value > 0 else "Benign"
                elif isinstance(value, str):
                    # Normalize string labels
                    value_lower = value.lower()
                    malicious_terms = ["malicious", "attack", "bad", "1"]
                    if any(term in value_lower for term in malicious_terms):
                        return "Malicious"
                    else:
                        return "Benign"

        # Default to benign if no label found
        return "Benign"

    def _create_synthetic_dataset(self) -> Dataset:
        """Create a synthetic dataset for testing purposes."""
        examples = [
            {
                "prompt": (
                    "TCP connection from 10.0.0.5:445 to 192.168.1.10:80, flags [S], "
                    "unusual port scanning pattern detected"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "HTTP GET request from 192.168.1.100 to www.example.com, "
                    "normal web browsing activity"
                ),
                "answer": "Benign"
            },
            {
                "prompt": (
                    "Failed SSH login attempt from 203.0.113.0, "
                    "brute force attack pattern identified"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "DNS query from 192.168.1.50 for mail.company.com, "
                    "standard email resolution"
                ),
                "answer": "Benign"
            },
            {
                "prompt": (
                    "Outbound connection blocked to known malware C&C server "
                    "198.51.100.1:443"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "HTTPS connection to banking.example.com from 192.168.1.25, "
                    "encrypted traffic normal"
                ),
                "answer": "Benign"
            },
            {
                "prompt": (
                    "Multiple failed authentication attempts detected from IP "
                    "203.0.113.5, suspicious activity"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "Regular file transfer via SFTP to backup server 10.0.1.100, "
                    "scheduled maintenance"
                ),
                "answer": "Benign"
            },
            {
                "prompt": (
                    "DDoS attack detected from botnet IPs, "
                    "traffic volume exceeding normal thresholds"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "Email SMTP connection to mail.corporate.com from "
                    "authenticated user, routine communication"
                ),
                "answer": "Benign"
            },
            {
                "prompt": (
                    "SQL injection attempt blocked in web application logs, "
                    "malicious payload detected"
                ),
                "answer": "Malicious"
            },
            {
                "prompt": (
                    "VPN connection established from remote worker 192.168.100.5, "
                    "valid credentials"
                ),
                "answer": "Benign"
            },
        ]

        logger.info(f"Created synthetic dataset with {len(examples)} examples")
        return Dataset.from_list(examples)

    def _extract_classification(self, model_output: str) -> str:
        """Extract classification label from potentially verbose model output.

        Args:
            model_output: The model's raw output text

        Returns:
            str: Extracted classification ("Malicious" or "Benign")
        """
        output_lower = model_output.lower().strip()

        # Look for explicit labels first
        if "malicious" in output_lower:
            return "Malicious"
        elif "benign" in output_lower:
            return "Benign"

        # Look for other indicators of malicious activity
        malicious_indicators = ["attack", "threat", "dangerous", "harmful", "bad", "suspicious"]
        if any(indicator in output_lower for indicator in malicious_indicators):
            return "Malicious"

        # Look for indicators of benign activity
        benign_indicators = ["normal", "safe", "legitimate", "good", "clean"]
        if any(indicator in output_lower for indicator in benign_indicators):
            return "Benign"

        # Fallback: return the first word if it matches expected labels
        words = output_lower.split()
        if words:
            first_word = words[0]
            if first_word in ["malicious", "benign"]:
                return first_word.capitalize()

        # Default fallback - assume benign for safety
        return "Benign"
