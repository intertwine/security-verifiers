#!/usr/bin/env python3
"""Common paired report for actual bounded-runner outputs; never an empirical gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from statistics import fmean

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict]:
    return (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_output(text: str, environment: str) -> dict | None:
    """Accept a whole JSON object or whole fenced object; never salvage reasoning."""
    match = re.fullmatch(r"\s*```(?:json)?\s*\n?(.*?)\n?```\s*", text, re.DOTALL)
    try:
        data = json.loads(match.group(1) if match else text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    confidence = data.get("confidence")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        return None
    if environment == "e1":
        if set(data) - {"label", "confidence", "rationale"} or not isinstance(data.get("label"), str):
            return None
        if data["label"] not in {"Benign", "Malicious", "Abstain"}:
            return None
        if "rationale" in data and not isinstance(data["rationale"], str):
            return None
    else:
        if set(data) - {"violations", "patch", "confidence"} or not isinstance(data.get("violations"), list):
            return None
        if data.get("patch") is not None and not isinstance(data.get("patch"), str):
            return None
        for finding in data["violations"]:
            if (
                not isinstance(finding, dict)
                or set(finding) != {"id", "severity"}
                or not isinstance(finding["id"], str)
                or finding["severity"] not in {"low", "med", "high"}
            ):
                return None
    return data


def e1_score(row: dict | None, answer: str, costs: dict) -> dict:
    if answer.lower() not in {"malicious", "benign"}:
        raise ValueError("Unknown E1 reference label")
    if row is None:
        return {"status": "missing", "expected_cost": costs["invalid"]}
    if row.get("status") != "completed":
        return {"status": row.get("status", "failed"), "expected_cost": costs["invalid"]}
    parsed = strict_output(row.get("completion", ""), "e1")
    if parsed is None:
        return {"status": "invalid", "expected_cost": costs["invalid"]}
    predicted = parsed["label"].lower()
    if predicted == "abstain":
        return {"status": "abstain", "expected_cost": costs["abstain"]}
    outcome = (
        ("tp" if answer.lower() == "malicious" else "tn")
        if predicted == answer.lower()
        else ("fn" if answer.lower() == "malicious" else "fp")
    )
    return {
        "status": outcome,
        "expected_cost": costs.get(outcome, 0),
        "confidence": parsed["confidence"],
        "correct": outcome in {"tp", "tn"},
    }


def e2_score(row: dict | None, verification: dict | None, answer: dict | str | None = None) -> dict:
    if row is None or row.get("status") != "completed":
        return {
            "status": "missing" if row is None else row.get("status", "failed"),
            "verified_patch_success": 0.0,
        }
    parsed = strict_output(row.get("completion", ""), "e2")
    if parsed is None:
        return {"status": "invalid", "verified_patch_success": 0.0}
    result = {
        "status": "valid",
        "verified_patch_success": None,
        "predicted_finding_ids": sorted({v["id"] for v in parsed["violations"]}),
    }
    oracle_ids = None
    oracle = json.loads(answer) if isinstance(answer, str) else answer
    if isinstance(oracle, dict) and isinstance(oracle.get("oracle", oracle.get("violations")), list):
        findings = oracle.get("oracle", oracle.get("violations"))
        if any(
            not isinstance(f, dict) or not (f.get("id") or (f.get("tool") and f.get("rule_id")))
            for f in findings
        ):
            raise ValueError("E2 reference finding lacks an authentic identifier")
        oracle_ids = {f.get("id") or f"{f['tool']}/{f['rule_id']}" for f in findings}
        predicted_ids = set(result["predicted_finding_ids"])
        tool_style = any(
            identity.startswith(("kube-linter/", "semgrep/", "opa/"))
            for identity in oracle_ids | predicted_ids
        )
        if tool_style:
            prefix = "semgrep/" if oracle.get("fixture_type") in {"tf", "terraform"} else "kube-linter/"
            oracle_ids = {identity for identity in oracle_ids if identity.startswith(prefix)}
            predicted_ids = {identity for identity in predicted_ids if identity.startswith(prefix)}
        result["case_kind"] = "vulnerable" if oracle_ids else "clean"
        tp, fp, fn = (
            len(oracle_ids & predicted_ids),
            len(predicted_ids - oracle_ids),
            len(oracle_ids - predicted_ids),
        )
        result["finding_f1_unique_ids"] = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0
        result["clean_case_false_positive"] = bool(predicted_ids) if not oracle_ids else None
    if verification is not None:
        if oracle_ids is None:
            raise ValueError("E2 verification requires explicit reference findings")
        patch = parsed.get("patch") or ""
        if verification.get("patch_sha256") != hashlib.sha256(patch.encode()).hexdigest():
            raise ValueError("E2 verification is not linked to this exact patch")
        if not oracle_ids:
            if verification.get("verification_protocol") != "clean-no-regression-v1" or not isinstance(
                verification.get("clean_no_regression_success"), bool
            ):
                raise ValueError("Clean cases require explicit no-regression verification protocol")
        fingerprint = hashlib.sha256(row["completion"].encode()).hexdigest()
        if verification.get("completion_sha256") != fingerprint:
            raise ValueError("E2 verification is not linked to this exact completion")
        for key in ("scanner_success", "structure_preserved", "semantic_preserved"):
            if not isinstance(verification.get(key), bool):
                raise ValueError("E2 verification requires explicit scanner/structure/semantic outcomes")
        if not verification.get("tool_versions") or not verification.get("evidence_sha256"):
            raise ValueError("E2 verification requires backend versions and hashed evidence")
        result["verified_patch_success"] = float(
            all(verification[key] for key in ("scanner_success", "structure_preserved", "semantic_preserved"))
            and (bool(patch.strip()) if oracle_ids else verification["clean_no_regression_success"])
        )
        result["verification"] = verification
    return result


def bootstrap_delta(pairs: list[tuple[float, float]], seed: int, resamples: int) -> dict:
    """Policy minus base; draw independent case pairs, not completions."""
    if not pairs:
        return {"n_pairs": 0, "delta": None, "ci95": None}
    deltas = [policy - base for base, policy in pairs]
    samples = []
    rng = random.Random(seed)
    for _ in range(resamples):
        samples.append(fmean(rng.choices(deltas, k=len(deltas))))
    samples.sort()
    return {
        "n_pairs": len(pairs),
        "delta": fmean(deltas),
        "ci95": [samples[int(0.025 * (resamples - 1))], samples[int(0.975 * (resamples - 1))]],
    }


def report(
    run_dir: Path,
    data_root: Path,
    verification_path: Path | None = None,
    seed: int = 20261010,
    resamples: int = 10000,
    costs: dict | None = None,
) -> dict:
    if resamples < 100:
        raise ValueError("At least 100 bootstrap resamples required")
    costs = {"fn": 10.0, "fp": 1.0, "abstain": 1.0, "invalid": 10.0} if costs is None else costs
    if set(costs) != {"fn", "fp", "abstain", "invalid"} or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
        for v in costs.values()
    ):
        raise ValueError("Explicit finite nonnegative loss weights required")
    packet = json.loads((run_dir / "packet.json").read_text())
    frozen_loss = packet.get("environments", {}).get("e1", {}).get("analysis", {}).get("loss")
    if frozen_loss is not None:
        if (
            not isinstance(frozen_loss, dict)
            or set(frozen_loss) != {"false_negative", "false_positive", "abstain", "invalid"}
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                for value in frozen_loss.values()
            )
        ):
            raise ValueError("Frozen loss weights must be explicit finite nonnegative numbers")
        frozen_costs = {
            "fn": frozen_loss["false_negative"],
            "fp": frozen_loss["false_positive"],
            "abstain": frozen_loss["abstain"],
            "invalid": frozen_loss["invalid"],
        }
        if costs != frozen_costs:
            raise ValueError("Reporting loss weights differ from frozen execution packet")
    packet_hash = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    verification = {}
    for row in rows(verification_path) if verification_path else []:
        key = (row["policy_role"], row["case_id"])
        if key in verification:
            raise ValueError("Duplicate E2 verification identity")
        evidence = verification_path.parent / row.get("evidence_path", "")
        if not evidence.is_file() or sha(evidence) != row.get("evidence_sha256"):
            raise ValueError("E2 verification evidence absent or checksum differs")
        witness = json.loads(evidence.read_text())
        fields = (
            "completion_sha256",
            "scanner_success",
            "structure_preserved",
            "semantic_preserved",
            "tool_versions",
            "patch_sha256",
            "verification_protocol",
            "clean_no_regression_success",
        )
        if any(witness.get(field) != row.get(field) for field in fields):
            raise ValueError("E2 verification sidecar differs from linked evidence")
        verification[key] = row
    output = {
        "schema_version": 1,
        "evidence_kind": "observed-paired-evaluation",
        "research_complete": False,
        "packet_sha256": packet_hash,
        "source_fingerprints": json.loads((run_dir / "sources.json").read_text())
        if (run_dir / "sources.json").exists()
        else None,
        "e1_loss_weights": costs,
        "bootstrap": {"seed": seed, "resamples": resamples, "method": "paired percentile case bootstrap"},
        "environments": {},
        "limitations": [
            "Loss weights must be frozen before generating outputs; defaults are a reporting convention, "
            "not historical training rewards.",
            "Intervals require independent cases; input hashes alone do not establish independence.",
            "E2 semantic preservation requires separate hashed verification evidence; "
            "a structural safeguard alone is insufficient.",
            "Observed-pair intervals exclude missing cases and may be biased "
            "when missingness differs by policy; "
            "use complete paired runs for confirmatory claims.",
            "This report cannot create or pass the empirical completion index.",
        ],
    }
    for env, block in packet["environments"].items():
        cases = rows(data_root / block["dataset"])
        ids = [case["case_id"] for case in cases]
        if not ids or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("Frozen cases require unique nonempty identities")
        metric = "expected_cost" if env == "e1" else "verified_patch_success"
        section = {
            "planned_cases": len(cases),
            "metric": metric,
            "direction": "minimize" if env == "e1" else "maximize",
            "independence_verified": block.get("case_independence_verified") is True,
            "policies": {},
            "comparisons": {},
        }
        scored = {}
        for policy in block["policies"]:
            role = policy["role"]
            folder = run_dir / f"{env}-{role}"
            observed = rows(folder / "results.jsonl")
            indexed = {row["case_id"]: row for row in observed}
            if len(indexed) != len(observed) or set(indexed) - set(ids):
                raise ValueError("Duplicate or unexpected result case identity")
            if (folder / "metadata.json").exists():
                metadata = json.loads((folder / "metadata.json").read_text())
                if (
                    metadata["dataset_sha256"] != sha(data_root / block["dataset"])
                    or metadata["packet_sha256"] != packet_hash
                    or metadata["policy"] != policy
                    or metadata["limits"] != block["limits"]
                    or metadata.get("tool_versions") != block.get("tool_versions")
                ):
                    raise ValueError("Result metadata differs from frozen execution packet")
            elif observed:
                raise ValueError("Observed results lack metadata")
            scores = {}
            for case in cases:
                row = indexed.get(case["case_id"])
                if row is not None and (
                    row.get("prompt") != case["question"] or row.get("answer") != case["answer"]
                ):
                    raise ValueError("Result prompt/reference differs from frozen case")
                scores[case["case_id"]] = (
                    e1_score(row, case["answer"], costs)
                    if env == "e1"
                    else e2_score(row, verification.get((role, case["case_id"])), case["answer"])
                )
            scored[role] = (scores, set(indexed))
            values = [score[metric] for score in scores.values() if score[metric] is not None]
            supporting = {}
            if env == "e1":
                accepted = [score for score in scores.values() if "correct" in score]
                supporting["accepted_cases"] = len(accepted)
                supporting["coverage"] = len(accepted) / len(cases)
                supporting["accuracy_non_abstained"] = (
                    fmean(s["correct"] for s in accepted) if accepted else None
                )
                supporting["brier_correctness_non_abstained"] = (
                    fmean((score["confidence"] - int(score["correct"])) ** 2 for score in accepted)
                    if accepted
                    else None
                )
                ece = 0.0
                for bucket in range(10):
                    group = [score for score in accepted if min(int(score["confidence"] * 10), 9) == bucket]
                    if group:
                        ece += (
                            len(group)
                            / len(accepted)
                            * abs(fmean(s["confidence"] for s in group) - fmean(s["correct"] for s in group))
                        )
                supporting["ece_non_abstained"] = ece if accepted else None
            else:
                finding_scores = [
                    s["finding_f1_unique_ids"] for s in scores.values() if "finding_f1_unique_ids" in s
                ]
                supporting["finding_f1_denominator"] = len(finding_scores)
                supporting["verified_case_kind_counts"] = dict(
                    Counter(s.get("case_kind", "unknown") for s in scores.values())
                )
                supporting["finding_f1_unique_ids"] = fmean(finding_scores) if finding_scores else None
            section["policies"][role] = {
                "observed_cases": len(observed),
                "missing_cases": len(ids) - len(observed),
                "outcomes": dict(Counter(s["status"] for s in scores.values())),
                "metric_denominator": len(values),
                "metric_mean": fmean(values) if len(values) == len(cases) else None,
                "metric_observed_subset_mean": fmean(values) if values else None,
                "metric_complete": len(values) == len(cases),
                "case_scores": scores,
                "supporting_metrics": supporting,
            }
        contrasts = [(role, "base") for role in scored if role != "base"]
        if env == "e1" and "exec" in scored and "judge" in scored:
            contrasts.append(("exec", "judge"))
        for role, reference_role in contrasts:
            baseline, base_observed = scored[reference_role]
            scores, observed_ids = scored[role]
            common = [
                identity
                for identity in ids
                if identity in observed_ids & base_observed
                and baseline[identity][metric] is not None
                and scores[identity][metric] is not None
            ]
            comparison = bootstrap_delta(
                [(baseline[i][metric], scores[i][metric]) for i in common], seed, resamples
            )
            comparison.update(
                {
                    "excluded_pairs": len(ids) - len(common),
                    "improvement_direction": "negative" if env == "e1" else "positive",
                    "independence_verified": section["independence_verified"],
                    "policy_role": role,
                    "reference_role": reference_role,
                }
            )
            section["comparisons"][f"{role}_minus_{reference_role}"] = comparison
        output["environments"][env] = section
    return output


def markdown(summary: dict) -> str:
    lines = [
        "# Preserved policy evaluation",
        "",
        "Observed evaluation report. Research completion remains a separate evidence gate.",
        "",
        f"E1 loss weights: `{json.dumps(summary['e1_loss_weights'], sort_keys=True)}`.",
    ]
    for env, section in summary["environments"].items():
        lines += [
            "",
            f"## {env.upper()}",
            "",
            f"Primary metric: {section['metric']}; planned cases: {section['planned_cases']}; "
            f"independence verified: {section['independence_verified']}.",
            "",
            "| Policy | Observed | Missing | Scored denominator | Mean |",
            "|---|---:|---:|---:|---:|",
        ]
        for role, data in section["policies"].items():
            lines.append(
                f"| {role} | {data['observed_cases']} | {data['missing_cases']} | "
                f"{data['metric_denominator']} | {data['metric_mean']} |"
            )
        lines.append("")
        for role, data in section["policies"].items():
            lines.append(f"{role} outcomes: `{json.dumps(data['outcomes'], sort_keys=True)}`")
            lines.append("")
        lines += ["", "Paired differences (policy minus named reference):", ""]
        for role, data in section["comparisons"].items():
            lines.append(
                f"- {role}: delta {data['delta']}, 95% interval {data['ci95']}; "
                f"{data['n_pairs']} pairs, {data['excluded_pairs']} excluded."
            )
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in summary["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--data-root", default=ROOT, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--e2-verification", type=Path)
    parser.add_argument("--loss-weights", type=Path, help="Frozen JSON object fn/fp/abstain/invalid")
    parser.add_argument("--resamples", type=int, default=10000)
    args = parser.parse_args()
    summary = report(
        args.run_dir,
        args.data_root,
        args.e2_verification,
        resamples=args.resamples,
        costs=json.loads(args.loss_weights.read_text()) if args.loss_weights else None,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "report.md").write_text(markdown(summary))


if __name__ == "__main__":
    main()
