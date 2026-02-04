#!/usr/bin/env python3
"""Generate schema-stable SV-Bench per-run reports.

This script finds evaluation run directories under `outputs/evals/` (recursively)
and writes:
  - summary.json (schema: bench/schemas/summary.schema.json)
  - report.md (human-readable)

It skips `outputs/evals/archived/` by default.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("PYTHONPATH", str(REPO_ROOT))

# Default: avoid accidental network calls from auto-initialized tracing/logging.
os.environ.setdefault("WEAVE_DISABLED", "true")

from bench.report import generate_report_md, generate_summary, load_results  # noqa: E402

ENV_ALIASES = {
    "e1": "e1",
    "network-logs": "e1",
    "sv-env-network-logs": "e1",
    "e2": "e2",
    "config-verification": "e2",
    "sv-env-config-verification": "e2",
}


def _iter_run_dirs(eval_dir: Path, run_ids: set[str] | None) -> Iterable[Path]:
    """Yield run directories containing metadata.json + results.jsonl."""
    for metadata_file in eval_dir.rglob("metadata.json"):
        run_dir = metadata_file.parent
        if "archived" in run_dir.parts:
            continue
        if run_ids is not None and run_dir.name not in run_ids:
            continue
        if not (run_dir / "results.jsonl").exists():
            continue
        yield run_dir


def _resolve_env(metadata: dict, forced_env: str | None) -> str | None:
    """Resolve svbench env name ("e1" or "e2") from metadata."""
    if forced_env:
        return ENV_ALIASES.get(forced_env, forced_env)
    env = metadata.get("environment")
    if isinstance(env, str):
        return ENV_ALIASES.get(env, None)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SV-Bench per-run reports under outputs/evals/")
    parser.add_argument(
        "--eval-dir",
        type=Path,
        default=Path("outputs/evals"),
        help="Directory containing evaluation runs (default: outputs/evals)",
    )
    parser.add_argument(
        "--env",
        choices=["e1", "e2", "network-logs", "config-verification"],
        default=None,
        help="Only process one environment type (default: infer per run from metadata.json)",
    )
    parser.add_argument(
        "--run-ids",
        nargs="+",
        default=None,
        help="Only process these run ids (directory names)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail a run if required fields are missing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing files",
    )
    parser.add_argument(
        "--enable-weave",
        action="store_true",
        help="Allow Weave auto-init (default: disabled via WEAVE_DISABLED=true)",
    )

    args = parser.parse_args()

    if args.enable_weave:
        os.environ["WEAVE_DISABLED"] = "false"

    eval_dir = Path(args.eval_dir)
    if not eval_dir.exists():
        raise SystemExit(f"eval-dir not found: {eval_dir}")

    run_ids = set(args.run_ids) if args.run_ids else None

    processed = 0
    skipped = 0
    failed = 0

    for run_dir in sorted(_iter_run_dirs(eval_dir, run_ids)):
        results, metadata = load_results(run_dir)
        resolved_env = _resolve_env(metadata, args.env)
        if resolved_env is None:
            skipped += 1
            print(f"- Skipping {run_dir} (unable to determine env)")
            continue
        if args.env and ENV_ALIASES.get(args.env, args.env) != resolved_env:
            skipped += 1
            continue

        if args.dry_run:
            processed += 1
            print(f"- Would generate {resolved_env} report in {run_dir}")
            continue

        try:
            summary = generate_summary(
                resolved_env,
                results,
                metadata,
                run_id=run_dir.name,
                strict=args.strict,
            )
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            (run_dir / "report.md").write_text(generate_report_md(summary), encoding="utf-8")
            processed += 1
            print(f"✓ {resolved_env} {run_dir}")
        except Exception as exc:
            failed += 1
            print(f"✗ Failed {run_dir}: {exc}")

    print(f"\nProcessed: {processed}, skipped: {skipped}, failed: {failed}")


if __name__ == "__main__":
    main()
