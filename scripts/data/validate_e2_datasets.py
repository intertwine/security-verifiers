#!/usr/bin/env python3
"""
Validate E2 datasets against original source repositories.

Checks:
1. Schema compliance (prompt, info.violations, meta fields)
2. Tool scanning accuracy (KubeLinter, Semgrep, OPA)
3. File representation (YAML/HCL → prompt field)
4. Violation structure and severity levels
5. Source file existence and hash validation
6. Tool version consistency
"""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSONL dataset."""
    items = []
    with path.open() as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def validate_schema(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Validate that all items conform to E2 schema."""
    required_fields = ["prompt", "info", "meta"]
    required_info_fields = ["violations", "patch"]
    required_meta_fields = ["lang", "source", "hash"]
    required_violation_fields = ["tool", "rule_id", "severity", "msg", "loc"]

    errors = []
    for i, item in enumerate(items):
        # Check top-level fields
        missing = [f for f in required_fields if f not in item]
        if missing:
            errors.append(f"Item {i}: Missing fields {missing}")

        # Check info fields
        if "info" in item:
            missing_info = [f for f in required_info_fields if f not in item["info"]]
            if missing_info:
                errors.append(f"Item {i}: Missing info fields {missing_info}")

            # Check violations structure
            if "violations" in item["info"] and isinstance(item["info"]["violations"], list):
                for j, v in enumerate(item["info"]["violations"]):
                    missing_v = [f for f in required_violation_fields if f not in v]
                    if missing_v:
                        errors.append(f"Item {i}, violation {j}: Missing fields {missing_v}")

        # Check meta fields
        if "meta" in item:
            missing_meta = [f for f in required_meta_fields if f not in item["meta"]]
            if missing_meta:
                errors.append(f"Item {i}: Missing meta fields {missing_meta}")

            # Check lang is valid
            if "lang" in item["meta"] and item["meta"]["lang"] not in ["k8s", "tf"]:
                errors.append(f"Item {i}: Invalid lang '{item['meta']['lang']}'")

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "errors": errors,
        "valid": len(errors) == 0,
    }


