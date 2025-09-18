"""Configuration primitives for the Security Verifiers toolkit."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from security_verifiers.utils.rollout_logging import RolloutLogger, RolloutLoggingConfig

LOGGING_CONFIG = RolloutLoggingConfig(
    enabled=False,
    weave_enabled=True,
    wandb_enabled=True,
    weave_project="security-verifiers",
    wandb_project="security-verifiers-rl",
    wandb_entity=None,
    default_tags=("security-verifiers",),
)


def build_rollout_logger(overrides: Mapping[str, Any] | None = None) -> RolloutLogger:
    """Return a :class:`RolloutLogger` instance using the shared defaults."""

    config = LOGGING_CONFIG
    if overrides:
        params = asdict(config)
        params.update(dict(overrides))
        config = RolloutLoggingConfig(**params)
    return RolloutLogger(config=config)


__all__ = ["LOGGING_CONFIG", "build_rollout_logger"]
