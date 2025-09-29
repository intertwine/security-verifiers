"""Central rollout logging utilities shared across Security Verifiers.

IMPORTANT: This module provides supplementary logging capabilities for Security
Verifiers environments. The primary logging mechanism is Weave's automatic
tracing, which is enabled by importing `sv_shared.weave_init` before importing
the `verifiers` library.

The RolloutLogger class in this module offers additional custom logging features:
- Fine-grained control over what gets logged
- Local event buffering for analysis
- Custom filters and metrics
- Integration with both Weave and Weights & Biases

Use RolloutLogger when you need:
- Custom event filtering
- Local event storage and querying
- Additional metrics beyond Weave's automatic tracing
- Manual control over logging granularity

For most use cases, Weave's automatic tracing (via weave_init) is sufficient
and preferred for its simplicity and comprehensive coverage.
"""

from __future__ import annotations

import importlib
import logging
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, List, Mapping, Sequence

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RolloutLoggingConfig:
    """Configuration for :class:`RolloutLogger`.

    Attributes:
        enabled: Globally enable/disable logging.
        weave_enabled: Whether Weave tracing should be initialised.
        wandb_enabled: Whether Weights & Biases logging should be initialised.
        weave_project: Optional Weave project name.
        weave_config: Additional keyword arguments passed to the Weave ``init`` call.
        wandb_project: Optional Weights & Biases project name.
        wandb_entity: Optional Weights & Biases entity/organisation name.
        wandb_run_name: Optional run name for Weights & Biases sessions.
        wandb_config: Additional configuration dictionary forwarded to ``wandb.init``.
        default_tags: Tags attached to every logged event.
        step_filter: Optional predicate controlling whether individual steps are
            forwarded to the remote backends. Returning ``False`` keeps the event in
            the local buffer but avoids network calls.
        episode_filter: Optional predicate controlling whether episode summaries are
            forwarded to the remote backends.
    """

    enabled: bool = True
    weave_enabled: bool = True
    wandb_enabled: bool = True
    weave_project: str | None = None
    weave_config: Mapping[str, Any] = field(default_factory=dict)
    wandb_project: str | None = None
    wandb_entity: str | None = None
    wandb_run_name: str | None = None
    wandb_config: Mapping[str, Any] = field(default_factory=dict)
    default_tags: Sequence[str] = field(default_factory=tuple)
    step_filter: Callable[["RolloutLoggingState"], bool] | None = None
    episode_filter: Callable[[Mapping[str, Any]], bool] | None = None


def dataclass_replace(config: RolloutLoggingConfig, **kwargs: Any) -> RolloutLoggingConfig:
    """Return a copy of ``config`` replacing the provided fields."""

    params = asdict(config)
    params.update(kwargs)
    return RolloutLoggingConfig(**params)


@dataclass(slots=True)
class RolloutLoggingState:
    """Local representation of a single step emitted by the logger."""

    episode_id: str
    step_index: int
    state: Mapping[str, Any] | None
    action: Mapping[str, Any] | None
    reward: float | None
    info: Mapping[str, Any] | None
    metrics: Mapping[str, Any] | None = None


