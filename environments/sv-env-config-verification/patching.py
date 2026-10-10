"""Patch application utilities."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import yaml

PatchFormat = Literal["unified-diff", "json-patch"]


class PatchError(RuntimeError):
    """Raised when a patch cannot be applied."""


def preserves_config_structure(original: str, patched: str, fixture_type: str) -> bool:
    """Reject resource/container deletion before awarding scanner-removal credit.

    This is a structural safeguard, not a proof of functional equivalence.
    """
    if not patched.strip():
        return False
    if fixture_type == "tf":
        resource = re.compile(r'^\s*resource\s+"([^"\n]+)"\s+"([^"\n]+)"\s*\{', re.MULTILINE)

        def without_comments(text: str) -> str:
            # HCL comment delimiters inside strings are literal text. Replace
            # real comments with whitespace so inactive declarations cannot
            # count as retained resources or concatenate neighboring tokens.
            output: list[str] = []
            index = 0
            quoted = False
            while index < len(text):
                char = text[index]
                if quoted:
                    if char in "\r\n":
                        return ""  # HCL quoted strings cannot span raw lines.
                    output.append(char)
                    index += 1
                    if char == "\\" and index < len(text):
                        output.append(text[index])
                        index += 1
                    elif char == '"':
                        quoted = False
                elif char == '"':
                    quoted = True
                    output.append(char)
                    index += 1
                elif text.startswith("<<", index):
                    # This guard is not an HCL parser. Fail closed on heredocs
                    # rather than treating resource-looking string contents as
                    # active declarations.
                    return ""
                elif text.startswith("/*", index):
                    end = text.find("*/", index + 2)
                    if end < 0:
                        return ""
                    output.extend("\n" if c == "\n" else " " for c in text[index : end + 2])
                    index = end + 2
                elif char == "#" or text.startswith("//", index):
                    end = text.find("\n", index)
                    if end < 0:
                        break
                    output.append("\n")
                    index = end + 1
                else:
                    output.append(char)
                    index += 1
            return "" if quoted else "".join(output)

        before = set(resource.findall(without_comments(original)))
        after = set(resource.findall(without_comments(patched)))
        return bool(before) and before <= after
    if fixture_type != "k8s":
        return False

    def identities(text: str) -> dict[tuple[str, ...], set[tuple[tuple[str, ...], str]]]:
        resources = {}
        for doc in yaml.safe_load_all(text):
            if not isinstance(doc, dict):
                raise TypeError("expected Kubernetes resource")
            docs = doc.get("items", []) if doc.get("kind") == "List" else [doc]
            for item in docs:
                metadata = item.get("metadata", {})
                identity = (
                    item["apiVersion"],
                    item["kind"],
                    metadata.get("namespace", "default"),
                    metadata["name"],
                )
                containers: set[tuple[tuple[str, ...], str]] = set()

                def collect(
                    value: object,
                    names: set[tuple[tuple[str, ...], str]],
                    path: tuple[str, ...] = (),
                ) -> None:
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key in {"containers", "initContainers", "ephemeralContainers"}:
                                for container in child:
                                    names.add(((*path, key), container["name"]))
                            else:
                                collect(child, names, (*path, key))
                    elif isinstance(value, list):
                        for index, child in enumerate(value):
                            collect(child, names, (*path, str(index)))

                collect(item, containers)
                if identity in resources:
                    raise ValueError("duplicate Kubernetes resource")
                resources[identity] = containers
        return resources

    try:
        before, after = identities(original), identities(patched)
        return bool(before) and all(key in after and names <= after[key] for key, names in before.items())
    except (yaml.YAMLError, KeyError, TypeError, AttributeError, ValueError):
        return False


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


def try_apply_patch(path: str, patch: str) -> tuple[bool, str]:
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
    "PatchError",
    "PatchFormat",
    "apply_json_patch",
    "apply_patch_to_text",
    "detect_patch_format",
    "try_apply_patch",
]
