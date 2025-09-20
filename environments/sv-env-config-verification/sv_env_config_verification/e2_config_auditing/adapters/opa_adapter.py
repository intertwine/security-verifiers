"""Adapter for OPA."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .types import ToolFinding


class OPAError(RuntimeError):
    """Raised when the OPA CLI returns an error or unexpected output."""


def opa_eval(
    input_data: str | Dict[str, Any],
    policy_paths: Sequence[str | Path],
    query: str = "data.security.deny",
    opa_bin: str | Path = "opa",
    timeout_s: int = 15,
    env: Dict[str, str] | None = None,
) -> List[ToolFinding]:
    """Run ``opa eval`` and return findings.

    Parameters are defined in the project canvas. The function expects the
    given query to evaluate to a list of objects with ``id``, ``message`` and
    ``severity`` fields.
    """

    input_str = input_data if isinstance(input_data, str) else json.dumps(input_data)
    cmd = [
        str(opa_bin),
        "eval",
        "--format=json",
        query,
    ]
    for p in policy_paths:
        cmd.extend(["--data", str(p)])

    try:
        proc = subprocess.run(
            cmd,
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise OPAError(exc.stderr.strip() or "opa eval failed") from exc
    try:
        data = json.loads(proc.stdout)
        results = data.get("result", [])
        if results and "expressions" in results[0]:
            value = results[0]["expressions"][0]["value"]
        else:
            value = []
    except (
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as exc:  # pragma: no cover - defensive
        raise OPAError("invalid OPA output") from exc

    findings: List[ToolFinding] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        findings.append(
            ToolFinding(
                tool="opa",
                rule_id=str(item.get("id", "")),
                severity=str(item.get("severity", "")),
                message=str(item.get("message", "")),
                file=item.get("file"),
                start_line=item.get("line"),
                end_line=item.get("end_line"),
                extra=item,
            )
        )
    return findings


__all__ = ["opa_eval", "OPAError"]
