#!/usr/bin/env python3
"""
Validate E1 (network logs) canonical JSONL splits with Pydantic.

E1 schema: SingleTurn classification with calibration
{
  "question": "string",
  "answer": "Malicious | Benign",
  "meta": {
    "source": "string",
    "scenario": "string",
    "attack_family": "string",
    "hash": "string",
    "split": "train|dev|test|ood"
  }
}

Usage:
    uv run scripts/data/validate_splits_e1.py --dir environments/sv-env-network-logs/data
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator


class MetaE1(BaseModel):
    """Metadata for E1 network log samples."""

    source: str = Field(..., description="Dataset source (iot23, cic-ids-2017, unsw-nb15)")
    scenario: str = Field(default="unknown", description="Attack scenario (optional for demo files)")
    attack_family: str = Field(
        default="unknown", description="Attack family classification (optional for demo files)"
    )
    hash: str = Field(..., description="SHA256 hash (short form)")
    split: str = Field(default="demo", description="Split assignment (optional for demo files)")

    @field_validator("split")
    @classmethod
    def validate_split(cls, v: str) -> str:
        """Validate split is one of train/dev/test/ood/demo."""
        allowed = {"train", "dev", "test", "ood", "demo"}
        if v not in allowed:
            raise ValueError(f"split must be one of {allowed}, got: {v}")
        return v


class RowE1(BaseModel):
    """E1 canonical row schema."""

    question: str = Field(..., description="Network log question text")
    answer: str = Field(..., description="Classification label")
    meta: MetaE1 = Field(..., description="Sample metadata")

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        """Validate answer is Malicious or Benign."""
        allowed = {"Malicious", "Benign"}
        if v not in allowed:
            raise ValueError(f"answer must be one of {allowed}, got: {v}")
        return v


def validate_file(p: Path) -> int:
    """Validate a single JSONL file. Returns number of bad rows."""
    ok = 0
    bad = 0
    with p.open() as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                RowE1.model_validate_json(line)
                ok += 1
            except ValidationError as e:
                bad += 1
                print(f"[E1] {p}:{i} validation error:\n{e}\n", file=sys.stderr)
            except json.JSONDecodeError as e:
                bad += 1
                print(f"[E1] {p}:{i} JSON decode error:\n{e}\n", file=sys.stderr)
    print(f"[E1] {p.name}: OK={ok} BAD={bad}")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Validate E1 canonical JSONL splits with Pydantic")
    ap.add_argument(
        "--dir",
        type=Path,
        default=Path("environments/sv-env-network-logs/data"),
        help="Directory containing E1 JSONL files",
    )
    args = ap.parse_args()

    if not args.dir.exists():
        print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
        sys.exit(1)

    bad_total = 0
    jsonl_files = sorted(args.dir.glob("*.jsonl"))

    if not jsonl_files:
        print(f"Warning: No JSONL files found in {args.dir}", file=sys.stderr)
        sys.exit(0)

    print(f"[E1] Validating {len(jsonl_files)} JSONL files in {args.dir}")
    for p in jsonl_files:
        bad_total += validate_file(p)

    print(f"\n[E1] Summary: Total BAD rows = {bad_total}")
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()
