from e2_config_auditing.patching import apply_json_patch, apply_patch_to_text


def test_detect_and_apply_unified_diff() -> None:
    original = "line1\nline2\n"
    patch = """--- file.txt\n+++ file.txt\n@@ -1,2 +1,2 @@\n line1\n-line2\n+lineX\n"""
    new_text = apply_patch_to_text(original, patch)
    assert "lineX" in new_text


def test_json_patch_application() -> None:
    obj = {"a": 1}
    patch_ops = [{"op": "add", "path": "/b", "value": 2}]
    new_obj = apply_json_patch(obj, patch_ops)
    assert new_obj["b"] == 2
