from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ConfigVerificationVerifier(Protocol):
    """Interface for configuration verification verifiers.

    Verifiers implementing this protocol should be able to analyze configuration
    files and identify security misconfigurations or policy violations.
    """

    def score(self, config_text: str, ground_truth: str) -> float:
        """Score configuration analysis accuracy.

        Args:
            config_text: The configuration file content
            ground_truth: The expected analysis result

        Returns:
            float: Score between 0.0 and 1.0, where 1.0 indicates perfect analysis
        """
        ...

    def analyze(self, config_text: str) -> str:
        """Analyze a configuration file for security issues.

        Args:
            config_text: The configuration file content

        Returns:
            str: Analysis result with detected issues or compliance verdict
        """
        ...

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information from the last verification.

        Returns:
            Mapping containing details like detected issues, confidence scores,
            or reasoning for the analysis decision.
        """
        ...


@runtime_checkable
class ConfigVerificationEnvironment(Protocol):
    """Environment interface for configuration verification training.

    This environment wraps verifiers to provide RL training signals for models
    learning to audit security configuration files and identify policy violations.
    """

    def evaluate(self, config_text: str, model_output: str) -> tuple[float, Mapping[str, Any]]:
        """Evaluate a model's analysis of a configuration file.

        Args:
            config_text: The configuration file content that was analyzed
            model_output: The model's analysis response

        Returns:
            tuple: (reward, info) where reward is the RL signal and info contains
                   auxiliary data about the evaluation
        """
        ...

    def get_dataset(self) -> Any:
        """Get the dataset of configuration files for training/evaluation.

        Returns:
            Dataset containing configuration files with known vulnerabilities
        """
        ...


__all__ = ["ConfigVerificationVerifier", "ConfigVerificationEnvironment"]
