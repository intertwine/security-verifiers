#!/usr/bin/env python3
"""Prime CLI v0.5+ compatibility checks for hosted RL training (WP3a/WP3b)."""

from __future__ import annotations

import json
import re
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
    """Check if a subcommand appears in CLI help output."""
    for line in help_text.splitlines():
        # Strip whitespace and Rich box-drawing characters (│, ╭, ╰, etc.)
        cleaned = line.strip().lstrip("│╭╰╮╯─┃┏┗┓┛━ ")
        if cleaned.startswith(subcommand):
            return True
    return False


def parse_version(version_str: str) -> tuple[int, ...] | None:
    """Extract semver tuple from version string like 'prime 0.5.41' or '0.5.41'."""
    match = re.search(r"(\d+\.\d+\.\d+)", version_str)
    if match:
        return tuple(int(x) for x in match.group(1).split("."))
    return None


def main() -> int:
    checks: list[CheckResult] = []

    # 1) Check prime CLI is installed
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

    # 2) Check prime --version and verify >= 0.5.0
    ok, version_output = run(["prime", "--version"])
    version_tuple = parse_version(version_output) if ok else None
    version_ok = version_tuple is not None and version_tuple >= (0, 5, 0)
    checks.append(
        CheckResult(
            name="prime_version",
            ok=version_ok,
            detail=version_output if ok else "unable to determine version",
        )
    )

    # 3) Check prime whoami for auth status
    auth_ok, auth_output = run(["prime", "whoami"])
    checks.append(
        CheckResult(
            name="prime_auth",
            ok=auth_ok,
            detail=auth_output or "unable to determine auth state",
        )
    )

    # Extract team slug from whoami output if available
    team_slug = None
    if auth_ok and auth_output:
        # Try to extract team/org info from whoami output
        for line in auth_output.splitlines():
            lower = line.lower()
            if "team" in lower or "org" in lower or "slug" in lower:
                team_slug = line.strip()
                break
        if team_slug is None:
            team_slug = auth_output.splitlines()[0].strip()

    # 4) Check prime rl subcommand availability
    ok, help_output = run(["prime", "--help"])
    rl_available = ok and has_subcommand(help_output, "rl")
    checks.append(
        CheckResult(
            name="prime_rl_command",
            ok=rl_available,
            detail="rl subcommand available" if rl_available else "rl subcommand unavailable",
        )
    )

    # 5) Check prime env subcommand availability
    env_available = ok and has_subcommand(help_output, "env")
    checks.append(
        CheckResult(
            name="prime_env_command",
            ok=env_available,
            detail="env subcommand available" if env_available else "env subcommand unavailable",
        )
    )

    compatible = all(
        c.ok
        for c in checks
        if c.name in {"prime_cli_installed", "prime_version", "prime_rl_command", "prime_auth"}
    )

    result = {
        "compatible": compatible,
        "checks": [asdict(c) for c in checks],
    }
    if team_slug:
        result["team_slug"] = team_slug

    print(json.dumps(result, indent=2))
    return 0 if compatible else 1


if __name__ == "__main__":
    sys.exit(main())
