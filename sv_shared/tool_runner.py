"""Reproducible command runner for local and sandbox-backed security tools."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")


@dataclass
class ToolResult:
    """Normalized result for one tool invocation."""

    command: list[str]
    mode: str
    exit_code: int
    duration_ms: float
    stdout_snippet: str
    stderr_snippet: str
    tool_version: str | None = None
    normalized_findings: list[dict[str, object]] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _scrub(text: str, extra_env: Mapping[str, str] | None = None) -> str:
    scrubbed = text
    candidates = dict(os.environ)
    if extra_env:
        candidates.update(extra_env)
    for name, value in candidates.items():
        if not value or len(value) < 6:
            continue
        if any(marker in name.upper() for marker in SECRET_MARKERS):
            scrubbed = scrubbed.replace(value, "[REDACTED]")
    return scrubbed


def _snippet(text: str, limit: int = 4000, extra_env: Mapping[str, str] | None = None) -> str:
    return _scrub(text, extra_env=extra_env)[:limit]


def _version_for(command: Sequence[str]) -> str | None:
    executable = command[0] if command else ""
    if not executable or shutil.which(executable) is None:
        return None
    for flag in ("--version", "version", "-version"):
        try:
            result = subprocess.run(
                [executable, flag],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            continue
        output = (result.stdout or result.stderr).strip()
        if output:
            return output.splitlines()[0][:200]
    return None


class ToolRunner:
    """Run tools in local, Docker, or dry-run Prime Sandbox modes."""

    def __init__(self, mode: str = "local", image: str | None = None, timeout_seconds: int = 60) -> None:
        if mode not in {"local", "docker", "prime-sandbox"}:
            raise ValueError("mode must be local, docker, or prime-sandbox")
        self.mode = mode
        self.image = image
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        dry_run: bool = False,
    ) -> ToolResult:
        if self.mode == "prime-sandbox":
            return self._run_prime_sandbox(command, cwd=cwd, env=env, dry_run=dry_run)
        if self.mode == "docker":
            return self._run_docker(command, cwd=cwd, env=env, dry_run=dry_run)
        return self._run_local(command, cwd=cwd, env=env, dry_run=dry_run)

    def _run_local(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None,
        env: Mapping[str, str] | None,
        dry_run: bool,
    ) -> ToolResult:
        start = time.perf_counter()
        if dry_run:
            return ToolResult(
                command=list(command),
                mode="local",
                exit_code=0,
                duration_ms=0.0,
                stdout_snippet="dry-run: local command not executed",
                stderr_snippet="",
                tool_version=_version_for(command),
                dry_run=True,
            )
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        result = subprocess.run(
            list(command),
            cwd=cwd,
            env=run_env,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        return ToolResult(
            command=list(command),
            mode="local",
            exit_code=result.returncode,
            duration_ms=(time.perf_counter() - start) * 1000,
            stdout_snippet=_snippet(result.stdout or "", extra_env=env),
            stderr_snippet=_snippet(result.stderr or "", extra_env=env),
            tool_version=_version_for(command),
        )

    def _run_docker(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None,
        env: Mapping[str, str] | None,
        dry_run: bool,
    ) -> ToolResult:
        image = self.image or "python:3.12-slim"
        workdir = Path(cwd or Path.cwd()).resolve()
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workdir}:/workspace",
            "-w",
            "/workspace",
            image,
            *command,
        ]
        if dry_run or shutil.which("docker") is None:
            return ToolResult(
                command=docker_cmd,
                mode="docker",
                exit_code=0 if dry_run else 127,
                duration_ms=0.0,
                stdout_snippet="dry-run: docker command not executed" if dry_run else "docker executable not found",
                stderr_snippet="",
                dry_run=dry_run,
            )
        return ToolRunner(mode="local", timeout_seconds=self.timeout_seconds).run(
            docker_cmd,
            env=env,
        )

    def _run_prime_sandbox(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None,
        env: Mapping[str, str] | None,
        dry_run: bool,
    ) -> ToolResult:
        del cwd, env
        image = self.image or "python:3.12-slim"
        prime_cmd = ["prime", "sandbox", "run", "<sandbox-id>", *command]
        return ToolResult(
            command=prime_cmd,
            mode="prime-sandbox",
            exit_code=0 if dry_run else 2,
            duration_ms=0.0,
            stdout_snippet=(
                f"dry-run: would run in Prime Sandbox image {image}. Create a sandbox first, then replace <sandbox-id>."
            ),
            stderr_snippet="" if dry_run else "Prime Sandbox live execution is intentionally explicit.",
            dry_run=dry_run,
        )


__all__ = ["ToolResult", "ToolRunner"]
