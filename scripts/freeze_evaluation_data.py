#!/usr/bin/env python3
"""Freeze private candidate cases; verify exclusion only against complete membership.

This establishes exact input exclusion, not statistical independence or absence
from pretraining. Historical sampled rollouts are not full membership evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_rows(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Dataset must contain nonempty JSON objects")
    return rows


def case_id(row: dict) -> str:
    # Labels are deliberately excluded: contradictory labels still overlap.
    prompt = row.get("question", row.get("prompt"))
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Each case needs a nonempty string question/prompt")
    return digest(prompt.encode("utf-8"))


def freeze(
    candidates: Path,
    output: Path,
    count: int,
    training: Path | None = None,
    provenance: Path | None = None,
) -> dict:
    if count < 1:
        raise ValueError("Case count must be positive")
    if output.exists():
        raise ValueError("Output already exists; frozen datasets cannot be overwritten")
    rows = load_rows(candidates)
    unique = {}
    for row in rows:
        identity = case_id(row)
        if identity in unique:
            # Ignore differing metadata but never silently choose competing labels.
            old = unique[identity]
            if (old.get("answer"), old.get("info")) != (row.get("answer"), row.get("info")):
                raise ValueError("Identical input has contradictory answers/info")
        else:
            unique[identity] = row
    train_ids: set[str] = set()
    full_membership = False
    training_descriptor = None
    if training is not None:
        train_rows = load_rows(training)
        train_ids = {case_id(row) for row in train_rows}
        if provenance is not None:
            training_descriptor = json.loads(provenance.read_text())
            if training_descriptor.get("dataset_sha256") != digest(training.read_bytes()):
                raise ValueError("Training dataset checksum differs from provenance")
            full_membership = training_descriptor.get("coverage") == "full-training-membership"
            if full_membership:
                run_ids = training_descriptor.get("training_run_ids")
                revision = training_descriptor.get("source_revision", "")
                if (
                    not isinstance(run_ids, list)
                    or not run_ids
                    or any(not isinstance(x, str) or not x.strip() for x in run_ids)
                ):
                    raise ValueError("Full membership must name all covered training runs")
                if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", revision):
                    raise ValueError("Full membership requires an immutable source revision")
                evidence = training_descriptor.get("membership_evidence", {})
                if not isinstance(evidence, dict):
                    raise ValueError("Full membership requires a hashed membership evidence file")
                evidence_path = provenance.parent / evidence.get("path", "")
                if not evidence_path.is_file() or digest(evidence_path.read_bytes()) != evidence.get(
                    "sha256"
                ):
                    raise ValueError("Full membership evidence checksum differs or file is absent")
    elif provenance is not None:
        raise ValueError("Training provenance requires training data")
    eligible = sorted(set(unique) - train_ids)
    if len(eligible) < count:
        raise ValueError(f"Requested {count} distinct cases; only {len(eligible)} eligible")
    chosen = eligible[:count]
    data = "".join(
        json.dumps(dict(unique[identity], case_id=identity), sort_keys=True, ensure_ascii=False) + "\n"
        for identity in chosen
    ).encode("utf-8")
    manifest = {
        "schema_version": 1,
        "dataset_path": "cases.jsonl",
        "dataset_sha256": digest(data),
        "case_count": len(chosen),
        "candidate_source_sha256": digest(candidates.read_bytes()),
        "candidate_rows": len(rows),
        "candidate_distinct_inputs": len(unique),
        "duplicate_input_rows": len(rows) - len(unique),
        "excluded_training_inputs": len(set(unique) & train_ids),
        "training_dataset_sha256": digest(training.read_bytes()) if training else None,
        "training_sources": training_descriptor,
        "heldout_verified": False,
        "claimed_full_membership": full_membership,
        "independence_status": "case-independence-unverified",
        "exclusion_status": "documented-full-membership" if full_membership else "unknown-full-membership",
        "heldout_ids_path": "heldout_ids.json",
        "train_ids_path": "train_ids.json",
        "selection": "ascending SHA256 of exact prompt UTF-8; no label stratification",
        "limitations": [
            "Exact-input exclusion does not prove independence of correlated cases.",
            "Full-membership assertions require scientific review of the linked evidence.",
            "Prompt changes can evade exact matching; related variants need source/group review.",
            "No claim about base-model pretraining contamination is made.",
        ],
    }
    output.mkdir(parents=True)
    (output / "cases.jsonl").write_bytes(data)
    (output / "heldout_ids.json").write_text(json.dumps(chosen, indent=2) + "\n")
    (output / "train_ids.json").write_text(json.dumps(sorted(train_ids), indent=2) + "\n")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--training", type=Path)
    parser.add_argument("--training-provenance", type=Path)
    args = parser.parse_args()
    manifest = freeze(args.candidates, args.output, args.count, args.training, args.training_provenance)
    print(json.dumps({k: manifest[k] for k in ("case_count", "dataset_sha256", "heldout_verified")}))


if __name__ == "__main__":
    main()
