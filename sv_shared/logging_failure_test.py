"""Fallback diagnostics must preserve outcomes without logging error payloads."""

import logging
import sys
from types import SimpleNamespace

import pytest

from sv_shared import tool_runner, weave_init
from sv_shared.rollout_logging import RolloutLogger

PAYLOAD = "example-error-payload-that-must-not-be-logged"


def fail(*args, **kwargs):
    raise RuntimeError(PAYLOAD)


@pytest.fixture(autouse=True)
def capture_diagnostics(monkeypatch, caplog):
    logger = logging.getLogger("sv_shared.failure_diagnostic_fixture")
    monkeypatch.setattr(logger, "level", logging.ERROR)
    monkeypatch.setattr(logger, "disabled", False)
    monkeypatch.setattr(logger, "propagate", False)
    monkeypatch.setattr(logger, "filters", [])
    monkeypatch.setattr(logger, "handlers", [caplog.handler])
    for function in (
        tool_runner._version_for,
        RolloutLogger._log_to_backends,
        weave_init.initialize_weave_if_enabled,
    ):
        monkeypatch.setitem(function.__globals__, "_LOGGER", logger)


def test_version_probe_failures_remain_nonfatal_and_visible(monkeypatch, caplog):
    monkeypatch.setattr(tool_runner.shutil, "which", lambda _: "/fixture/tool")
    monkeypatch.setattr(tool_runner.subprocess, "run", fail)
    with caplog.at_level(logging.ERROR):
        assert tool_runner._version_for(["fixture-tool"]) is None
    assert len(caplog.records) == 3
    assert "RuntimeError" in caplog.text
    assert PAYLOAD not in caplog.text


def test_backend_failures_do_not_interrupt_other_backends(monkeypatch, caplog):
    logger = RolloutLogger()
    monkeypatch.setattr(logger, "initialize_weave", lambda: None)
    monkeypatch.setattr(logger, "initialize_wandb", lambda: None)
    logger._weave_log_fn = fail
    logger._wandb_module = SimpleNamespace(log=fail)
    with caplog.at_level(logging.ERROR):
        logger._log_to_backends({"fixture": "retained-observation"})
    assert len(caplog.records) == 2
    assert PAYLOAD not in caplog.text
    assert "retained-observation" not in caplog.text


@pytest.mark.parametrize("stage", ["client", "init"])
def test_weave_failures_preserve_disabled_or_failed_init_result(monkeypatch, caplog, stage):
    monkeypatch.setattr(weave_init, "_INITIALIZED", False)
    monkeypatch.setenv("WEAVE_DISABLED", "false")
    monkeypatch.setenv("WEAVE_AUTO_INIT", "false" if stage == "client" else "true")
    fake = SimpleNamespace(get_client=fail if stage == "client" else lambda: None, init=fail)
    monkeypatch.setitem(sys.modules, "weave", fake)
    with caplog.at_level(logging.ERROR):
        assert weave_init.initialize_weave_if_enabled() is False
    assert "RuntimeError" in caplog.text
    assert PAYLOAD not in caplog.text
