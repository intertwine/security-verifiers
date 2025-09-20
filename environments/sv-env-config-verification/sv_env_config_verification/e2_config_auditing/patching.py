"""Patch application utilities."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Tuple

PatchFormat = Literal["unified-diff", "json-patch"]


class PatchError(RuntimeError):
    """Raised when a patch cannot be applied."""


def detect_patch_format(patch: str) -> PatchFormat:
    """Best-effort detection of patch format."""

    patch = patch.strip()
    if patch.startswith("["):
        return "json-patch"
    return "unified-diff"


def apply_patch_to_text(original: str, patch: str) -> str:
    """Apply a unified diff patch to ``original`` text using the ``patch`` CLI."""

    with tempfile.TemporaryDirectory() as td:
        file_path = Path(td, "file.txt")
        file_path.write_text(original, encoding="utf-8")
        proc = subprocess.run(
            ["patch", str(file_path)],
            input=patch,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise PatchError(proc.stderr.strip() or "patch failed")
        return file_path.read_text(encoding="utf-8")


def apply_json_patch(obj: dict, patch_ops: list[dict]) -> dict:
    """Apply a minimal subset of RFC6902 JSON Patch operations."""

    data = copy.deepcopy(obj)
    for op in patch_ops:
        path = op.get("path", "")
        tokens = [t for t in path.strip("/").split("/") if t]
        parent = data
        for t in tokens[:-1]:
            parent = parent.setdefault(t, {})
        key = tokens[-1] if tokens else None
        if op.get("op") in {"add", "replace"}:
            parent[key] = op.get("value")
        elif op.get("op") == "remove":
            parent.pop(key, None)
        else:  # pragma: no cover - simple set
            raise PatchError(f"unsupported op {op.get('op')}")
    return data


def try_apply_patch(path: str, patch: str) -> Tuple[bool, str]:
    """Apply ``patch`` to the file at ``path`` and return ``(applied, text)``."""

    original = Path(path).read_text(encoding="utf-8")
    fmt = detect_patch_format(patch)
    if fmt == "unified-diff":
        try:
            new_text = apply_patch_to_text(original, patch)
        except PatchError:
            return False, original
        return True, new_text
    try:
        ops = json.loads(patch)
        new_obj = apply_json_patch(json.loads(original), ops)
        return True, json.dumps(new_obj, indent=2)
    except (json.JSONDecodeError, ValueError, PatchError):
        return False, original


__all__ = [
    "PatchFormat",
    "PatchError",
    "detect_patch_format",
    "apply_patch_to_text",
    "apply_json_patch",
    "try_apply_patch",
]
