"""Tests for the central rollout logging utility."""

from __future__ import annotations

import importlib
import types

import pytest
from security_verifiers.utils import RolloutLogger, RolloutLoggingConfig


@pytest.fixture
def patched_backends(monkeypatch):
    """Provide fake weave and wandb modules for logging tests."""

    weave_calls: list[dict] = []
    wandb_calls: list[dict] = []
    weave_module = types.SimpleNamespace()
    wandb_module = types.SimpleNamespace()

    def weave_init(**kwargs):
        weave_module.init_kwargs = kwargs

    def weave_log(payload):
        weave_calls.append(payload)

    def wandb_init(**kwargs):
        wandb_module.init_kwargs = kwargs
        return "run"

    def wandb_log(payload):
        wandb_calls.append(payload)

    def wandb_finish():
        wandb_module.finished = True

    weave_module.init = weave_init
    weave_module.log = weave_log
    wandb_module.init = wandb_init
    wandb_module.log = wandb_log
    wandb_module.finish = wandb_finish

    original_import = importlib.import_module

    def fake_import(name, package=None):  # noqa: D401 - signature matches importlib
        if name == "weave":
            return weave_module
        if name == "wandb":
            return wandb_module
        return original_import(name, package)

    monkeypatch.setattr("importlib.import_module", fake_import)

    yield weave_module, weave_calls, wandb_module, wandb_calls

    monkeypatch.setattr("importlib", "import_module", original_import)


def test_rollout_logger_streams_payloads(patched_backends):
    """The logger initialises both backends and forwards rollout events."""

    weave_module, weave_calls, wandb_module, wandb_calls = patched_backends

    config = RolloutLoggingConfig(
        enabled=True,
        weave_enabled=True,
        wandb_enabled=True,
        weave_project="security-verifiers",
        wandb_project="security-verifiers-rl",
    )
    logger = RolloutLogger(config=config)

    logger.log_step(
        episode_id="episode-1",
        step_index=0,
        state={"observation": "start"},
        action={"response": "act"},
        reward=0.42,
        info={"threat_level": "medium"},
    )
    logger.log_episode_summary(
        episode_id="episode-1",
        total_reward=1.0,
        length=1,
        metrics={"success_rate": 1.0},
    )
    logger.close()

    assert weave_module.init_kwargs["project"] == "security-verifiers"
    assert wandb_module.init_kwargs["project"] == "security-verifiers-rl"
    assert weave_calls[0]["episode_id"] == "episode-1"
    assert wandb_calls[0]["event"] == "rollout_step"
    assert getattr(wandb_module, "finished", False)


def test_rollout_logger_filters_and_queries(monkeypatch):
    """Step filters prevent remote logging while keeping local buffers accessible."""

    config = RolloutLoggingConfig(
        enabled=True,
        weave_enabled=False,
        wandb_enabled=False,
        step_filter=lambda event: (event.reward or 0.0) < 0.5,
    )
    logger = RolloutLogger(config=config)

    logger.log_step(
        episode_id="episode-2",
        step_index=0,
        state={},
        action={},
        reward=0.75,
    )
    logger.log_step(
        episode_id="episode-2",
        step_index=1,
        state={},
        action={},
        reward=0.25,
        metrics={"policy_change": True},
    )

    dips = logger.find_reward_dips(0.5)
    assert len(dips) == 1
    assert dips[0].step_index == 1
    assert logger.query_events(lambda event: event.metrics.get("policy_change"))
