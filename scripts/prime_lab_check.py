#!/usr/bin/env python3
"""Prime platform compatibility checks for WP2.5 gating."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def run(cmd: list[str]) -> tuple[bool, str]:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False, "command not found"
    output = (res.stdout or res.stderr).strip()
    return res.returncode == 0, output


def has_subcommand(help_text: str, subcommand: str) -> bool:
    return any(line.strip().startswith(subcommand) for line in help_text.splitlines())


def main() -> int:
    checks: list[CheckResult] = []

    prime_path = shutil.which("prime")
    checks.append(
        CheckResult(
            name="prime_cli_installed",
            ok=prime_path is not None,
            detail=prime_path or "prime executable not found in PATH",
        )
    )

    if prime_path is None:
        print(json.dumps({"compatible": False, "checks": [asdict(c) for c in checks]}, indent=2))
        return 1

    ok, version_output = run(["prime", "--version"])
    checks.append(CheckResult("prime_version", ok=ok, detail=version_output or "unavailable"))

    ok, help_output = run(["prime", "--help"])
    lab_available = ok and has_subcommand(help_output, "lab")
    checks.append(
        CheckResult(
            name="prime_lab_command",
            ok=lab_available,
            detail="lab subcommand available" if lab_available else "lab subcommand unavailable",
        )
    )

    # Fallback primitives expected by WP2.5a
    env_available = ok and has_subcommand(help_output, "env")
    checks.append(
        CheckResult(
            name="prime_env_command",
            ok=env_available,
            detail="env subcommand available" if env_available else "env subcommand unavailable",
        )
    )

    auth_ok, auth_output = run(["prime", "whoami"])
    checks.append(
        CheckResult(
            name="prime_auth",
            ok=auth_ok,
            detail=auth_output or "unable to determine auth state",
        )
    )

    compatible = all(
        c.ok for c in checks if c.name in {"prime_cli_installed", "prime_lab_command", "prime_auth"}
    )

    print(json.dumps({"compatible": compatible, "checks": [asdict(c) for c in checks]}, indent=2))
    return 0 if compatible else 1


if __name__ == "__main__":
    sys.exit(main())
