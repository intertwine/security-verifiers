#!/usr/bin/env python3
"""
Scan K8s YAML and Terraform HCL with pinned tools (KubeLinter, Semgrep, OPA),
emit SV E2 JSONLs, and optionally create a patch-verified subset by re-scanning after patch.

Outputs (under environments/sv-env-config-verification/data/):
  - k8s-labeled-v1.jsonl
  - terraform-labeled-v1.jsonl
  - k8s-patch-verified-v1.jsonl          # optional, when --patches-dir provided
  - tools-versions.json                   # exact tool versions used
  - sampling-e2-v1.json                   # sampling metadata
"""

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

KUBELINTER = os.environ.get("KUBELINTER", "kube-linter")
SEMGREP = os.environ.get("SEMGREP", "semgrep")
OPA = os.environ.get("OPA", "opa")


def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out, err


def get_version(binary: str, flag: str = "version") -> str:
    """Get version string for a binary.

    Args:
        binary: Path to the binary
        flag: Version flag or subcommand (default: "version")

    Returns:
        Version string or "unknown" if detection fails
    """
    rc, out, _ = run([binary, flag])
    if rc == 0:
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        if not lines:
            return "unknown"
        # For semgrep (--version flag), version is on last line after warnings
        # For others (version subcommand), version is on first line
        if flag.startswith("--"):
            return lines[-1]
        else:
            return lines[0]
    return "unknown"


def is_valid_k8s_manifest(path: Path) -> bool:
    """Check if file contains valid K8s manifest."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # Skip empty files
    if not content.strip():
        return False

    # Check for K8s API markers (need at least 2 to be confident)
    k8s_markers = ["apiVersion:", "kind:", "metadata:", "spec:"]
    marker_count = sum(1 for marker in k8s_markers if marker in content)
    return marker_count >= 2


def is_valid_hcl(path: Path) -> bool:
    """Check if file contains valid Terraform HCL."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    # Skip empty files
    if not content.strip():
        return False

    # Check for HCL block markers
    hcl_markers = ["resource ", "module ", "data ", "variable ", "output ", "provider ", "terraform "]
    return any(marker in content for marker in hcl_markers)


def find_files(root: Path, exts: Tuple[str, ...], validator=None) -> List[Path]:
    """Find files by extension, optionally filtering by content validator."""
    files = [p for p in root.rglob("*") if p.suffix.lower() in exts and p.is_file()]
    if validator:
        original_count = len(files)
        files = [f for f in files if validator(f)]
        filtered_count = original_count - len(files)
        if filtered_count > 0:
            print(f"  Filtered out {filtered_count} invalid files (empty or wrong content)")
    return files


def kubelinter_scan(path: Path) -> List[Dict[str, Any]]:
    rc, out, err = run([KUBELINTER, "lint", str(path), "--format", "json"])
    if rc != 0 and not out.strip():
        # kube-linter exits nonzero when issues found; still parse stdout
        pass
    try:
        data = json.loads(out or "{}")
    except json.JSONDecodeError:
        return []
    if data is None:
        return []
    issues = []
    for d in data.get("Reports", []) or []:
        issues.append(
            {
                "tool": "kube-linter",
                "rule_id": d.get("Check", ""),
                "severity": d.get("Severity", "").lower() or "medium",
                "msg": d.get("Remediation", "") or d.get("Reason", ""),
                "loc": d.get("Object", {}).get("K8sObject", {}).get("Object", ""),
            }
        )
    return issues


def semgrep_scan(path: Path, lang: str) -> List[Dict[str, Any]]:
    # Use community rulesets; for TF: p/terraform; for K8s YAML: p/kubernetes
    ruleset = "p/kubernetes" if lang == "k8s" else "p/terraform"
    rc, out, err = run([SEMGREP, "scan", "--json", "--quiet", "--config", ruleset, str(path)])
    if rc not in (0, 1):  # 1 means findings found
        return []
    data = json.loads(out or "{}")
    issues = []
    for r in data.get("results", []):
        issues.append(
            {
                "tool": "semgrep",
                "rule_id": r.get("check_id", ""),
                "severity": (r.get("extra", {}) or {}).get("severity", "unknown"),
                "msg": (r.get("extra", {}) or {}).get("message", ""),
                "loc": f"{r.get('path', '')}:{r.get('start', {}).get('line', '')}",
            }
        )
    return issues


def opa_eval_policies(path: Path, rego_dir: Path) -> List[Dict[str, Any]]:
    # Evaluate all .rego in rego_dir against the file content; expect boolean "deny" results
    if not rego_dir or not rego_dir.exists():
        return []
    policies = list(rego_dir.glob("*.rego"))
    issues = []
    for rego in policies:
        # Assume package provides 'deny' set of strings
        rc, out, err = run([OPA, "eval", "-f", "json", "-d", str(rego), "-I", str(path), "data.deny"])
        if rc != 0:
            continue
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue
        for r in data.get("result") or []:
            for expr in r.get("expressions", []):
                val = expr.get("value") or []
                for msg in val:
                    issues.append(
                        {"tool": "opa", "rule_id": rego.stem, "severity": "high", "msg": str(msg), "loc": ""}
                    )
    return issues


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return p.read_text(errors="ignore")


def emit_items(files: List[Path], lang: str, rego_dir: Path, out_path: Path) -> List[Dict[str, Any]]:
    items = []
    with out_path.open("w") as w:
        for f in files:
            raw = read_text(f)
            issues = []
            if lang == "k8s":
                issues += kubelinter_scan(f)
                issues += semgrep_scan(f, "k8s")
            else:
                issues += semgrep_scan(f, "tf")
            issues += opa_eval_policies(f, rego_dir)
            item = {
                "prompt": raw,
                "info": {"violations": issues, "patch": None},
                "meta": {"lang": lang, "source": str(f), "hash": hashlib(raw)},
            }
            items.append(item)
            w.write(json.dumps(item) + "\n")
    return items


