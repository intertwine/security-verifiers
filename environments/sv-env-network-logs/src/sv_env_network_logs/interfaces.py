from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class NetworkLogsVerifier(Protocol):
    """Interface for network log anomaly detection verifiers.

    Verifiers implementing this protocol should be able to analyze network log entries
    and determine if they represent malicious or benign activity.
    """

    def score(self, log_entry: str, ground_truth: str) -> float:
        """Score a network log entry classification.

        Args:
            log_entry: The raw network log entry text
            ground_truth: The expected classification ("Malicious" or "Benign")

        Returns:
            float: Score between 0.0 and 1.0, where 1.0 indicates perfect classification
        """
        ...

    def classify(self, log_entry: str) -> str:
        """Classify a network log entry as malicious or benign.

        Args:
            log_entry: The raw network log entry text

        Returns:
            str: Classification result ("Malicious" or "Benign")
        """
        ...

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information from the last verification.

        Returns:
            Mapping containing details like confidence scores, detected patterns,
            or reasoning for the classification decision.
        """
        ...


@runtime_checkable
class NetworkLogsEnvironment(Protocol):
    """Environment interface for network logs anomaly detection training.

    This environment wraps verifiers to provide RL training signals for models
    learning to classify network logs as malicious or benign.
    """

    def evaluate(self, log_entry: str, model_output: str) -> tuple[float, Mapping[str, Any]]:
        """Evaluate a model's classification of a network log entry.

        Args:
            log_entry: The network log entry that was classified
            model_output: The model's classification response

        Returns:
            tuple: (reward, info) where reward is the RL signal and info contains
                   auxiliary data about the evaluation
        """
        ...

    def get_dataset(self) -> Any:
        """Get the dataset of network log entries for training/evaluation.

        Returns:
            Dataset containing network log entries with ground truth labels
        """
        ...


__all__ = ["NetworkLogsVerifier", "NetworkLogsEnvironment"]
