import json
import subprocess
import sys
from pathlib import Path


def test_normalize_hosted_eval_metadata(tmp_path: Path) -> None:
    src = tmp_path / "hosted.json"
    dst = tmp_path / "normalized" / "metadata.json"
    src.write_text(
        json.dumps(
            {
                "run_id": "run-123",
                "environment_version": "0.2.10",
                "model_id": "Qwen/Qwen3-4B-Instruct-2507",
                "model_revision": "main",
                "dataset_sha": "sha256:abcd",
                "created_at": "2026-02-14T00:00:00Z",
                "n_examples": 10,
                "repo_sha": "deadbee",
                "image": "prime/lab:latest",
                "compute": "a100x1",
                "loader_mode": "public_mini",
            }
        )
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/normalize_hosted_eval.py",
            "--input",
            str(src),
            "--output",
            str(dst),
            "--environment",
            "sv-env-network-logs",
            "--dataset",
            "public-mini-e1",
        ],
        check=True,
    )

    normalized = json.loads(dst.read_text())
    assert normalized["run_id"] == "run-123"
    assert normalized["environment"] == "sv-env-network-logs"
    assert normalized["dataset"] == "public-mini-e1"
    assert normalized["platform_metadata"]["compute"] == "a100x1"
