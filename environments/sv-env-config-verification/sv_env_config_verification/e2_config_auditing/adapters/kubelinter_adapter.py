"""Adapter for KubeLinter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence

from .types import ToolFinding


class KubeLinterError(RuntimeError):
    """Raised when KubeLinter fails or emits invalid output."""


def kubelinter_lint(
    k8s_paths: Sequence[str | Path],
    kube_linter_bin: str | Path = "kube-linter",
    timeout_s: int = 30,
    config_yaml: str | Path | None = None,
    env: Dict[str, str] | None = None,
) -> List[ToolFinding]:
    """Run ``kube-linter lint`` and return findings."""

    cmd = [str(kube_linter_bin), "lint", "--format", "json"]
    if config_yaml:
        cmd.extend(["--config", str(config_yaml)])
    cmd.extend([str(p) for p in k8s_paths])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=env,
        check=False,
    )
    # kube-linter exits with code 1 when violations are found, which is expected
    # Only treat as error if we can't parse JSON output or there's a real error
    try:
        data = json.loads(proc.stdout)
        findings_json = data.get("Reports", [])
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        # If JSON parsing fails, check if it's a real error
        if proc.returncode != 0 and not proc.stdout.strip():
            raise KubeLinterError(proc.stderr.strip() or "kube-linter failed") from exc
        raise KubeLinterError("invalid kube-linter output") from exc

    findings: List[ToolFinding] = []
    for item in findings_json:
        diagnostic = item.get("Diagnostic", {})
        findings.append(
            ToolFinding(
                tool="kube-linter",
                rule_id=str(item.get("Check", "")),
                severity="",  # kube-linter doesn't provide severity in this format
                message=str(diagnostic.get("Message", "")),
                file=item.get("Object", {}).get("Metadata", {}).get("FilePath"),
                start_line=None,  # Not provided in this format
                end_line=None,  # Not provided in this format
                extra=item,
            )
        )
    return findings


__all__ = ["kubelinter_lint", "KubeLinterError"]
