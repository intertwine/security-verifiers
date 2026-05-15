#!/usr/bin/env python3
"""Compare executable, judge, and hybrid reward-source runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import fmean
from typing import Any

from bench.run_manifest import validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUDGET_FIELDS = (
    "environment_id",
    "dataset_id",
    "dataset_revision",
    "split",
    "model_id",
    "model_revision_or_digest",
    "max_steps",
    "rollouts_per_example",
    "max_tokens",
    "max_turns",
    "tool_budget",
    "trainer",
)
HOSTED_IDENTITY_FIELDS = (
    "prime_environment_id",
    "environment_version",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(path: str, base: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if (base / candidate).exists():
        return base / candidate
    return REPO_ROOT / candidate


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_json(path)
    validate_manifest(manifest)
    manifest["_manifest_path"] = str(path)
    return manifest


def _field_mismatches(
    manifests: dict[str, dict[str, Any]],
    fields: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    baseline = manifests["executable"]
    mismatches: dict[str, dict[str, Any]] = {}
    for variant, manifest in manifests.items():
        if variant == "executable":
            continue
        for field in fields:
            if manifest.get(field) != baseline.get(field):
                mismatches.setdefault(field, {})["executable"] = baseline.get(field)
                mismatches[field][variant] = manifest.get(field)
    return mismatches


def _budget_mismatches(manifests: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _field_mismatches(manifests, BUDGET_FIELDS)


def _flatten_metrics(summary: dict[str, Any]) -> dict[str, float]:
    flat: dict[str, float] = {}

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(f"{prefix}.{key}" if prefix else str(key), child)
            return
        if isinstance(value, list):
            numeric = [float(item) for item in value if isinstance(item, (int, float))]
            if numeric:
                flat[prefix] = fmean(numeric)
            return
        if isinstance(value, (int, float)):
            flat[prefix] = float(value)

    visit("", summary.get("metrics", summary))
    return flat


def _load_metrics(manifest: dict[str, Any], *, allow_incomplete: bool) -> dict[str, float]:
    manifest_path = Path(str(manifest["_manifest_path"]))
    summary_path = _resolve(str(manifest["metrics_summary_path"]), manifest_path.parent)
    summary = _load_json(summary_path)
    run_status = summary.get("run_status")
    if not allow_incomplete and manifest.get("platform_mode") == "hosted" and run_status != "COMPLETED":
        raise ValueError(
            f"Run {manifest.get('run_id')} is not complete enough for claim comparison: {run_status}"
        )
    metrics = _flatten_metrics(summary)
    if not allow_incomplete and not metrics:
        raise ValueError(f"Run {manifest.get('run_id')} has no comparable metrics")
    return metrics


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return right - left


def _build_summary(
    env: str,
    manifests: dict[str, dict[str, Any]],
    allow_unmatched: bool,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    mismatches = _budget_mismatches(manifests)
    if mismatches and not allow_unmatched:
        raise ValueError(
            "Budget parity failed. Use --allow-unmatched only for exploratory reports. "
            f"Mismatched fields: {', '.join(sorted(mismatches))}"
        )

    hosted_identity_mismatches = _field_mismatches(manifests, HOSTED_IDENTITY_FIELDS)
    if hosted_identity_mismatches and not allow_unmatched:
        raise ValueError(
            "Hosted identity parity failed. Use --allow-unmatched only for exploratory reports. "
            f"Mismatched fields: {', '.join(sorted(hosted_identity_mismatches))}"
        )
    metrics = {
        variant: _load_metrics(manifest, allow_incomplete=allow_incomplete)
        for variant, manifest in manifests.items()
    }
    metric_names = sorted({name for variant_metrics in metrics.values() for name in variant_metrics})
    rows: list[dict[str, Any]] = []
    for name in metric_names:
        executable = metrics["executable"].get(name)
        judge = metrics["judge"].get(name)
        hybrid = metrics["hybrid"].get(name)
        rows.append(
            {
                "metric": name,
                "executable": executable,
                "judge": judge,
                "hybrid": hybrid,
                "judge_delta_vs_executable": _delta(executable, judge),
                "hybrid_delta_vs_executable": _delta(executable, hybrid),
            }
        )

    return {
        "environment": env,
        "allow_unmatched": allow_unmatched,
        "allow_incomplete": allow_incomplete,
        "budget_fields": list(BUDGET_FIELDS),
        "budget_mismatches": mismatches,
        "hosted_identity_fields": list(HOSTED_IDENTITY_FIELDS),
        "hosted_identity_mismatches": hosted_identity_mismatches,
        "runs": {
            variant: {
                "run_id": manifest["run_id"],
                "manifest": manifest["_manifest_path"],
                "reward_config_id": manifest["reward_config_id"],
                "reward_source": manifest.get("reward_source", variant),
            }
            for variant, manifest in manifests.items()
        },
        "metric_rows": rows,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Reward Source Comparison: {summary['environment'].upper()}",
        "",
        "## Budget Parity",
        "",
    ]
    if summary["budget_mismatches"]:
        lines.append("Budget mismatches were present. This report is exploratory unless explicitly approved.")
        lines.append("")
        lines.extend(
            f"- `{field}`: {values}" for field, values in sorted(summary["budget_mismatches"].items())
        )
    else:
        lines.append("All required budget fields match across executable, judge, and hybrid manifests.")
    lines.extend(
        [
            "",
            "## Hosted Identity",
            "",
        ]
    )
    if summary["hosted_identity_mismatches"]:
        lines.append(
            "Hosted environment identity/version differs across variants and is reported separately."
        )
        lines.append("")
        lines.extend(
            f"- `{field}`: {values}"
            for field, values in sorted(summary["hosted_identity_mismatches"].items())
        )
    else:
        lines.append("Hosted environment IDs and versions match across variants, or were not reported.")
    lines.extend(
        [
            "",
            "## Metric Deltas",
            "",
            "| Metric | Executable | Judge | Hybrid | Judge delta | Hybrid delta |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["metric_rows"]:
        lines.append(
            "| {metric} | {executable} | {judge} | {hybrid} | {judge_delta} | {hybrid_delta} |".format(
                metric=row["metric"],
                executable=_fmt(row["executable"]),
                judge=_fmt(row["judge"]),
                hybrid=_fmt(row["hybrid"]),
                judge_delta=_fmt(row["judge_delta_vs_executable"]),
                hybrid_delta=_fmt(row["hybrid_delta_vs_executable"]),
            )
        )
    lines.extend(
        [
            "",
            "## Failure-Mode Notes",
            "",
            "- Inspect `results.jsonl` or `rollouts_raw.json` before quoting representative traces.",
            "- Treat judge-only gains cautiously unless unsupported claims and invalid schemas remain low.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare matched reward-source manifests.")
    parser.add_argument("--env", choices=["e1", "e2"], required=True)
    parser.add_argument("--executable", required=True, help="Executable reward run manifest")
    parser.add_argument("--judge", required=True, help="LLM-judge reward run manifest")
    parser.add_argument("--hybrid", required=True, help="Hybrid reward run manifest")
    parser.add_argument("--out", required=True, help="Markdown output path")
    parser.add_argument("--json-out", default=None, help="JSON summary output path")
    parser.add_argument("--allow-unmatched", action="store_true", help="Allow unmatched budgets")
    parser.add_argument("--allow-incomplete", action="store_true", help="Allow incomplete/empty metrics")
    args = parser.parse_args()

    manifests = {
        "executable": _load_manifest(Path(args.executable)),
        "judge": _load_manifest(Path(args.judge)),
        "hybrid": _load_manifest(Path(args.hybrid)),
    }
    summary = _build_summary(args.env, manifests, args.allow_unmatched, args.allow_incomplete)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown(summary), encoding="utf-8")

    json_path = Path(args.json_out) if args.json_out else out_path.with_suffix(".json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"✓ Wrote {out_path}")
    print(f"✓ Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
