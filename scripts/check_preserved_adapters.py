#!/usr/bin/env python3
"""Check preserved LoRA tensor shapes against pinned base config snapshots, offline.

A successful check establishes structural compatibility, not the historical base
weight revision, numerical validity, successful loading or generation quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path


def expected_shapes(config: dict, rank: int) -> dict[str, list[int]]:
    """Model-specific projection shapes for supported dense Qwen families."""
    family = config["model_type"]
    if family not in {"qwen3", "qwen3_5"}:
        raise ValueError(f"Unsupported base architecture: {family}")
    text = config.get("text_config", config)
    hidden, intermediate = text["hidden_size"], text["intermediate_size"]
    attention = text["head_dim"] * text["num_attention_heads"]
    kv = text["head_dim"] * text["num_key_value_heads"]
    prefix = "model.language_model" if family == "qwen3_5" else "model"
    shapes = {}
    for layer in range(text["num_hidden_layers"]):
        modules = {
            "mlp.down_proj": (intermediate, hidden),
            "mlp.gate_proj": (hidden, intermediate),
            "mlp.up_proj": (hidden, intermediate),
        }
        full_attention = family == "qwen3" or text["layer_types"][layer] == "full_attention"
        if full_attention:
            modules.update(
                {
                    "self_attn.q_proj": (hidden, attention * (2 if text.get("attn_output_gate") else 1)),
                    "self_attn.k_proj": (hidden, kv),
                    "self_attn.v_proj": (hidden, kv),
                    "self_attn.o_proj": (attention, hidden),
                }
            )
        for module, (incoming, outgoing) in modules.items():
            key = f"{prefix}.layers.{layer}.{module}"
            shapes[f"{key}.lora_A.weight"] = [rank, incoming]
            shapes[f"{key}.lora_B.weight"] = [outgoing, rank]
    return shapes


def compare_shapes(header: dict, expected: dict) -> list[str]:
    actual = {key: value["shape"] for key, value in header.items() if key != "__metadata__"}
    errors = [f"missing tensor: {key}" for key in expected.keys() - actual.keys()]
    errors += [f"unexpected tensor: {key}" for key in actual.keys() - expected.keys()]
    errors += [
        f"shape mismatch: {key}: {actual[key]} != {expected[key]}"
        for key in actual.keys() & expected.keys()
        if actual[key] != expected[key]
    ]
    return sorted(errors)


def check_adapter(path: Path, reference: dict) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP member names")
        failed = archive.testzip()
        if failed:
            raise ValueError(f"ZIP CRC failed: {failed}")
        adapter = json.loads(archive.read("adapter_config.json"))
        if adapter["base_model_name_or_path"] != reference["repository"]:
            raise ValueError("Adapter base model differs from config reference")
        if adapter["peft_type"] != "LORA" or adapter.get("modules_to_save"):
            raise ValueError("Unsupported adapter type or saved non-LoRA modules")
        expected = expected_shapes(reference["config"], adapter["r"])
        with archive.open("adapter_model.safetensors") as stream:
            length_bytes = stream.read(8)
            length = struct.unpack("<Q", length_bytes)[0]
            if length > 16 * 1024 * 1024:
                raise ValueError("Unexpectedly large safetensors header")
            header = json.loads(stream.read(length))
        errors = compare_shapes(header, expected)
        payload_bytes = archive.getinfo("adapter_model.safetensors").file_size - 8 - length
        widths = {"F32": 4, "BF16": 2, "F16": 2}
        spans = []
        for key, value in header.items():
            if key == "__metadata__":
                continue
            begin, end = value["data_offsets"]
            shape = value["shape"]
            width = widths.get(value["dtype"])
            if width is None or len(shape) != 2 or begin < 0 or end > payload_bytes:
                errors.append(f"invalid tensor encoding: {key}")
            elif end - begin != width * shape[0] * shape[1]:
                errors.append(f"invalid tensor byte count: {key}")
            spans.append((begin, end))
        cursor = 0
        for begin, end in sorted(spans):
            if begin != cursor or end < begin:
                errors.append("tensor offsets overlap or contain gaps")
            cursor = end
        if cursor != payload_bytes:
            errors.append("unreferenced or truncated tensor payload")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "run_id": path.stem,
        "adapter_zip_sha256": digest.hexdigest(),
        "base_model": adapter["base_model_name_or_path"],
        "reference_config_revision": reference["observed_revision"],
        "historical_base_revision_proven": False,
        "adapter_revision_field": adapter.get("revision"),
        "tensor_count": len(spans),
        "rank": adapter["r"],
        "structural_compatibility": not errors,
        "errors": sorted(set(errors)),
        "runtime_load_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapters", required=True, type=Path)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    refs = {
        ref["repository"]: ref
        for file in args.references.glob("*.json")
        if "repository" in (ref := json.loads(file.read_text()))
    }
    rows = []
    for path in sorted(args.adapters.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            base = json.loads(archive.read("adapter_config.json"))["base_model_name_or_path"]
        rows.append(check_adapter(path, refs[base]))
    if not rows:
        raise ValueError("No adapter archives found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2) + "\n")
    print(
        f"Checked {len(rows)} adapters; structural matches: "
        f"{sum(row['structural_compatibility'] for row in rows)}; historical revision proof: 0"
    )
    return int(any(not row["structural_compatibility"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