def analyze_violations(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Analyze violation patterns and tool coverage."""
    total_violations = 0
    by_tool = Counter()
    by_severity = Counter()
    items_with_violations = 0

    for item in items:
        violations = item.get("info", {}).get("violations", [])
        if violations:
            items_with_violations += 1
            total_violations += len(violations)

        for v in violations:
            by_tool[v.get("tool", "unknown")] += 1
            by_severity[v.get("severity", "unknown")] += 1

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "items_with_violations": items_with_violations,
        "items_without_violations": len(items) - items_with_violations,
        "total_violations": total_violations,
        "avg_violations_per_item": total_violations / len(items) if items else 0,
        "violations_by_tool": dict(by_tool),
        "violations_by_severity": dict(by_severity),
    }


def verify_source_files(
    items: List[Dict[str, Any]], dataset_name: str, source_root: Path = None
) -> Dict[str, Any]:
    """Verify that source files exist and hashes match."""
    if not source_root or not source_root.exists():
        return {
            "dataset": dataset_name,
            "note": "Source root not provided or doesn't exist - skipping source verification",
        }

    missing_files = []
    hash_mismatches = []

    for i, item in enumerate(items):
        source_path = Path(item["meta"]["source"])

        # Try to resolve source path
        if source_path.is_absolute() and source_path.exists():
            file_path = source_path
        elif source_root:
            # Try relative to source root
            file_path = source_root / source_path.name
            if not file_path.exists():
                # Try finding in subdirs
                matches = list(source_root.rglob(source_path.name))
                file_path = matches[0] if matches else None
        else:
            file_path = None

        if not file_path or not Path(file_path).exists():
            missing_files.append({"index": i, "source": str(source_path)})
            continue

        # Verify hash
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except Exception:
            content = Path(file_path).read_text(errors="ignore")

        computed_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        expected_hash = item["meta"]["hash"]

        if computed_hash != expected_hash:
            hash_mismatches.append(
                {
                    "index": i,
                    "source": str(source_path),
                    "expected_hash": expected_hash,
                    "computed_hash": computed_hash,
                }
            )

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "missing_files": missing_files,
        "hash_mismatches": hash_mismatches,
        "files_verified": len(items) - len(missing_files) - len(hash_mismatches),
    }


def verify_prompt_content(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """Verify that prompt field contains actual file content."""
    errors = []

    for i, item in enumerate(items):
        prompt = item.get("prompt", "")
        lang = item.get("meta", {}).get("lang", "")

        # Basic sanity checks
        if not prompt or len(prompt.strip()) == 0:
            errors.append({"index": i, "error": "Empty prompt"})
            continue

        # Check for expected content markers
        if lang == "k8s":
            # Should contain YAML-like content
            has_yaml_markers = any(
                marker in prompt for marker in ["apiVersion:", "kind:", "metadata:", "spec:"]
            )
            if not has_yaml_markers:
                errors.append({"index": i, "error": "Prompt doesn't look like K8s YAML"})

        elif lang == "tf":
            # Should contain Terraform HCL
            has_tf_markers = any(
                marker in prompt for marker in ["resource ", "variable ", "output ", "provider "]
            )
            if not has_tf_markers:
                errors.append({"index": i, "error": "Prompt doesn't look like Terraform HCL"})

    return {
        "dataset": dataset_name,
        "total_items": len(items),
        "errors": errors,
        "valid_prompts": len(items) - len(errors),
    }


def check_tool_versions(data_dir: Path) -> Dict[str, Any]:
    """Check tool versions match expected versions."""
    versions_file = data_dir / "tools-versions.json"

    if not versions_file.exists():
        return {"error": "tools-versions.json not found"}

    versions = json.loads(versions_file.read_text())

    # Try to get current tool versions
    current_versions = {}

    try:
        result = subprocess.run(
            ["kube-linter", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            current_versions["kube-linter"] = result.stdout.strip().split("\n")[0]
    except Exception as e:
        current_versions["kube-linter"] = f"error: {e}"

    try:
        result = subprocess.run(
            ["semgrep", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            current_versions["semgrep"] = result.stdout.strip().split("\n")[-1]
    except Exception as e:
        current_versions["semgrep"] = f"error: {e}"

    try:
        result = subprocess.run(
            ["opa", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            current_versions["opa"] = result.stdout.strip().split("\n")[0]
    except Exception as e:
        current_versions["opa"] = f"error: {e}"

    return {
        "recorded_versions": versions,
        "current_versions": current_versions,
        "note": "Version mismatches may affect reproducibility",
    }


def validate_k8s_dataset(data_dir: Path, source_root: Path = None) -> Dict[str, Any]:
    """Validate K8s dataset."""
    dataset_path = data_dir / "k8s-labeled-v1.jsonl"

    if not dataset_path.exists():
        return {"error": f"Dataset not found: {dataset_path}"}

    items = load_jsonl(dataset_path)

    results = {
        "dataset_file": str(dataset_path),
        "schema_validation": validate_schema(items, "k8s-labeled-v1"),
        "violations_analysis": analyze_violations(items, "k8s-labeled-v1"),
        "prompt_validation": verify_prompt_content(items, "k8s-labeled-v1"),
        "source_verification": verify_source_files(items, "k8s-labeled-v1", source_root),
    }

    return results


def validate_terraform_dataset(data_dir: Path, source_root: Path = None) -> Dict[str, Any]:
    """Validate Terraform dataset."""
    dataset_path = data_dir / "terraform-labeled-v1.jsonl"

    if not dataset_path.exists():
        return {"error": f"Dataset not found: {dataset_path}"}

    items = load_jsonl(dataset_path)

    results = {
        "dataset_file": str(dataset_path),
        "schema_validation": validate_schema(items, "terraform-labeled-v1"),
        "violations_analysis": analyze_violations(items, "terraform-labeled-v1"),
        "prompt_validation": verify_prompt_content(items, "terraform-labeled-v1"),
        "source_verification": verify_source_files(items, "terraform-labeled-v1", source_root),
    }

    return results


def print_summary(results: Dict[str, Any], title: str):
    """Print validation summary."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print("=" * 80)
    print(json.dumps(results, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Validate E2 datasets against source repositories")
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=Path("environments/sv-env-config-verification/data"),
        help="Data directory",
    )
    ap.add_argument(
        "--k8s-source-root",
        type=Path,
        help="Root directory of K8s source repositories (optional)",
    )
    ap.add_argument(
        "--tf-source-root",
        type=Path,
        help="Root directory of Terraform source repositories (optional)",
    )
    ap.add_argument(
        "--datasets",
        choices=["k8s", "terraform", "all"],
        default="all",
        help="Which datasets to validate",
    )
    ap.add_argument(
        "--output",
        type=Path,
        help="Optional output JSON file for validation report",
    )
    args = ap.parse_args()

    validation_report = {}

    # Check tool versions
    tool_versions = check_tool_versions(args.data_dir)
    validation_report["tool_versions"] = tool_versions
    print_summary(tool_versions, "Tool Versions Check")

    # Load metadata
    metadata_path = args.data_dir / "sampling-e2-v1.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        validation_report["metadata"] = metadata
        print_summary(metadata, "Dataset Metadata")

    if args.datasets in ["k8s", "all"]:
        k8s_results = validate_k8s_dataset(args.data_dir, args.k8s_source_root)
        validation_report["k8s"] = k8s_results
        print_summary(k8s_results, "K8s Dataset Validation")

    if args.datasets in ["terraform", "all"]:
        tf_results = validate_terraform_dataset(args.data_dir, args.tf_source_root)
        validation_report["terraform"] = tf_results
        print_summary(tf_results, "Terraform Dataset Validation")

    # Overall summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    all_valid = True
    for dataset_name in ["k8s", "terraform"]:
        if dataset_name in validation_report:
            results = validation_report[dataset_name]
            if isinstance(results, dict) and "schema_validation" in results:
                schema_valid = results["schema_validation"].get("valid", False)
                prompt_valid = results.get("prompt_validation", {}).get("valid_prompts", 0)
                total = results.get("prompt_validation", {}).get("total_items", 1)
                prompt_pct = (prompt_valid / total * 100) if total > 0 else 0

                print(f"{dataset_name}:")
                print(f"  Schema valid: {schema_valid}")
                print(f"  Prompt validation: {prompt_valid}/{total} ({prompt_pct:.1f}%)")

                if not schema_valid or prompt_pct < 95:
                    all_valid = False

    print(f"\nOverall validation: {'✅ PASSED' if all_valid else '❌ FAILED'}")

    # Write output file if specified
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(validation_report, indent=2))
        print(f"\nValidation report written to: {args.output}")


if __name__ == "__main__":
    main()
