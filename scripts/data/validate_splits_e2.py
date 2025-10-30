#!/usr/bin/env python3
"""
Validate E2 (config verification) canonical JSONL splits with Pydantic.

E2 schema: Tool-grounded config verification; detect + optional patch
{
  "prompt": "string",
  "info": {
    "violations": [
      {"tool":"string","rule_id":"string","severity":"string","msg":"string","loc":"string"}
    ],
    "patch": "string or null"
  },
  "meta": {
    "lang": "k8s|tf",
    "source": "string",
    "hash": "string"
  }
}

Usage:
    uv run scripts/data/validate_splits_e2.py --dir environments/sv-env-config-verification/data
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class Violation(BaseModel):
    """Security violation detected by tools."""

    tool: str = Field(..., description="Tool name (kube-linter, semgrep, opa)")
    rule_id: str = Field(..., description="Rule identifier")
    severity: str = Field(..., description="Severity level")
    msg: str = Field(..., description="Violation message")
    loc: str = Field(..., description="Location in file")


class InfoE2(BaseModel):
    """Detection and patch information for E2."""

    violations: list[Violation] = Field(default_factory=list, description="List of detected violations")
    patch: Optional[str] = Field(default="", description="Unified diff patch (null coerced to empty string)")


class MetaE2(BaseModel):
    """Metadata for E2 config verification samples."""

    lang: str = Field(..., description="Config language (k8s or tf)")
    source: str = Field(..., description="Source repository")
    hash: str = Field(..., description="SHA256 hash (short form)")

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        """Validate lang is k8s or tf."""
        allowed = {"k8s", "tf"}
        if v not in allowed:
            raise ValueError(f"lang must be one of {allowed}, got: {v}")
        return v


class RowE2(BaseModel):
    """E2 canonical row schema."""

    question: str = Field(..., description="Raw YAML/HCL configuration")
    info: InfoE2 = Field(..., description="Detection and patch info")
    meta: MetaE2 = Field(..., description="Sample metadata")


def validate_file(p: Path) -> int:
    """Validate a single JSONL file. Returns number of bad rows."""
    ok = 0
    bad = 0
    with p.open() as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                RowE2.model_validate_json(line)
                ok += 1
            except ValidationError as e:
                bad += 1
                print(f"[E2] {p}:{i} validation error:\n{e}\n", file=sys.stderr)
            except json.JSONDecodeError as e:
                bad += 1
                print(f"[E2] {p}:{i} JSON decode error:\n{e}\n", file=sys.stderr)
    print(f"[E2] {p.name}: OK={ok} BAD={bad}")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Validate E2 canonical JSONL splits with Pydantic")
    ap.add_argument(
        "--dir",
        type=Path,
        default=Path("environments/sv-env-config-verification/data"),
        help="Directory containing E2 JSONL files",
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

    print(f"[E2] Validating {len(jsonl_files)} JSONL files in {args.dir}")
    for p in jsonl_files:
        bad_total += validate_file(p)

    print(f"\n[E2] Summary: Total BAD rows = {bad_total}")
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()
