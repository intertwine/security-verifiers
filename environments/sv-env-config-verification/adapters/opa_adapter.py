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
        "--stdin-input",  # Tell OPA to read input from stdin
    ]
    for p in policy_paths:
        cmd.extend(["--data", str(p)])
    cmd.append(query)  # Query should be last

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
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        if isinstance(exc, FileNotFoundError):
            raise OPAError(f"OPA binary not found: {opa_bin}") from exc
        raise OPAError(exc.stderr.strip() or "opa eval failed") from exc
    try:
        data = json.loads(proc.stdout)
        results = data.get("result", [])

        # OPA returns deny rules as a set, which appears as an object/dict in JSON
        # We need to extract the values from the set
        findings: List[ToolFinding] = []

        if results and "expressions" in results[0]:
            value = results[0]["expressions"][0]["value"]

            # Check if the value contains violations key (test format)
            if isinstance(value, dict) and "violations" in value:
                # Handle test format with violations array
                for item in value["violations"]:
                    if isinstance(item, dict):
                        findings.append(
                            ToolFinding(
                                tool="opa",
                                rule_id=str(item.get("rule_id", "")),
                                severity=str(item.get("severity", "")),
                                message=str(item.get("message", "")),
                                file=item.get("file"),
                                start_line=item.get("line"),
                                end_line=item.get("end_line"),
                                extra=item,
                            )
                        )
            # If value is a dict (set representation), get its values
            elif isinstance(value, dict):
                # For sets, OPA returns the messages as keys
                # We need to query with [x] to get actual values
                # Re-run query to get actual messages
                # Build new command with modified query
                cmd_with_var = [str(opa_bin), "eval", "--format=json", "--stdin-input"]
                for p in policy_paths:
                    cmd_with_var.extend(["--data", str(p)])
                cmd_with_var.append(query + "[x]")
                proc2 = subprocess.run(
                    cmd_with_var,
                    input=input_str,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env=env,
                    check=False,
                )
                if proc2.returncode == 0:
                    data2 = json.loads(proc2.stdout)
                    for result in data2.get("result", []):
                        if "bindings" in result and "x" in result["bindings"]:
                            item = result["bindings"]["x"]
                            if isinstance(item, dict):
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
            elif isinstance(value, list):
                # If it's already a list, process as before
                for item in value:
                    if isinstance(item, dict):
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
    except (
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as exc:  # pragma: no cover - defensive
        raise OPAError("invalid OPA output") from exc
    return findings


__all__ = ["opa_eval", "OPAError"]
