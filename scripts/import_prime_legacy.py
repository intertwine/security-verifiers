"""Offline, lossless reconstruction of Prime legacy exports into private run artifacts.

Run with ``python scripts/import_prime_legacy.py --archive EXPORT.zip --output outputs/prime_legacy``.
Requires pyarrow for parquet. No network calls or model execution occur.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

JSON_FIELDS = {"prompt", "completion", "trajectory", "info", "metrics", "timing", "metadata", "extra"}
GAPS = [
    "Legacy exports omit model checkpoints and adapters; recover them separately.",
    "Hosted model revision/digest and immutable dataset provenance may be unavailable.",
    "Training samples are not independent held-out evaluation evidence.",
    "Colliding legacy sample IDs do not identify duplicate completions.",
]


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def normalized_row(row: dict[str, Any]) -> dict[str, Any]:
    result = json_value(row)
    for key in JSON_FIELDS & result.keys():
        if isinstance(result[key], str):
            try:
                result[key] = json_value(json.loads(result[key]))
            except ValueError:
                pass  # Plain strings, empty values and malformed historic content stay intact.
    return result


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    path.chmod(0o600)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical(row) + "\n" for row in rows))
    path.chmod(0o600)


def read_rows(name: str, data: bytes) -> list[dict[str, Any]]:
    if name.endswith(".jsonl"):
        return [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    import pyarrow.parquet as parquet

    return parquet.read_table(io.BytesIO(data)).to_pylist()


def compare_curated(rows: list[dict[str, Any]], directory: Path | None) -> dict[str, Any]:
    """Compare shared fields before decoding; one local row may match any archived row."""
    if directory is None or not (directory / "results.jsonl").exists():
        return {"available": False}
    local = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines() if line]
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    keys = ("step", "tag", "problem_id", "sample_id")
    for row in rows:
        by_identity[canonical([row.get(key) for key in keys])].append(json_value(row))
    matched = missing = changed = 0
    for row in local:
        candidates = by_identity[canonical([row.get(key) for key in keys])]
        if not candidates:
            missing += 1
        elif any(all(candidate.get(key) == value for key, value in row.items()) for candidate in candidates):
            matched += 1
        else:
            changed += 1
    return {
        "available": True,
        "local_rows": len(local),
        "matched": matched,
        "missing": missing,
        "changed": changed,
        "comparison": "all locally retained fields, before JSON-string decoding",
    }


def import_archive(archive: Path, output: Path, curated_root: Path | None = None) -> dict[str, Any]:
    """Retain every source row and provenance; refuse overwrites and unsafe ZIP members."""
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    with archive.open("rb") as handle:
        archive_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Archive has duplicate member names")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError(f"Unsafe archive member: {name}")
        if source.testzip() is not None:
            raise ValueError("Archive CRC integrity check failed")
        manifest = json.loads(source.read("manifest.json"))
        objects = [("training_runs", item["id"]) for item in manifest["trainingRuns"]]
        objects += [("evaluations", item["id"]) for item in manifest["evaluations"]]
        for kind, identifier in objects:
            if not identifier or PurePosixPath(identifier).name != identifier or identifier in {".", ".."}:
                raise ValueError("Unsafe archive object ID")
            metadata_name = "run.json" if kind == "training_runs" else "evaluation.json"
            if f"{kind}/{identifier}/{metadata_name}" not in names:
                raise ValueError(f"Manifest object is missing metadata: {identifier}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".prime-import-", dir=output.parent))
        try:
            report = {
                "schema_version": 1,
                "archive_sha256": archive_digest,
                "archive_filename": archive.name,
                "manifest": manifest,
                "limitations": GAPS,
                "objects": [],
            }
            write_json(staging / "export_manifest.json", manifest)
            for kind, identifier in objects:
                prefix = f"{kind}/{identifier}/"
                directory = staging / kind / identifier
                directory.mkdir(parents=True, mode=0o700)
                members = sorted(name for name in names if name.startswith(prefix) and not name.endswith("/"))
                metadata_name = "run.json" if kind == "training_runs" else "evaluation.json"
                metadata = json.loads(source.read(prefix + metadata_name))
                raw_samples: list[dict[str, Any]] = []
                samples: list[dict[str, Any]] = []
                member_records = []
                ancillary: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for name in members:
                    data = source.read(name)
                    record = {"member": name, "sha256": sha256(data), "bytes": len(data)}
                    if "/artifacts/" in name:
                        artifact = directory / name.removeprefix(prefix)
                        artifact.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        artifact.write_bytes(data)
                        artifact.chmod(0o600)
                    elif name.endswith((".parquet", ".jsonl")):
                        rows = read_rows(name, data)
                        record["rows"] = len(rows)
                        category = (
                            "samples"
                            if "/samples/" in name or name.endswith("/samples.jsonl")
                            else ("distributions" if "/distributions/" in name else "metrics")
                        )
                        for index, row in enumerate(rows):
                            normalized = normalized_row(row)
                            provenance = {
                                "archive_sha256": archive_digest,
                                "member": name,
                                "row": index,
                                "payload_sha256": sha256(canonical(json_value(row)).encode()),
                            }
                            normalized["_archive_source"] = provenance
                            if category == "samples":
                                raw_samples.append(row)
                                samples.append(normalized)
                            else:
                                ancillary[category].append(normalized)
                    member_records.append(record)
                identities = Counter(
                    canonical([row.get(key) for key in ("step", "tag", "problem_id", "sample_id")])
                    for row in raw_samples
                )
                payloads = Counter(canonical(json_value(row)) for row in raw_samples)
                curated = curated_root / identifier if curated_root is not None else None
                coverage = {
                    "id": identifier,
                    "kind": kind,
                    "sample_rows": len(samples),
                    "distinct_payloads": len(payloads),
                    "repeated_payload_rows": len(samples) - len(payloads),
                    "identity_collision_rows": len(samples) - len(identities),
                    "step_counts": dict(Counter(str(row.get("step")) for row in raw_samples)),
                    "members": member_records,
                    "curated_comparison": compare_curated(raw_samples, curated),
                    "limitations": GAPS,
                    "deduplication": "none: all rows retained with member+row identity",
                }
                write_jsonl(directory / "results.jsonl", samples)
                for category, rows in ancillary.items():
                    write_jsonl(directory / f"{category}.jsonl", rows)
                write_json(directory / "archive_metadata.json", metadata)
                write_json(
                    directory / "metadata.json",
                    {
                        **metadata,
                        "run_id": identifier,
                        "model": metadata.get("baseModel") or metadata.get("model") or "unknown",
                        "archive_preservation": {"limitations": GAPS, "held_out_evidence": False},
                    },
                )
                write_json(directory / "archive_provenance.json", coverage)
                if curated is not None and (curated / "run_manifest.json").exists():
                    write_json(
                        directory / "historical_run_manifest.json",
                        json.loads((curated / "run_manifest.json").read_text()),
                    )
                report["objects"].append(coverage)
            write_json(staging / "reconciliation.json", report)
            lines = [
                "# Private legacy archive reconstruction",
                "",
                f"Archive SHA-256: `{archive_digest}`",
                "",
                "All source rows are retained, including repeated IDs and identical payloads.",
                "This reconstruction preserves historical evidence; "
                "it does not establish a held-out benchmark.",
                "",
                f"Missing source objects: {len(manifest.get('missingObjects', []))}",
                "",
                "| Kind | ID | Rows | Distinct payloads | ID collisions | Curated matches |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
            for item in report["objects"]:
                comparison = item["curated_comparison"]
                matches = str(comparison["matched"]) if comparison["available"] else "unavailable"
                lines.append(
                    f"| {item['kind']} | {item['id']} | {item['sample_rows']} | "
                    f"{item['distinct_payloads']} | {item['identity_collision_rows']} | {matches} |"
                )
            lines.extend(["", "## Remaining provenance gaps", "", *(f"- {gap}" for gap in GAPS), ""])
            (staging / "report.md").write_text("\n".join(lines))
            (staging / "report.md").chmod(0o600)
            os.rename(staging, output)
        except BaseException:
            shutil.rmtree(staging)
            raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New private output directory")
    parser.add_argument("--curated-root", type=Path)
    args = parser.parse_args()
    report = import_archive(args.archive, args.output, args.curated_root)
    print(f"Imported {len(report['objects'])} objects; archive SHA-256 {report['archive_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
