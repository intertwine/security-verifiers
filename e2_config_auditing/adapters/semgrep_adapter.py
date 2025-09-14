from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence

from .types import ToolFinding


class SemgrepError(RuntimeError):
    """Raised when semgrep fails or emits invalid output."""


def semgrep_scan(
    targets: Sequence[str | Path],
    rules: Sequence[str | Path] | str = ("p/ci",),
    semgrep_bin: str | Path = "semgrep",
    timeout_s: int = 60,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    env: Dict[str, str] | None = None,
) -> List[ToolFinding]:
    """Run ``semgrep`` and return findings."""

    cmd = [str(semgrep_bin), "--json", "--quiet"]
    if isinstance(rules, (list, tuple)):
        for r in rules:
            cmd.extend(["--rules", str(r)])
    else:
        cmd.extend(["--rules", str(rules)])
    if include:
        for inc in include:
            cmd.extend(["--include", inc])
    if exclude:
        for exc in exclude:
            cmd.extend(["--exclude", exc])
    cmd.extend([str(t) for t in targets])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SemgrepError(exc.stderr.strip() or "semgrep failed") from exc
    try:
        data = json.loads(proc.stdout)
        findings_json = data.get("results", [])
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SemgrepError("invalid semgrep output") from exc

    findings: List[ToolFinding] = []
    for item in findings_json:
        findings.append(
            ToolFinding(
                tool="semgrep",
                rule_id=str(item.get("check_id")),
                severity=str(item.get("extra", {}).get("severity", "")),
                message=str(item.get("extra", {}).get("message", "")),
                file=item.get("path"),
                start_line=item.get("start", {}).get("line"),
                end_line=item.get("end", {}).get("line"),
                extra=item,
            )
        )
    return findings


__all__ = ["semgrep_scan", "SemgrepError"]
