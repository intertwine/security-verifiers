"""Synthetic archive tests; no private research payloads or network access."""

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.import_prime_legacy import import_archive, normalized_row  # noqa: E402


def archive(path: Path, rows: list[dict], extra: dict[str, bytes] | None = None) -> None:
    with zipfile.ZipFile(path, "w") as source:
        source.writestr(
            "manifest.json",
            json.dumps({"trainingRuns": [{"id": "run"}], "evaluations": [], "missingObjects": []}),
        )
        source.writestr("training_runs/run/run.json", json.dumps({"id": "run", "status": "COMPLETED"}))
        source.writestr("training_runs/run/samples/data.jsonl", "".join(json.dumps(r) + "\n" for r in rows))
        for name, data in (extra or {}).items():
            source.writestr(name, data)


def test_colliding_ids_and_duplicate_payloads_preserve_every_row(tmp_path):
    rows = [
        {"step": 0, "sample_id": "0", "completion": '[{"content": "a"}]'},
        {"step": 0, "sample_id": "0", "completion": '[{"content": "b"}]'},
    ]
    rows.append(rows[0])
    source = tmp_path / "export.zip"
    archive(source, rows)
    output = tmp_path / "private"
    report = import_archive(source, output)
    imported = [
        json.loads(line) for line in (output / "training_runs/run/results.jsonl").read_text().splitlines()
    ]
    assert [row["completion"][0]["content"] for row in imported] == ["a", "b", "a"]
    assert [row["_archive_source"]["row"] for row in imported] == [0, 1, 2]
    assert report["objects"][0]["identity_collision_rows"] == 2
    assert report["objects"][0]["repeated_payload_rows"] == 1
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / "training_runs/run/results.jsonl").stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        import_archive(source, output)


def test_curated_comparison_matches_any_colliding_completion(tmp_path):
    source = tmp_path / "export.zip"
    rows = [{"sample_id": "0", "answer": "a"}, {"sample_id": "0", "answer": "b", "extra": "{}"}]
    archive(source, rows)
    curated = tmp_path / "curated/run"
    curated.mkdir(parents=True)
    (curated / "results.jsonl").write_text(json.dumps({"sample_id": "0", "answer": "b"}) + "\n")
    report = import_archive(source, tmp_path / "private", curated.parent)
    assert report["objects"][0]["curated_comparison"]["matched"] == 1


def test_unsafe_archive_is_rejected_before_writes(tmp_path):
    source = tmp_path / "export.zip"
    archive(source, [], {"../escape": b"unsafe"})
    output = tmp_path / "private"
    with pytest.raises(ValueError, match="Unsafe archive member"):
        import_archive(source, output)
    assert not output.exists()


def test_parquet_metrics_and_artifacts_are_retained(tmp_path):
    parquet = pytest.importorskip("pyarrow.parquet")
    arrow = pytest.importorskip("pyarrow")
    buffer = io.BytesIO()
    parquet.write_table(arrow.Table.from_pylist([{"step": 1, "reward": 0.5}]), buffer)
    source = tmp_path / "export.zip"
    archive(
        source,
        [],
        {
            "training_runs/run/metrics/part.parquet": buffer.getvalue(),
            "training_runs/run/artifacts/trace.txt": b"fixture",
            "training_runs/run/artifacts/media.parquet": b"opaque media payload",
        },
    )
    output = tmp_path / "private"
    import_archive(source, output)
    metrics = json.loads((output / "training_runs/run/metrics.jsonl").read_text())
    assert metrics["reward"] == 0.5
    assert metrics["_archive_source"]["member"].endswith("part.parquet")
    assert (output / "training_runs/run/artifacts/trace.txt").read_bytes() == b"fixture"
    assert (output / "training_runs/run/artifacts/media.parquet").read_bytes() == b"opaque media payload"


def test_json_decode_leaves_plain_and_malformed_text_intact():
    row = normalized_row(
        {
            "answer": "Benign",
            "prompt": "plain",
            "extra": '{"trajectory": [1]}',
            "completion": "{bad",
            "metrics": '{"reward": NaN}',
        }
    )
    assert row["answer"] == "Benign"
    assert row["prompt"] == "plain"
    assert row["completion"] == "{bad"
    assert row["extra"]["trajectory"] == [1]
    assert row["metrics"]["reward"] == "nan"
