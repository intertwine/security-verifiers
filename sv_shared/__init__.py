"""Shared components for Security Verifiers environments."""

__version__ = "0.3.1"

from .dataset_loader import (
    DEFAULT_E1_HF_REPO,
    DEFAULT_E2_HF_REPO,
    HF_DATASET_MAP,
    DatasetSource,
    load_dataset_with_fallback,
)
from .parsers import JsonClassificationParser, extract_json_from_markdown
from .rewards import (
    reward_accuracy,
    reward_asymmetric_cost,
    reward_calibration,
)
from .rollout_logging import (
    DEFAULT_ROLLOUT_LOGGING_CONFIG,
    RolloutLogger,
    RolloutLoggingConfig,
    RolloutLoggingState,
    build_rollout_logger,
)
from .utils import get_response_text


def initialize_weave_if_enabled() -> bool:
    """Initialize Weave lazily to avoid import-time side effects."""
    from .weave_init import initialize_weave_if_enabled as _initialize_weave_if_enabled

    return _initialize_weave_if_enabled()


__all__ = [
    "DEFAULT_E1_HF_REPO",
    "DEFAULT_E2_HF_REPO",
    "DEFAULT_ROLLOUT_LOGGING_CONFIG",
    "HF_DATASET_MAP",
    "DatasetSource",
    "JsonClassificationParser",
    "RolloutLogger",
    "RolloutLoggingConfig",
    "RolloutLoggingState",
    "build_rollout_logger",
    "extract_json_from_markdown",
    "get_response_text",
    "initialize_weave_if_enabled",
    "load_dataset_with_fallback",
    "reward_accuracy",
    "reward_asymmetric_cost",
    "reward_calibration",
]
