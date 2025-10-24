"""Shared components for Security Verifiers environments."""

__version__ = "0.1.0"

from .dataset_loader import (
    DEFAULT_E1_HF_REPO,
    DEFAULT_E2_HF_REPO,
    HF_DATASET_MAP,
    DatasetSource,
    load_dataset_with_fallback,
)
from .parsers import JsonClassificationParser
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
from .weave_init import initialize_weave_if_enabled

__all__ = [
    "JsonClassificationParser",
    "reward_accuracy",
    "reward_calibration",
    "reward_asymmetric_cost",
    "get_response_text",
    "RolloutLogger",
    "RolloutLoggingConfig",
    "RolloutLoggingState",
    "DEFAULT_ROLLOUT_LOGGING_CONFIG",
    "build_rollout_logger",
    "initialize_weave_if_enabled",
    "DatasetSource",
    "load_dataset_with_fallback",
    "HF_DATASET_MAP",
    "DEFAULT_E1_HF_REPO",
    "DEFAULT_E2_HF_REPO",
]