class RolloutLogger:
    """Supplementary logging utility for custom rollout tracking.

    IMPORTANT: This is a supplementary logging mechanism. The primary logging
    for Security Verifiers environments is handled by Weave's automatic tracing,
    which is enabled by importing `sv_shared.weave_init` before importing verifiers.

    This class provides additional features beyond automatic tracing:
    - Custom event filtering and transformation
    - Local event buffering for offline analysis
    - Query capabilities for finding specific events (e.g., reward dips)
    - Fine-grained control over what gets sent to remote backends

    The class lazily imports both Weave and Weights & Biases to avoid introducing
    heavy dependencies when logging is disabled. All logging calls are threadsafe
    and store a local buffer so downstream applications can query for key events
    such as reward dips or policy regressions.

    Use this logger when you need custom logging logic that goes beyond
    what Weave's automatic tracing provides.
    """

    def __init__(self, config: RolloutLoggingConfig | None = None) -> None:
        self._config = config or RolloutLoggingConfig()
        self._lock = threading.Lock()
        self._events: List[RolloutLoggingState] = []
        self._weave_module: Any | None = None
        self._weave_log_fn: Callable[[Mapping[str, Any]], Any] | None = None
        self._wandb_module: Any | None = None
        self._wandb_run: Any | None = None
        self._enabled = self._config.enabled

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        """Return whether logging is globally enabled."""

        return self._enabled

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def initialize_weave(self) -> None:
        """Initialise the Weave backend if required."""

        if not self._enabled or not self._config.weave_enabled or self._weave_module:
            return

        try:
            module = importlib.import_module("weave")
        except ImportError:  # pragma: no cover - depends on optional dependency
            _LOGGER.debug("Weave is not installed; rollout tracing will be skipped.")
            self._config = dataclass_replace(self._config, weave_enabled=False)
            return

        init_kwargs: dict[str, Any] = {}
        if self._config.weave_project:
            init_kwargs["project"] = self._config.weave_project
        init_kwargs.update(dict(self._config.weave_config))

        init_fn = getattr(module, "init", None)
        if callable(init_fn):
            init_fn(**init_kwargs)
        else:
            trace_module = getattr(module, "trace", None)
            trace_init = getattr(trace_module, "init", None) if trace_module else None
            if callable(trace_init):
                trace_init(**init_kwargs)
                trace_log = getattr(trace_module, "log", None)
                if callable(trace_log):
                    self._weave_log_fn = trace_log
            else:
                _LOGGER.debug("Weave module does not expose an init function.")

        if self._weave_log_fn is None:
            log_fn = getattr(module, "log", None)
            if callable(log_fn):
                self._weave_log_fn = log_fn

        self._weave_module = module

    def initialize_wandb(self) -> None:
        """Initialise the Weights & Biases backend if required."""

        if not self._enabled or not self._config.wandb_enabled or self._wandb_module:
            return

        try:
            module = importlib.import_module("wandb")
        except ImportError:  # pragma: no cover - depends on optional dependency
            _LOGGER.debug("Weights & Biases is not installed; rollout logging disabled.")
            self._config = dataclass_replace(self._config, wandb_enabled=False)
            return

        init_kwargs: dict[str, Any] = {}
        if self._config.wandb_project:
            init_kwargs["project"] = self._config.wandb_project
        if self._config.wandb_entity:
            init_kwargs["entity"] = self._config.wandb_entity
        if self._config.wandb_run_name:
            init_kwargs["name"] = self._config.wandb_run_name
        if self._config.wandb_config:
            init_kwargs["config"] = dict(self._config.wandb_config)

        self._wandb_run = module.init(**init_kwargs) if hasattr(module, "init") else None
        self._wandb_module = module

    # ------------------------------------------------------------------
    # Logging entry points
    # ------------------------------------------------------------------
    def log_environment_init(
        self,
        *,
        environment_name: str,
        dataset_name: str | None,
        total_examples: int | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Log details about the loaded environment and dataset."""

        if not self._enabled:
            return

        payload: dict[str, Any] = {
            "event": "environment_init",
            "environment": environment_name,
            "dataset": dataset_name,
            "total_examples": total_examples,
            "metadata": dict(metadata or {}),
            "tags": list(self._config.default_tags),
        }
        self._log_to_backends(payload)

    def log_step(
        self,
        *,
        episode_id: str,
        step_index: int,
        state: Mapping[str, Any] | None,
        action: Mapping[str, Any] | None,
        reward: float | None,
        info: Mapping[str, Any] | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> None:
        """Log a single step of an environment rollout."""

        if not self._enabled:
            return

        event = RolloutLoggingState(
            episode_id=episode_id,
            step_index=step_index,
            state=state,
            action=action,
            reward=reward,
            info=info,
            metrics=metrics,
        )

        with self._lock:
            self._events.append(event)

        if self._config.step_filter and not self._config.step_filter(event):
            return

        payload: dict[str, Any] = {
            "event": "rollout_step",
            "episode_id": episode_id,
            "step": step_index,
            "state": dict(state or {}),
            "action": dict(action or {}),
            "reward": reward,
            "info": dict(info or {}),
            "metrics": dict(metrics or {}),
            "tags": list(self._config.default_tags),
        }
        self._log_to_backends(payload)

    def log_episode_summary(
        self,
        *,
        episode_id: str,
        total_reward: float | None,
        length: int,
        metrics: Mapping[str, Any] | None = None,
    ) -> None:
        """Log an episode level summary."""

        if not self._enabled:
            return

        summary: dict[str, Any] = {
            "event": "episode_summary",
            "episode_id": episode_id,
            "total_reward": total_reward,
            "length": length,
            "metrics": dict(metrics or {}),
            "tags": list(self._config.default_tags),
        }

        if self._config.episode_filter and not self._config.episode_filter(summary):
            return

        self._log_to_backends(summary)

    def log_metrics(self, metrics: Mapping[str, Any], step: int | None = None) -> None:
        """Log aggregated training or evaluation metrics."""

        if not self._enabled:
            return

        payload = {
            "event": "metrics",
            "step": step,
            "metrics": dict(metrics),
            "tags": list(self._config.default_tags),
        }
        self._log_to_backends(payload)

    def query_events(
        self,
        predicate: Callable[[RolloutLoggingState], bool],
    ) -> list[RolloutLoggingState]:
        """Return locally buffered events matching ``predicate``."""

        with self._lock:
            return [event for event in self._events if predicate(event)]

    def find_reward_dips(self, threshold: float) -> list[RolloutLoggingState]:
        """Return all logged steps where reward fell below ``threshold``."""

        return self.query_events(lambda event: (event.reward or 0.0) < threshold)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Flush and close remote logging sessions."""

        if not self._enabled:
            return

        if self._wandb_module and hasattr(self._wandb_module, "finish"):
            self._wandb_module.finish()
        self._wandb_module = None
        self._wandb_run = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log_to_backends(self, payload: Mapping[str, Any]) -> None:
        """Ensure both backends receive the given payload."""

        self.initialize_weave()
        self.initialize_wandb()

        if self._weave_log_fn:
            try:
                self._weave_log_fn(payload)
            except Exception as exc:  # pragma: no cover - defensive logging
                _LOGGER.debug("Failed to log payload to Weave: %s", exc)

        if self._wandb_module and hasattr(self._wandb_module, "log"):
            try:
                self._wandb_module.log(dict(payload))
            except Exception as exc:  # pragma: no cover - defensive logging
                _LOGGER.debug("Failed to log payload to wandb: %s", exc)


DEFAULT_ROLLOUT_LOGGING_CONFIG = RolloutLoggingConfig(
    enabled=False,
    weave_enabled=True,
    wandb_enabled=True,
    weave_project="security-verifiers",
    wandb_project="security-verifiers-rl",
    wandb_entity=None,
    default_tags=("security-verifiers",),
)


def build_rollout_logger(
    overrides: Mapping[str, Any] | None = None,
) -> RolloutLogger:
    """Create a :class:`RolloutLogger` using the shared defaults.

    Args:
        overrides: Optional mapping of configuration overrides. When provided the
            values replace the defaults defined in :data:`DEFAULT_ROLLOUT_LOGGING_CONFIG`.

    Returns:
        A configured :class:`RolloutLogger` instance ready for injection into
        environments or training loops.
    """

    config = DEFAULT_ROLLOUT_LOGGING_CONFIG
    if overrides:
        config = dataclass_replace(config, **dict(overrides))
    return RolloutLogger(config=config)


__all__ = [
    "RolloutLogger",
    "RolloutLoggingConfig",
    "RolloutLoggingState",
    "DEFAULT_ROLLOUT_LOGGING_CONFIG",
    "build_rollout_logger",
]
