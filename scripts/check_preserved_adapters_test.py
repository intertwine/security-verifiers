"""Regression tests for model-specific LoRA shape validation."""

import copy

import pytest
from check_preserved_adapters import compare_shapes, expected_shapes


def config(family="qwen3_5"):
    text = {
        "hidden_size": 8,
        "intermediate_size": 12,
        "num_hidden_layers": 2,
        "head_dim": 2,
        "num_attention_heads": 4,
        "num_key_value_heads": 2,
        "layer_types": ["linear_attention", "full_attention"],
        "attn_output_gate": True,
    }
    return (
        {"model_type": family, "text_config": text}
        if family == "qwen3_5"
        else {"model_type": family, **text, "attn_output_gate": False}
    )


def test_qwen35_gated_query_and_hybrid_layers():
    shapes = expected_shapes(config(), 2)
    assert len(shapes) == 20
    assert shapes["model.language_model.layers.1.self_attn.q_proj.lora_B.weight"] == [16, 2]
    assert not any("layers.0.self_attn" in key for key in shapes)


def test_qwen3_full_attention_uses_original_prefix_and_projection_width():
    shapes = expected_shapes(config("qwen3"), 2)
    assert len(shapes) == 28
    assert shapes["model.layers.0.self_attn.q_proj.lora_B.weight"] == [8, 2]


def test_missing_unpaired_tensor_and_shape_mismatch_are_rejected():
    shapes = expected_shapes(config(), 2)
    header = {key: {"shape": shape} for key, shape in shapes.items()}
    assert compare_shapes(header, shapes) == []
    modified = copy.deepcopy(header)
    modified.pop(next(iter(modified)))
    key = next(iter(modified))
    modified[key]["shape"] = [999, 2]
    modified["foreign.module"] = {"shape": [2, 2]}
    errors = compare_shapes(modified, shapes)
    assert len(errors) == 3


def test_unknown_architecture_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        expected_shapes(config("unknown"), 2)


def make_archive(tmp_path, mutate=None):
    import json
    import struct
    import zipfile

    shapes = expected_shapes(config(), 2)
    header = {}
    cursor = 0
    for key, shape in shapes.items():
        end = cursor + 4 * shape[0] * shape[1]
        header[key] = {"shape": shape, "dtype": "F32", "data_offsets": [cursor, end]}
        cursor = end
    if mutate:
        mutate(header)
    encoded = json.dumps(header).encode()
    path = tmp_path / "adapter.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "adapter_config.json",
            json.dumps({"base_model_name_or_path": "Qwen/test", "peft_type": "LORA", "r": 2}),
        )
        archive.writestr(
            "adapter_model.safetensors", struct.pack("<Q", len(encoded)) + encoded + bytes(cursor)
        )
    return path, {"repository": "Qwen/test", "config": config(), "observed_revision": "a" * 40}


def test_zip_check_does_not_claim_runtime_or_historical_revision(tmp_path):
    from check_preserved_adapters import check_adapter

    path, reference = make_archive(tmp_path)
    result = check_adapter(path, reference)
    assert result["structural_compatibility"]
    assert not result["runtime_load_verified"]
    assert not result["historical_base_revision_proven"]


def test_overlapping_tensor_payload_rejected(tmp_path):
    from check_preserved_adapters import check_adapter

    def mutate(header):
        value = list(header.values())[1]
        value["data_offsets"] = [0, value["data_offsets"][1] - value["data_offsets"][0]]

    path, reference = make_archive(tmp_path, mutate)
    result = check_adapter(path, reference)
    assert not result["structural_compatibility"]
    assert "tensor offsets overlap or contain gaps" in result["errors"]


def test_wrong_base_model_rejected(tmp_path):
    from check_preserved_adapters import check_adapter

    path, reference = make_archive(tmp_path)
    reference["repository"] = "Qwen/other"
    with pytest.raises(ValueError, match="differs"):
        check_adapter(path, reference)
