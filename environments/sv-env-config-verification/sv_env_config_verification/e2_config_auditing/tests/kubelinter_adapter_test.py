"""Tests for kubelinter adapter."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from sv_env_config_verification.e2_config_auditing.adapters import kubelinter_adapter


def test_kubelinter_end_line(monkeypatch: Any) -> None:
    """Test kubelinter adapter end line."""
    dummy_output = json.dumps(
        {
            "Reports": [
                {
                    "Check": "run-as-non-root",
                    "Diagnostic": {
                        "Message": "msg",
                    },
                    "Object": {
                        "Metadata": {
                            "FilePath": "f.yaml",
                        },
                    },
                }
            ]
        }
    )

    # pylint: disable=unused-argument
    def fake_run(
        cmd: Any,
        capture_output: bool,
        text: bool,
        timeout: int,
        env: Any,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout=dummy_output, stderr="")

    monkeypatch.setattr(kubelinter_adapter.subprocess, "run", fake_run)

    findings = kubelinter_adapter.kubelinter_lint(["f.yaml"])
    assert len(findings) == 1
    assert findings[0].rule_id == "run-as-non-root"
