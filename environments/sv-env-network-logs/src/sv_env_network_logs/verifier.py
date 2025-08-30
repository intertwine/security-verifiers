"""NetworkLogsVerifier implementation for network log anomaly detection."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .interfaces import NetworkLogsVerifier as NetworkLogsVerifierProtocol


class NetworkLogsVerifier(NetworkLogsVerifierProtocol):
    """Verifier for network log anomaly detection using pattern-based classification.

    This verifier uses a combination of regex patterns and heuristics to classify
    network log entries as malicious or benign. It's designed to match the behavior
    expected by the SingleTurnEnv for anomaly detection in network logs.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        """Initialize the network logs verifier.

        Args:
            confidence_threshold: Minimum confidence score to classify as malicious
        """
        self.confidence_threshold = confidence_threshold
        self._last_details: dict[str, Any] = {}

        # Define patterns that typically indicate malicious activity
        self.malicious_patterns = [
            r"port scan",
            r"unusual port scanning",
            r"failed login attempt",
            r"brute force",
            r"malware",
            r"botnet",
            r"ddos",
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
            r"attack",
            r"threat",
            r"vulnerability",
            r"c&c server",
            r"command and control",
            r"payload",
            r"infiltration",
            r"compromise",
        ]

        # Define patterns that typically indicate benign activity
        self.benign_patterns = [
            r"normal",
            r"legitimate",
            r"standard",
            r"routine",
            r"regular",
            r"scheduled",
            r"authenticated",
            r"authorized",
            r"valid credentials",
            r"maintenance",
            r"backup",
            r"update",
        ]

        # Compile patterns for efficiency
        self.malicious_regex = re.compile("|".join(self.malicious_patterns), re.IGNORECASE)
        self.benign_regex = re.compile("|".join(self.benign_patterns), re.IGNORECASE)

    def score(self, log_entry: str, ground_truth: str) -> float:
        """Score classification accuracy for a network log entry.

        Args:
            log_entry: The raw network log entry text
            ground_truth: The expected classification ("Malicious" or "Benign")

        Returns:
            float: 1.0 for correct classification, 0.0 for incorrect
        """
        classification = self.classify(log_entry)

        # Calculate confidence and other metrics
        confidence = self._calculate_confidence(log_entry)
        matched_malicious = self._get_matched_patterns(log_entry, malicious=True)
        matched_benign = self._get_matched_patterns(log_entry, malicious=False)

        # Store details for this classification
        self._last_details = {
            "log_entry": log_entry[:200] + "..." if len(log_entry) > 200 else log_entry,
            "predicted": classification,
            "ground_truth": ground_truth,
            "confidence": confidence,
            "matched_malicious_patterns": matched_malicious,
            "matched_benign_patterns": matched_benign,
            "pattern_count_malicious": len(matched_malicious),
            "pattern_count_benign": len(matched_benign),
        }

        # Binary scoring: 1.0 for exact match, 0.0 for mismatch
        return 1.0 if classification.lower() == ground_truth.lower() else 0.0

    def classify(self, log_entry: str) -> str:
        """Classify a network log entry as malicious or benign.

        Args:
            log_entry: The raw network log entry text

        Returns:
            str: Classification result ("Malicious" or "Benign")
        """
        # Count pattern matches
        malicious_matches = len(self._get_matched_patterns(log_entry, malicious=True))
        benign_matches = len(self._get_matched_patterns(log_entry, malicious=False))

        # Calculate confidence score
        confidence = self._calculate_confidence(log_entry)

        # Store basic details for this classification
        self._last_details = {
            "log_entry": log_entry[:200] + "..." if len(log_entry) > 200 else log_entry,
            "confidence": confidence,
            "matched_malicious_patterns": self._get_matched_patterns(log_entry, malicious=True),
            "matched_benign_patterns": self._get_matched_patterns(log_entry, malicious=False),
            "pattern_count_malicious": malicious_matches,
            "pattern_count_benign": benign_matches,
        }

        # Classification logic:
        # 1. If we have malicious patterns and confidence is above threshold -> Malicious
        # 2. If we have strong benign indicators and no malicious -> Benign
        # 3. If confidence is high and malicious patterns outnumber benign -> Malicious
        # 4. Default to Benign for ambiguous cases

        if malicious_matches > 0 and confidence >= self.confidence_threshold:
            if malicious_matches > benign_matches:
                self._last_details["predicted"] = "Malicious"
                return "Malicious"

        if benign_matches > 0 and malicious_matches == 0:
            self._last_details["predicted"] = "Benign"
            return "Benign"

        if confidence >= 0.8 and malicious_matches > benign_matches:
            self._last_details["predicted"] = "Malicious"
            return "Malicious"

        # Default to benign for safety
        self._last_details["predicted"] = "Benign"
        return "Benign"

    def details(self) -> Mapping[str, Any]:
        """Return auxiliary information from the last verification.

        Returns:
            Mapping containing details like confidence scores, detected patterns,
            and reasoning for the classification decision.
        """
        return self._last_details.copy()

    def _get_matched_patterns(self, log_entry: str, malicious: bool = True) -> list[str]:
        """Get list of patterns that matched in the log entry.

        Args:
            log_entry: The network log entry text
            malicious: If True, return malicious patterns; if False, return benign patterns

        Returns:
            list[str]: List of matched pattern strings
        """
        patterns = self.malicious_patterns if malicious else self.benign_patterns
        matched = []

        for pattern in patterns:
            if re.search(pattern, log_entry, re.IGNORECASE):
                matched.append(pattern)

        return matched

    def _calculate_confidence(self, log_entry: str) -> float:
        """Calculate confidence score based on pattern matches and other factors.

        Args:
            log_entry: The network log entry text

        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        malicious_matches = len(self._get_matched_patterns(log_entry, malicious=True))
        benign_matches = len(self._get_matched_patterns(log_entry, malicious=False))

        # Base confidence on pattern matches
        if malicious_matches == 0 and benign_matches == 0:
            # No patterns matched - low confidence, assume benign
            return 0.3

        if malicious_matches > 0 and benign_matches == 0:
            # Only malicious patterns - high confidence
            return min(0.9, 0.6 + (malicious_matches * 0.1))

        if benign_matches > 0 and malicious_matches == 0:
            # Only benign patterns - high confidence for benign
            return min(0.9, 0.6 + (benign_matches * 0.1))

        # Mixed signals - calculate based on ratio
        total_matches = malicious_matches + benign_matches
        if total_matches > 0:
            malicious_ratio = malicious_matches / total_matches
            # Higher ratio of malicious patterns = higher confidence if classifying as malicious
            # Lower ratio = higher confidence if classifying as benign
            return 0.4 + (0.4 * abs(malicious_ratio - 0.5) * 2)

        return 0.5  # Neutral confidence

    def add_malicious_pattern(self, pattern: str) -> None:
        """Add a new malicious pattern to the verifier.

        Args:
            pattern: Regex pattern to add to malicious patterns list
        """
        if pattern not in self.malicious_patterns:
            self.malicious_patterns.append(pattern)
            # Recompile regex
            self.malicious_regex = re.compile("|".join(self.malicious_patterns), re.IGNORECASE)

    def add_benign_pattern(self, pattern: str) -> None:
        """Add a new benign pattern to the verifier.

        Args:
            pattern: Regex pattern to add to benign patterns list
        """
        if pattern not in self.benign_patterns:
            self.benign_patterns.append(pattern)
            # Recompile regex
            self.benign_regex = re.compile("|".join(self.benign_patterns), re.IGNORECASE)

    def get_pattern_stats(self) -> dict[str, int]:
        """Get statistics about loaded patterns.

        Returns:
            dict: Statistics including pattern counts
        """
        return {
            "malicious_patterns_count": len(self.malicious_patterns),
            "benign_patterns_count": len(self.benign_patterns),
            "total_patterns": len(self.malicious_patterns) + len(self.benign_patterns),
        }
