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
    if proc.returncode != 0:
        raise KubeLinterError(proc.stderr.strip() or "kube-linter failed")
    try:
        data = json.loads(proc.stdout)
        findings_json = data.get("reports", [])
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise KubeLinterError("invalid kube-linter output") from exc

    findings: List[ToolFinding] = []
    for item in findings_json:
        findings.append(
            ToolFinding(
                tool="kube-linter",
                rule_id=str(item.get("check")),
                severity=str(item.get("severity", "")),
                message=str(item.get("message", "")),
                file=item.get("kubeObject", {}).get("file"),
                start_line=item.get("kubeObject", {}).get("line"),
                end_line=item.get("kubeObject", {}).get("column"),
                extra=item,
            )
        )
    return findings


__all__ = ["kubelinter_lint", "KubeLinterError"]