def hashlib(s: str) -> str:
    import hashlib as H

    return H.sha256(s.encode()).hexdigest()[:16]


def make_patch_verified(k8s_items_path: Path, patches_dir: Path, out_path: Path, rego_dir: Path):
    """
    For files with corresponding patch (*.patch or *.diff) in patches_dir,
    apply patch, re-scan, and keep only those where primary-oracle violations are gone.
    """
    import difflib
    import tempfile

    # Simple JSONL reader
    items = [json.loads(line) for line in k8s_items_path.read_text().splitlines() if line.strip()]
    kept = []
    for it in items:
        src = Path(it["meta"]["source"])
        patch_file = patches_dir / (src.name + ".patch")
        if not patch_file.exists():
            continue
        # Apply unified diff in memory (best-effort)
        diff = patch_file.read_text().splitlines(keepends=True)
        try:
            patched = list(difflib.restore(diff, which=2))  # If diff was generated via difflib.ndiff
        except Exception:
            # Fallback: naive replacement when diff is a full file content
            patched = patch_file.read_text().splitlines(keepends=True)
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp:
            tmp.writelines(patched)
            tmp_path = Path(tmp.name)

        # Re-scan with OPA as primary oracle + tools as corroboration
        issues_after = (
            opa_eval_policies(tmp_path, rego_dir) + kubelinter_scan(tmp_path) + semgrep_scan(tmp_path, "k8s")
        )
        if not any(v for v in issues_after if v["tool"] == "opa"):
            kept.append(
                {
                    "prompt": "".join(patched),
                    "info": {"violations": it["info"]["violations"], "patch": patch_file.read_text()},
                    "meta": {**it["meta"], "patch_source": str(patch_file)},
                }
            )
    out_path.write_text("\n".join(map(json.dumps, kept)) + ("\n" if kept else ""))
    return len(kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k8s-root", type=Path, required=True, help="Directory of Kubernetes YAML manifests")
    ap.add_argument("--tf-root", type=Path, required=True, help="Directory of Terraform modules")
    ap.add_argument(
        "--rego-dir",
        type=Path,
        default=Path("environments/sv-env-config-verification/policies"),
        help="OPA/Rego policy folder (primary oracle)",
    )
    ap.add_argument("--patches-dir", type=Path, help="Optional directory of minimal patches for a subset")
    ap.add_argument("--outdir", type=Path, default=Path("environments/sv-env-config-verification/data"))
    ap.add_argument(
        "--mode",
        choices=["full", "test"],
        default="full",
        help="Build mode: 'full' for production (uploaded to HF), 'test' for CI fixtures",
    )
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    # Choose filename suffix based on mode
    suffix = "-test" if args.mode == "test" else "-v1"

    # Tool versions record
    versions = {
        "kube-linter": get_version(KUBELINTER),
        "semgrep": get_version(SEMGREP, "--version"),
        "opa": get_version(OPA),
    }
    (args.outdir / "tools-versions.json").write_text(json.dumps(versions, indent=2))

    print(f"Scanning K8s manifests in {args.k8s_root}...")
    k8s_files = find_files(args.k8s_root, (".yml", ".yaml"), validator=is_valid_k8s_manifest)
    print(f"  Found {len(k8s_files)} valid K8s manifests")

    print(f"\nScanning Terraform files in {args.tf_root}...")
    tf_files = find_files(args.tf_root, (".tf",), validator=is_valid_hcl)
    print(f"  Found {len(tf_files)} valid Terraform files")

    k8s_items = emit_items(k8s_files, "k8s", args.rego_dir, args.outdir / f"k8s-labeled{suffix}.jsonl")
    tf_items = emit_items(tf_files, "tf", args.rego_dir, args.outdir / f"terraform-labeled{suffix}.jsonl")

    patch_verified_count = 0
    if args.patches_dir and args.patches_dir.exists():
        patch_verified_count = make_patch_verified(
            args.outdir / f"k8s-labeled{suffix}.jsonl",
            args.patches_dir,
            args.outdir / f"k8s-patch-verified{suffix}.jsonl",
            args.rego_dir,
        )
        print(f"Patch-verified K8s items: {patch_verified_count}")

    # Write sampling metadata
    sampling_path = args.outdir / f"sampling-e2{suffix}.json"
    stats = {
        "mode": args.mode,
        "k8s_root": str(args.k8s_root),
        "tf_root": str(args.tf_root),
        "rego_dir": str(args.rego_dir),
        "datasets": {
            "k8s": {
                "files_scanned": len(k8s_files),
                "total_items": len(k8s_items),
                "with_violations": sum(1 for x in k8s_items if x["info"]["violations"]),
            },
            "terraform": {
                "files_scanned": len(tf_files),
                "total_items": len(tf_items),
                "with_violations": sum(1 for x in tf_items if x["info"]["violations"]),
            },
        },
        "tools": versions,
        "patch_verified": patch_verified_count if args.patches_dir else None,
    }
    if args.mode == "test":
        stats["warning"] = "CI fixture only - not for evaluation"

    sampling_path.write_text(json.dumps(stats, indent=2))

    print(f"Done. Outputs in {args.outdir}. Tool versions: {versions}")
    print(f"Sampling metadata: {stats}")


if __name__ == "__main__":
    main()
