"""Tests for network logs anomaly detection environment."""

import pytest
from sv_env_network_logs import NetworkLogsEnvironment, NetworkLogsVerifier


def test_network_logs_verifier_malicious_classification():
    """Test that verifier correctly identifies malicious log entries."""
    verifier = NetworkLogsVerifier()

    malicious_log = (
        "TCP connection from 10.0.0.5:445 to 192.168.1.10:80, unusual port scanning pattern detected"
    )
    classification = verifier.classify(malicious_log)

    assert classification == "Malicious"

    # Test scoring
    score = verifier.score(malicious_log, "Malicious")
    assert score == 1.0

    # Check details
    details = verifier.details()
    assert details["predicted"] == "Malicious"
    assert details["ground_truth"] == "Malicious"
    assert len(details["matched_malicious_patterns"]) > 0


def test_network_logs_verifier_benign_classification():
    """Test that verifier correctly identifies benign log entries."""
    verifier = NetworkLogsVerifier()

    benign_log = "HTTP GET request from 192.168.1.100 to www.example.com, normal web browsing activity"
    classification = verifier.classify(benign_log)

    assert classification == "Benign"

    # Test scoring
    score = verifier.score(benign_log, "Benign")
    assert score == 1.0

    # Check details
    details = verifier.details()
    assert details["predicted"] == "Benign"
    assert details["ground_truth"] == "Benign"


def test_network_logs_verifier_incorrect_classification():
    """Test scoring when classification is incorrect."""
    verifier = NetworkLogsVerifier()

    malicious_log = "Failed SSH login attempt from 203.0.113.0, brute force attack detected"

    # Score against wrong ground truth
    score = verifier.score(malicious_log, "Benign")
    assert score == 0.0


def test_network_logs_environment_initialization():
    """Test that environment initializes correctly."""
    env = NetworkLogsEnvironment()

    assert env.dataset_name == "19kmunz/iot-23-preprocessed-minimumcolumns"
    assert env.max_examples == 1000
    assert env.verifier is not None
    assert env.system_prompt is not None


def test_network_logs_environment_synthetic_dataset():
    """Test that synthetic dataset is created correctly."""
    env = NetworkLogsEnvironment()

    # Force use of synthetic dataset
    dataset = env._create_synthetic_dataset()

    assert len(dataset) > 0

    # Check dataset structure
    example = dataset[0]
    assert "prompt" in example
    assert "answer" in example
    assert example["answer"] in ["Malicious", "Benign"]


def test_network_logs_environment_evaluation():
    """Test environment evaluation functionality."""
    env = NetworkLogsEnvironment()

    log_entry = "DDoS attack detected from botnet IPs, traffic volume exceeding thresholds"
    model_output = "Malicious"

    reward, info = env.evaluate(log_entry, model_output)

    assert isinstance(reward, float)
    assert 0.0 <= reward <= 1.0
    assert isinstance(info, dict)
    assert "predicted_label" in info
    assert "model_output" in info


def test_network_logs_environment_extract_classification():
    """Test classification extraction from verbose model outputs."""
    env = NetworkLogsEnvironment()

    # Test exact match
    assert env._extract_classification("Malicious") == "Malicious"
    assert env._extract_classification("Benign") == "Benign"

    # Test within sentence
    assert env._extract_classification("This log entry is malicious.") == "Malicious"
    assert env._extract_classification("The traffic appears benign.") == "Benign"

    # Test with other indicators
    assert env._extract_classification("This is an attack!") == "Malicious"
    assert env._extract_classification("Normal traffic detected.") == "Benign"

    # Test fallback
    assert env._extract_classification("Unknown response") == "Benign"


def test_verifier_pattern_management():
    """Test adding custom patterns to verifier."""
    verifier = NetworkLogsVerifier()

    initial_malicious_count = len(verifier.malicious_patterns)
    initial_benign_count = len(verifier.benign_patterns)

    # Add malicious pattern
    verifier.add_malicious_pattern("custom_malware")
    assert len(verifier.malicious_patterns) == initial_malicious_count + 1

    # Add benign pattern
    verifier.add_benign_pattern("routine_backup")
    assert len(verifier.benign_patterns) == initial_benign_count + 1

    # Test duplicate addition (should not increase count)
    verifier.add_malicious_pattern("custom_malware")
    assert len(verifier.malicious_patterns) == initial_malicious_count + 1


def test_verifier_confidence_calculation():
    """Test confidence scoring mechanism."""
    verifier = NetworkLogsVerifier()

    # High confidence malicious (multiple indicators)
    malicious_log = "Malware detected, suspicious botnet activity, unauthorized access, exploit detected"
    verifier.classify(malicious_log)  # Trigger classification to set details
    details = verifier.details()
    assert details["confidence"] > 0.6

    # High confidence benign (clear indicators)
    benign_log = "Normal HTTPS connection, authenticated user, routine maintenance, scheduled backup"
    verifier.classify(benign_log)
    details = verifier.details()
    assert details["confidence"] > 0.6

    # Low confidence (no clear indicators)
    ambiguous_log = "Network connection established"
    verifier.classify(ambiguous_log)
    details = verifier.details()
    assert details["confidence"] <= 0.5


def test_verifier_pattern_stats():
    """Test pattern statistics functionality."""
    verifier = NetworkLogsVerifier()

    stats = verifier.get_pattern_stats()

    assert "malicious_patterns_count" in stats
    assert "benign_patterns_count" in stats
    assert "total_patterns" in stats
    expected_total = stats["malicious_patterns_count"] + stats["benign_patterns_count"]
    assert stats["total_patterns"] == expected_total
    assert stats["malicious_patterns_count"] > 0
    assert stats["benign_patterns_count"] > 0


def test_environment_dataset_transformation():
    """Test dataset transformation logic."""
    env = NetworkLogsEnvironment()

    # Test log text extraction
    example1 = {"log": "Test log message", "label": "malicious"}
    log_text = env._extract_log_text(example1)
    assert log_text == "Test log message"

    # Test label extraction
    label = env._extract_label(example1)
    assert label == "Malicious"

    # Test numeric label
    example2 = {"data": "Some data", "target": 1}
    label = env._extract_label(example2)
    assert label == "Malicious"

    example3 = {"data": "Some data", "target": 0}
    label = env._extract_label(example3)
    assert label == "Benign"


@pytest.fixture
def sample_environment():
    """Fixture providing a sample environment for testing."""
    return NetworkLogsEnvironment(max_examples=10)


def test_environment_verifiers_integration(sample_environment):
    """Test integration with Verifiers framework."""
    env = sample_environment

    # Get the underlying Verifiers environment
    verifiers_env = env.get_verifiers_env()

    assert verifiers_env is not None
    assert hasattr(verifiers_env, "dataset")
    assert hasattr(verifiers_env, "rubric")


def test_load_environment_function():
    """Test the load_environment function."""
    from sv_env_network_logs import load_environment

    env = load_environment()
    assert isinstance(env, NetworkLogsEnvironment)
    assert env.verifier is not None
