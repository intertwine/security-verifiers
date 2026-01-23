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


def apply_json_patch(obj: dict, patch_ops: list[dict]) -> object:
    """Apply a minimal subset of RFC6902 JSON Patch operations."""

    def _parse_index(token: str, allow_append: bool = False) -> int | str:
        if allow_append and token == "-":
            return token
        if token.isdigit():
            return int(token)
        raise PatchError(f"invalid array index '{token}'")

    data: dict | list = copy.deepcopy(obj)
    for op in patch_ops:
        path = op.get("path", "")
        tokens = [t for t in path.strip("/").split("/") if t]
        if not tokens:
            if op.get("op") in {"add", "replace"}:
                data = op.get("value")
                continue
            if op.get("op") == "remove":
                data = {}
                continue
            raise PatchError(f"unsupported op {op.get('op')}")

        parent: dict | list = data
        for t in tokens[:-1]:
            if isinstance(parent, dict):
                if t not in parent:
                    parent[t] = {}
                elif parent[t] is None:
                    raise PatchError(f"cannot traverse null value at path segment '{t}'")
                parent = parent[t]
            elif isinstance(parent, list):
                idx = _parse_index(t)
                if not isinstance(idx, int) or idx >= len(parent):
                    raise PatchError(f"array index out of range: {t}")
                parent = parent[idx]
            else:
                raise PatchError(f"unsupported container at path segment '{t}'")

        key = tokens[-1]
        if isinstance(parent, dict):
            if op.get("op") in {"add", "replace"}:
                parent[key] = op.get("value")
            elif op.get("op") == "remove":
                parent.pop(key, None)
            else:  # pragma: no cover - simple set
                raise PatchError(f"unsupported op {op.get('op')}")
        elif isinstance(parent, list):
            idx = _parse_index(key, allow_append=op.get("op") == "add")
            if op.get("op") == "add":
                if idx == "-":
                    parent.append(op.get("value"))
                elif isinstance(idx, int):
                    if idx > len(parent):
                        raise PatchError(f"array index out of range: {key}")
                    parent.insert(idx, op.get("value"))
            elif op.get("op") == "replace":
                if not isinstance(idx, int) or idx >= len(parent):
                    raise PatchError(f"array index out of range: {key}")
                parent[idx] = op.get("value")
            elif op.get("op") == "remove":
                if not isinstance(idx, int) or idx >= len(parent):
                    raise PatchError(f"array index out of range: {key}")
                parent.pop(idx)
            else:  # pragma: no cover - simple set
                raise PatchError(f"unsupported op {op.get('op')}")
        else:
            raise PatchError("unsupported parent container")
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
