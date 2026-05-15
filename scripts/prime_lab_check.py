#!/usr/bin/env python3
"""Prime CLI compatibility checks for hosted training and evaluation."""

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

    # 2) Check prime --version and verify >= 0.6.2. Prime 0.6.2+ has the
    # `prime train`/`prime eval run` surface used by the hosted workflow.
    ok, version_output = run(["prime", "--version"])
    version_tuple = parse_version(version_output) if ok else None
    version_ok = version_tuple is not None and version_tuple >= (0, 6, 2)
    checks.append(
        CheckResult(
            name="prime_version",
            ok=version_ok,
            detail=version_output if ok else "unable to determine version",
        )
    )

    # 3) Check prime whoami for auth status
    auth_ok, auth_output = run(["prime", "whoami", "--plain"])
    checks.append(
        CheckResult(
            name="prime_auth",
            ok=auth_ok,
            detail="authenticated" if auth_ok else auth_output or "unable to determine auth state",
        )
    )

    # Extract team slug from whoami output if available
    team_slug = None
    if auth_ok and auth_output:
        for line in auth_output.splitlines():
            normalized = " ".join(line.split())
            if normalized.lower().startswith("team name"):
                team_slug = normalized.removeprefix("Team Name").strip() or normalized
                break

    # 4) Check hosted training command availability. Prime 0.6+ uses
    # `prime train`; older 0.5.x releases exposed `prime rl`.
    ok, help_output = run(["prime", "--help"])
    train_available = ok and has_subcommand(help_output, "train")
    rl_available = ok and has_subcommand(help_output, "rl")
    checks.append(
        CheckResult(
            name="prime_train_command",
            ok=train_available or rl_available,
            detail=(
                "train command available"
                if train_available
                else "rl command available as legacy training command"
                if rl_available
                else "hosted training command unavailable"
            ),
        )
    )

    # 5) Check hosted/local eval command availability.
    eval_available = ok and has_subcommand(help_output, "eval")
    checks.append(
        CheckResult(
            name="prime_eval_command",
            ok=eval_available,
            detail="eval command available" if eval_available else "eval command unavailable",
        )
    )

    hosted_ready = all(
        c.ok
        for c in checks
        if c.name in {"prime_cli_installed", "prime_version", "prime_train_command", "prime_auth"}
    )
    fallback_ready = all(
        c.ok for c in checks if c.name in {"prime_cli_installed", "prime_version", "prime_eval_command"}
    )
    compatible = hosted_ready

    result = {
        "compatible": compatible,
        "status": "hosted-ready" if hosted_ready else "fallback-ready" if fallback_ready else "unavailable",
        "checks": [asdict(c) for c in checks],
        "next_steps": (
            [
                "Run `make config-validate`.",
                "Launch with `make lab-run-e1 REWARD_SOURCE=executable` "
                "or `make lab-run-e2 REWARD_SOURCE=executable`.",
                "Use `make env-eval-e1` / `make env-eval-e2` for hosted or fallback hosted-style eval.",
            ]
            if compatible
            else [
                "Authenticate with `prime login` before launching hosted RL."
                if fallback_ready
                else "Install or update the Prime CLI.",
                "Use local eval or fallback docs until hosted training is available.",
            ]
        ),
    }
    if team_slug:
        result["team_slug"] = team_slug

    print(json.dumps(result, indent=2))
    return 0 if hosted_ready or fallback_ready else 1


if __name__ == "__main__":
    sys.exit(main())
