#!/usr/bin/env python3
"""Suite v1.0 completion gate."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from eval_beta_env import DATASETS, _load_jsonl, validate_beta_env  # noqa: E402

ENVIRONMENTS = {
    "e1": (
        "environments/sv-env-network-logs/sv_env_network_logs.py",
        "datasets/public_mini/e1.jsonl",
        "configs/eval/e1_baseline.toml",
        "bench/metrics/METRICS_E1.md",
    ),
    "e2": (
        "environments/sv-env-config-verification/sv_env_config_verification.py",
        "datasets/public_mini/e2.jsonl",
        "configs/eval/e2_baseline.toml",
        "bench/metrics/METRICS_E2.md",
    ),
    "e3": (
        "environments/sv-env-code-vulnerability/sv_env_code_vulnerability.py",
        "datasets/public_mini/e3.jsonl",
        "configs/eval/e3_beta.toml",
        "bench/metrics/METRICS_E3.md",
    ),
    "e4": (
        "environments/sv-env-phishing-detection/sv_env_phishing_detection.py",
        "datasets/public_mini/e4.jsonl",
        "configs/eval/e4_beta.toml",
        "bench/metrics/METRICS_E4.md",
    ),
    "e5": (
        "environments/sv-env-redteam-attack/sv_env_redteam_attack.py",
        "datasets/public_mini/e5_sanitized.jsonl",
        "configs/eval/e5_beta.toml",
        "bench/metrics/METRICS_E5.md",
    ),
    "e6": (
        "environments/sv-env-redteam-defense/sv_env_redteam_defense.py",
        "datasets/public_mini/e6_sanitized.jsonl",
        "configs/eval/e6_beta.toml",
        "bench/metrics/METRICS_E6.md",
    ),
}


def _module_importable(path: Path) -> bool:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    return spec is not None and spec.loader is not None


def main() -> int:
    errors: list[str] = []
    for env_id, rels in ENVIRONMENTS.items():
        module, dataset, config, metrics = rels
        module_path = REPO_ROOT / module
        if not module_path.exists():
            errors.append(f"{env_id}: missing module {module}")
        elif not _module_importable(module_path):
            errors.append(f"{env_id}: module spec not importable {module}")
        for rel in (dataset, config, metrics):
            if not (REPO_ROOT / rel).exists():
                errors.append(f"{env_id}: missing {rel}")

    required = [
        "SUITE_V1_CHECKLIST.md",
        "docs/environments-hub-publication.md",
        "docs/redteam-data-publication-policy.md",
        "datasets/HELDOUT_POLICY.md",
        "bench/leaderboard/suite_v1.schema.json",
    ]
    for rel in required:
        if not (REPO_ROOT / rel).exists():
            errors.append(f"missing suite file {rel}")

    for env_id in ("e3", "e4", "e5", "e6"):
        try:
            rows = _load_jsonl(REPO_ROOT / DATASETS[env_id], 10)
            validate_beta_env(env_id, rows)
        except Exception as exc:
            errors.append(f"{env_id}: beta validation failed: {exc}")

    if errors:
        for error in errors:
            print(f"✗ {error}")
        return 1
    print("✓ Suite v1 completion checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
