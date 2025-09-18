from __future__ import annotations

import json
import subprocess
from typing import Any

from sv_env_config_verification.e2_config_auditing.adapters import kubelinter_adapter


def test_kubelinter_end_line(monkeypatch: Any) -> None:
    dummy_output = json.dumps(
        {
            "reports": [
                {
                    "check": "run-as-non-root",
                    "severity": "Error",
                    "message": "msg",
                    "kubeObject": {
                        "file": "f.yaml",
                        "line": 1,
                        "column": 2,
                        "endLine": 3,
                    },
                }
            ]
        }
    )

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
    assert findings[0].end_line == 3
