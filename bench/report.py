#!/usr/bin/env python3
"""SV-Bench Report Generator.

Generates summary.json and report.md from evaluation rollout results.

Usage:
    python -m bench.report --env e1 --input outputs/evals/network-logs--gpt-5-mini/run_123/
    python -m bench.report --env e2 --input outputs/evals/config-verification--gpt-5-mini/run_456/
    uv run svbench_report --env e1 --input outputs/evals/...
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import fmean
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sv_shared.parsers import extract_json_from_markdown  # noqa: E402

# ============================================================================
# Helpers
# ============================================================================

SEV_WEIGHT = {"low": 0.3, "med": 0.6, "high": 1.0}
TOOL_NAMES = ["opa", "kube-linter", "semgrep"]
TOOL_NAME_MAP = {
    "run_opa": "opa",
    "opa": "opa",
    "run_kubelinter": "kube-linter",
    "kube-linter": "kube-linter",
    "run_semgrep": "semgrep",
    "semgrep": "semgrep",
}


@lru_cache
def _load_summary_schema() -> dict[str, Any]:
    """Load summary.json schema definition."""
    schema_path = REPO_ROOT / "bench" / "schemas" / "summary.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_summary(summary: dict[str, Any]) -> None:
    """Validate summary dict against the schema."""
    schema = _load_summary_schema()
    try:
        jsonschema.validate(summary, schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"Summary schema validation failed: {exc.message}") from exc


def _mean(values: list[float]) -> float:
    """Compute mean of a list, returning 0.0 for empty lists."""
    return fmean(values) if values else 0.0


def _normalize_severity(value: Any) -> str:
    """Normalize severity strings to low/med/high with 'med' fallback."""
    sev = str(value).lower() if value is not None else "med"
    if sev == "medium":
        sev = "med"
    if sev == "critical":
        sev = "high"
    return sev if sev in SEV_WEIGHT else "med"


def _load_json_from_text(text: str) -> dict[str, Any] | None:
    """Attempt to parse JSON from raw text or markdown-wrapped JSON."""
    if not text:
        return None
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    extracted = extract_json_from_markdown(text)
    if extracted != text:
        try:
            data = json.loads(extracted)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _normalize_violation_list(raw: Any) -> list[dict[str, Any]]:
    """Normalize violations to dicts with id + severity fields."""
    violations: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            vid = item.get("id")
            rule_id = item.get("rule_id")
            tool = item.get("tool")
            if not vid:
                if rule_id and tool:
                    tool_name = TOOL_NAME_MAP.get(str(tool), str(tool))
                    vid = f"{tool_name}/{rule_id}"
                else:
                    vid = rule_id
            if not vid:
                continue
            violations.append({"id": str(vid), "severity": _normalize_severity(item.get("severity", "med"))})
    return violations


def _normalize_primary_tool_ids(
    violations: list[dict[str, Any]],
    primary_prefix: str,
    tool_prefixes: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Coerce unprefixed IDs to the primary tool and drop non-primary tool prefixes."""
    normalized: list[dict[str, Any]] = []
    for violation in violations:
        vid = str(violation.get("id", ""))
        if not vid:
            continue
        if vid.startswith(primary_prefix):
            normalized.append(violation)
            continue
        if vid.startswith(tool_prefixes):
            continue
        normalized.append({**violation, "id": f"{primary_prefix}{vid}"})
    return normalized


def _parse_e1_completion(completion: str) -> tuple[str | None, float | None]:
    """Parse E1 completion JSON into label/confidence."""
    data = _load_json_from_text(completion)
    if not data:
        # Heuristic fallback: try to recover fields from malformed JSON.
        # This commonly happens when the model emits an almost-correct JSON object
        # with a broken string quote in an auxiliary field (e.g. rationale).
        label_match = re.search(r'"label"\s*:\s*"?(malicious|benign|abstain)"?', completion, flags=re.I)
        conf_match = re.search(r'"confidence"\s*:\s*([+-]?\d+(?:\.\d+)?)', completion, flags=re.I)
        label_str = label_match.group(1).lower() if label_match else None
        try:
            confidence = float(conf_match.group(1)) if conf_match else None
        except (TypeError, ValueError):
            confidence = None
        if confidence is not None:
            confidence = max(0.0, min(1.0, confidence))
        return label_str, confidence
    label = data.get("label")
    label_str = label.lower() if isinstance(label, str) else None
    conf_val = data.get("confidence")
    try:
        confidence = float(conf_val)
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None:
        confidence = max(0.0, min(1.0, confidence))
    return label_str, confidence


def _parse_e2_completion(completion: str) -> tuple[list[dict[str, Any]], str, float, bool]:
    """Parse E2 completion JSON into violations/patch/confidence."""
    data = _load_json_from_text(completion)
    if not data:
        return [], "", 0.0, False
    violations = _normalize_violation_list(data.get("violations", []))
    patch = data.get("patch") or ""
    if not isinstance(patch, str):
        patch = str(patch)
    conf_val = data.get("confidence", 0.0)
    try:
        confidence = float(conf_val)
    except (TypeError, ValueError):
        confidence = 0.0
    return violations, patch, confidence, True


def _parse_e2_answer(answer: Any) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Parse E2 answer payload for oracle violations and fixture metadata."""
    answer_obj: dict[str, Any] = {}
    if isinstance(answer, str):
        try:
            answer_obj = json.loads(answer)
        except json.JSONDecodeError:
            answer_obj = {}
    elif isinstance(answer, dict):
        answer_obj = answer
    oracle_raw = answer_obj.get("oracle")
    if oracle_raw is None:
        oracle_raw = answer_obj.get("violations")
    oracle = _normalize_violation_list(oracle_raw or [])
    fixture_path = answer_obj.get("fixture_path")
    fixture_type = answer_obj.get("fixture_type", "k8s")
    if fixture_type not in ("k8s", "tf"):
        fixture_type = "k8s"
    return oracle, fixture_path, fixture_type


@lru_cache
def _load_e2_tooling():
    """Load E2 tooling functions with repo fallback."""
    try:
        from sv_env_config_verification.adapters.kubelinter_adapter import kubelinter_lint
        from sv_env_config_verification.adapters.semgrep_adapter import semgrep_scan
        from sv_env_config_verification.mapping import normalize_findings
        from sv_env_config_verification.patching import try_apply_patch

        return try_apply_patch, kubelinter_lint, semgrep_scan, normalize_findings
    except Exception:
        env_root = REPO_ROOT / "environments" / "sv-env-config-verification"
        if env_root.exists() and str(env_root) not in sys.path:
            sys.path.insert(0, str(env_root))
        from adapters.kubelinter_adapter import kubelinter_lint  # type: ignore
        from adapters.semgrep_adapter import semgrep_scan  # type: ignore
        from mapping import normalize_findings  # type: ignore
        from patching import try_apply_patch  # type: ignore

        return try_apply_patch, kubelinter_lint, semgrep_scan, normalize_findings


def _resolve_fixture_path(fixture_path: str | None) -> Path | None:
    """Resolve fixture paths relative to repo root if needed."""
    if not fixture_path:
        return None
    path = Path(fixture_path)
    if path.is_absolute():
        return path
    candidate = (REPO_ROOT / path).resolve()
    return candidate if candidate.exists() else path


def _compute_post_patch_violations(
    patch: str, fixture_path: str | None, fixture_type: str | None, strict: bool
) -> tuple[bool, list[dict[str, Any]]]:
    """Apply patch and re-run tools to compute post-patch violations."""
    if not patch or not fixture_path:
        return False, []
    path = _resolve_fixture_path(fixture_path)
    if path is None or not path.exists():
        if strict:
            raise ValueError(f"Fixture path not found: {fixture_path}")
        return False, []
    try:
        try_apply_patch, kubelinter_lint, semgrep_scan, normalize_findings = _load_e2_tooling()
    except Exception as exc:
        if strict:
            raise ValueError("Unable to load E2 tooling for patch verification") from exc
        return False, []
    applied, new_text = try_apply_patch(str(path), patch)
    if not applied:
        return False, []
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write(new_text)
        tmp_path = Path(tmp.name)
    try:
        if (fixture_type or "k8s") == "tf":
            findings = semgrep_scan([str(tmp_path)], rules="p/terraform")
        else:
            findings = kubelinter_lint([str(tmp_path)])
        post = normalize_findings(findings)
        post_dicts = [{"id": v.id, "severity": v.severity} for v in post]
    finally:
        tmp_path.unlink(missing_ok=True)
    return True, post_dicts


def _normalize_tool_usage(record: dict[str, Any]) -> tuple[int, float, dict[str, dict[str, float]]]:
    """Normalize tool usage fields from explicit counters or tool interactions."""
    tool_usage = {name: {"calls": 0, "time_ms": 0.0} for name in TOOL_NAMES}
    explicit = any(
        record.get(f"{name}_calls") is not None or record.get(f"{name}_time_ms") is not None
        for name in TOOL_NAMES
    )
    if explicit:
        for name in TOOL_NAMES:
            tool_usage[name]["calls"] = int(record.get(f"{name}_calls") or 0)
            tool_usage[name]["time_ms"] = float(record.get(f"{name}_time_ms") or 0.0)
    else:
        for interaction in record.get("tool_interactions", []) or []:
            if not isinstance(interaction, dict):
                continue
            name = TOOL_NAME_MAP.get(interaction.get("tool"))
            if not name:
                continue
            tool_usage[name]["calls"] += 1
            duration = interaction.get("duration_ms")
            if duration is None:
                duration = interaction.get("time_ms")
            tool_usage[name]["time_ms"] += float(duration) if duration else 0.0

    if record.get("tool_calls") is not None:
        tool_calls = int(record.get("tool_calls") or 0)
    else:
        tool_calls = sum(t["calls"] for t in tool_usage.values())

    if record.get("tool_time_ms") is not None:
        tool_time_ms = float(record.get("tool_time_ms") or 0.0)
    else:
        tool_time_ms = sum(t["time_ms"] for t in tool_usage.values())

    return tool_calls, tool_time_ms, tool_usage


def _normalize_e1_results(results: list[dict[str, Any]], strict: bool) -> list[dict[str, Any]]:
    """Normalize E1 records to predicted_label/answer/confidence."""
    normalized: list[dict[str, Any]] = []
    for idx, record in enumerate(results):
        pred = record.get("predicted_label")
        conf = record.get("confidence")
        actual = record.get("answer")
        if (pred is None or conf is None) and record.get("completion") is not None:
            parsed_label, parsed_conf = _parse_e1_completion(str(record.get("completion") or ""))
            if pred is None:
                pred = parsed_label
            if conf is None:
                conf = parsed_conf

        if isinstance(actual, dict):
            actual_label = str(actual.get("label") or actual.get("answer") or "")
        else:
            actual_label = str(actual or "")

        pred_label = str(pred or "").lower() if pred is not None else ""
        actual_label = actual_label.lower()

        if conf is None:
            if strict:
                raise ValueError(f"Missing confidence for E1 result at index {idx}")
            conf_val = 0.0
        else:
            conf_val = float(conf)

        if strict and (not pred_label or not actual_label):
            raise ValueError(f"Missing predicted_label or answer for E1 result at index {idx}")

        normalized.append({"predicted_label": pred_label, "answer": actual_label, "confidence": conf_val})
    return normalized


def _normalize_e2_results(results: list[dict[str, Any]], strict: bool) -> list[dict[str, Any]]:
    """Normalize E2 records to prediction/oracle/patch/tool usage fields."""
    normalized: list[dict[str, Any]] = []
    for idx, record in enumerate(results):
        predicted_raw = record.get("predicted_violations")
        patch = record.get("patch")
        valid_json = record.get("valid_json")
        parsed_ok = False
        if (predicted_raw is None or patch is None or valid_json is None) and record.get(
            "completion"
        ) is not None:
            parsed_violations, parsed_patch, _parsed_conf, parsed_ok = _parse_e2_completion(
                str(record.get("completion") or "")
            )
            if predicted_raw is None:
                predicted_raw = parsed_violations
            if patch is None:
                patch = parsed_patch
            if valid_json is None:
                valid_json = parsed_ok

        predicted = _normalize_violation_list(predicted_raw)
        if patch is None:
            patch = ""
        if not isinstance(patch, str):
            patch = str(patch)
        if valid_json is None:
            valid_json = parsed_ok

        oracle_raw = record.get("oracle_violations")
        fixture_path = record.get("fixture_path")
        fixture_type = record.get("fixture_type")
        if oracle_raw is None:
            oracle, ans_fixture_path, ans_fixture_type = _parse_e2_answer(record.get("answer"))
            if fixture_path is None:
                fixture_path = ans_fixture_path
            if fixture_type is None:
                fixture_type = ans_fixture_type
        else:
            oracle = _normalize_violation_list(oracle_raw)
            if fixture_path is None or fixture_type is None:
                _, ans_fixture_path, ans_fixture_type = _parse_e2_answer(record.get("answer"))
                fixture_path = fixture_path or ans_fixture_path
                fixture_type = fixture_type or ans_fixture_type

        if strict and oracle_raw is None and record.get("answer") is None:
            raise ValueError(f"Missing oracle violations for E2 result at index {idx}")
        if strict and predicted_raw is None and not parsed_ok:
            raise ValueError(f"Missing predicted violations for E2 result at index {idx}")
        if strict and patch and not fixture_path:
            raise ValueError(f"Missing fixture_path for E2 patch at index {idx}")

        # Align scoring to the environment's primary oracle per fixture type:
        # - k8s: kube-linter
        # - tf: semgrep
        # This avoids penalizing models for emitting extra tool findings (e.g., OPA) that are
        # present in tool outputs but are not part of the scored oracle.
        tool_prefixes = ("kube-linter/", "semgrep/", "opa/")
        tool_style = any(v.get("id", "").startswith(tool_prefixes) for v in oracle) or any(
            v.get("id", "").startswith(tool_prefixes) for v in predicted
        )
        if tool_style:
            primary_prefix = "kube-linter/" if (fixture_type or "k8s") == "k8s" else "semgrep/"
            oracle = _normalize_primary_tool_ids(oracle, primary_prefix, tool_prefixes)
            predicted = _normalize_primary_tool_ids(predicted, primary_prefix, tool_prefixes)

        patch_applied = record.get("patch_applied")
        post_patch_raw = record.get("post_patch_violations")
        if patch_applied is None or post_patch_raw is None:
            if patch:
                applied, post = _compute_post_patch_violations(patch, fixture_path, fixture_type, strict)
                if patch_applied is None:
                    patch_applied = applied
                if post_patch_raw is None:
                    post_patch_raw = post
            else:
                patch_applied = bool(patch_applied) if patch_applied is not None else False
                post_patch_raw = post_patch_raw or []

        post_patch = _normalize_violation_list(post_patch_raw)
        if tool_style and post_patch:
            primary_prefix = "kube-linter/" if (fixture_type or "k8s") == "k8s" else "semgrep/"
            post_patch = _normalize_primary_tool_ids(post_patch, primary_prefix, tool_prefixes)
        tool_calls, tool_time_ms, tool_usage = _normalize_tool_usage(record)
        turns = record.get("turns") or record.get("turns_used") or 1

        normalized.append(
            {
                "predicted_violations": predicted,
                "oracle_violations": oracle,
                "patch": patch,
                "patch_applied": bool(patch_applied),
                "post_patch_violations": post_patch,
                "tool_calls": tool_calls,
                "tool_time_ms": tool_time_ms,
                "tool_usage": tool_usage,
                "valid_json": bool(valid_json),
                "turns": int(turns),
            }
        )
    return normalized


# ============================================================================
# E1 Metrics: Network Logs Anomaly Detection
# ============================================================================


def compute_e1_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute E1 metrics from rollout results."""
    predictions: list[str] = []
    actuals: list[str] = []
    confidences: list[float] = []

    for record in results:
        pred = str(record.get("predicted_label", "")).lower()
        actual = str(record.get("answer", "")).lower()
        conf_val = record.get("confidence", 0.5)
        try:
            conf = float(conf_val)
        except (TypeError, ValueError):
            conf = 0.5

        if pred and actual:
            predictions.append(pred)
            actuals.append(actual)
            confidences.append(conf)

    non_abstain_mask = [pred != "abstain" for pred in predictions]
    pred_na = [pred for pred, keep in zip(predictions, non_abstain_mask) if keep]
    actual_na = [act for act, keep in zip(actuals, non_abstain_mask) if keep]
    conf_na = [conf for conf, keep in zip(confidences, non_abstain_mask) if keep]

    tp = sum(1 for pred, act in zip(pred_na, actual_na) if pred == "malicious" and act == "malicious")
    tn = sum(1 for pred, act in zip(pred_na, actual_na) if pred == "benign" and act == "benign")
    fp = sum(1 for pred, act in zip(pred_na, actual_na) if pred == "malicious" and act == "benign")
    fn = sum(1 for pred, act in zip(pred_na, actual_na) if pred == "benign" and act == "malicious")

    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = 1.0 - tpr
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    accuracy = (tp + tn) / len(pred_na) if pred_na else 0.0
    f1 = 2 * precision * tpr / (precision + tpr) if (precision + tpr) > 0 else 0.0

    correct_na = [pred == act for pred, act in zip(pred_na, actual_na)]
    ece = _compute_ece(correct_na, conf_na)
    brier = _compute_brier(correct_na, conf_na)

    fn_cost_weight = 10.0
    fp_cost_weight = 1.0
    total_cost = fn_cost_weight * fn + fp_cost_weight * fp
    max_cost = len(pred_na) * max(fn_cost_weight, fp_cost_weight)
    cost_weighted_accuracy = 1.0 - (total_cost / max_cost) if max_cost > 0 else 1.0

    n_abstain = sum(1 for keep in non_abstain_mask if not keep)
    abstain_rate = n_abstain / len(predictions) if predictions else 0.0
    accuracy_non_abstained = accuracy
    aurc = _compute_aurc(pred_na, actual_na, conf_na)

    return {
        "detection": {
            "tpr": float(tpr),
            "fpr": float(fpr),
            "fnr": float(fnr),
            "precision": float(precision),
            "f1": float(f1),
            "accuracy": float(accuracy),
        },
        "calibration": {
            "ece": float(ece),
            "brier": float(brier),
        },
        "cost": {
            "fn_cost_weight": fn_cost_weight,
            "fp_cost_weight": fp_cost_weight,
            "total_cost": float(total_cost),
            "cost_weighted_accuracy": float(cost_weighted_accuracy),
        },
        "abstention": {
            "abstain_rate": float(abstain_rate),
            "accuracy_non_abstained": float(accuracy_non_abstained),
            "aurc": float(aurc),
        },
        "confusion_matrix": {
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "abstain": int(n_abstain),
        },
    }


def _compute_ece(correct: list[bool], confidences: list[float], num_bins: int = 10) -> float:
    """Compute Expected Calibration Error."""
    if not correct:
        return 0.0

    bins = [i / num_bins for i in range(num_bins + 1)]
    ece = 0.0
    total = len(correct)

    for i in range(num_bins):
        if i == num_bins - 1:
            in_bin = [idx for idx, conf in enumerate(confidences) if conf >= bins[i] and conf <= bins[i + 1]]
        else:
            in_bin = [idx for idx, conf in enumerate(confidences) if conf >= bins[i] and conf < bins[i + 1]]
        if in_bin:
            bin_acc = sum(1 for idx in in_bin if correct[idx]) / len(in_bin)
            bin_conf = sum(confidences[idx] for idx in in_bin) / len(in_bin)
            ece += len(in_bin) / total * abs(bin_acc - bin_conf)

    return ece


def _compute_brier(correct: list[bool], confidences: list[float]) -> float:
    """Compute Brier score."""
    if not correct:
        return 0.0
    correct_float = [1.0 if value else 0.0 for value in correct]
    return sum((conf - label) ** 2 for conf, label in zip(confidences, correct_float)) / len(correct)


def _compute_aurc(predictions: list[str], actuals: list[str], confidences: list[float]) -> float:
    """Compute Area Under Risk-Coverage curve."""
    if not predictions:
        return 0.0

    thresholds = [i / 100 for i in range(101)]
    coverages: list[float] = []
    risks: list[float] = []

    for tau in thresholds:
        indices = [idx for idx, conf in enumerate(confidences) if conf >= tau]
        coverage = len(indices) / len(predictions)
        if coverage > 0:
            risk = sum(1 for idx in indices if predictions[idx] != actuals[idx]) / len(indices)
        else:
            risk = 0.0
        coverages.append(coverage)
        risks.append(risk)

    aurc = 0.0
    for i in range(1, len(coverages)):
        # As tau increases, coverage is (monotonically) decreasing; integrate over
        # increasing coverage to keep AURC non-negative.
        delta_coverage = coverages[i - 1] - coverages[i]
        aurc += delta_coverage * (risks[i] + risks[i - 1]) / 2.0
    return float(max(0.0, aurc))


# ============================================================================
# E2 Metrics: Config Verification
# ============================================================================


def compute_e2_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute E2 metrics from rollout results."""
    precisions_w: list[float] = []
    recalls_w: list[float] = []
    f1s_w: list[float] = []
    precisions_u: list[float] = []
    recalls_u: list[float] = []
    f1s_u: list[float] = []
    pos_f1s_w: list[float] = []
    pos_f1s_u: list[float] = []
    patch_provided = 0
    patch_success = 0
    total_fixed_weight = 0.0
    total_oracle_weight = 0.0
    violations_fixed: list[int] = []
    new_violations: list[int] = []
    tool_calls: list[int] = []
    tool_times: list[float] = []
    tool_usage = {name: {"calls": 0, "time_ms": 0.0} for name in TOOL_NAMES}
    format_valid = 0
    turns: list[int] = []
    clean_episodes = 0
    clean_pass = 0
    clean_false_positive = 0

    for record in results:
        pred_violations = record.get("predicted_violations", [])
        oracle_violations = record.get("oracle_violations", [])

        p_w, r_w, f1_w = _score_detection_weighted(pred_violations, oracle_violations)
        p_u, r_u, f1_u = _score_detection_unweighted(pred_violations, oracle_violations)

        precisions_w.append(p_w)
        recalls_w.append(r_w)
        f1s_w.append(f1_w)
        precisions_u.append(p_u)
        recalls_u.append(r_u)
        f1s_u.append(f1_u)

        has_oracle = len(oracle_violations) > 0
        has_pred = len(pred_violations) > 0
        if has_oracle:
            pos_f1s_w.append(f1_w)
            pos_f1s_u.append(f1_u)
        else:
            clean_episodes += 1
            if not has_pred:
                clean_pass += 1
            else:
                clean_false_positive += 1

        patch = record.get("patch", "")
        patch_applied = record.get("patch_applied", False)
        if patch:
            patch_provided += 1
            if patch_applied:
                patch_success += 1
                post_violations = record.get("post_patch_violations", [])
                fixed = _count_violations_fixed(oracle_violations, post_violations)
                violations_fixed.append(fixed)
                new_violations.append(_count_new_violations(oracle_violations, post_violations))
                fixed_weight = _count_violations_fixed_weighted(oracle_violations, post_violations)
                total_weight = _total_violation_weight(oracle_violations)
                total_fixed_weight += fixed_weight
                total_oracle_weight += total_weight

        tool_calls.append(int(record.get("tool_calls", 0)))
        tool_times.append(float(record.get("tool_time_ms", 0.0)))

        usage = record.get("tool_usage", {})
        for name in TOOL_NAMES:
            tool_usage[name]["calls"] += int(usage.get(name, {}).get("calls", 0))
            tool_usage[name]["time_ms"] += float(usage.get(name, {}).get("time_ms", 0.0))

        if record.get("valid_json", True):
            format_valid += 1
        turns.append(int(record.get("turns", 1)))

    n = len(results)
    n_findings = sum(len(r.get("predicted_violations", [])) for r in results)
    clean_pass_rate = clean_pass / clean_episodes if clean_episodes > 0 else 0.0
    clean_fp_rate = clean_false_positive / clean_episodes if clean_episodes > 0 else 0.0

    return {
        "finding_quality": {
            "precision_weighted": _mean(precisions_w),
            "recall_weighted": _mean(recalls_w),
            "f1_weighted": _mean(f1s_w),
            "precision_unweighted": _mean(precisions_u),
            "recall_unweighted": _mean(recalls_u),
            "f1_unweighted": _mean(f1s_u),
            "f1_weighted_positive_only": _mean(pos_f1s_w),
            "f1_unweighted_positive_only": _mean(pos_f1s_u),
        },
        "patch": {
            "patch_provided_rate": patch_provided / n if n > 0 else 0.0,
            "patch_success_rate": patch_success / patch_provided if patch_provided > 0 else 0.0,
            "patch_fix_rate": total_fixed_weight / total_oracle_weight if total_oracle_weight > 0 else 0.0,
            "mean_violations_fixed": _mean(violations_fixed),
            "new_violations_introduced": _mean(new_violations),
        },
        "tool_economy": {
            "mean_tool_calls": _mean([float(c) for c in tool_calls]),
            "mean_tool_time_ms": _mean(tool_times),
            "calls_per_finding": sum(tool_calls) / n_findings if n_findings > 0 else 0.0,
            "tool_distribution": tool_usage,
        },
        "episode": {
            "format_valid_rate": format_valid / n if n > 0 else 0.0,
            "mean_turns": _mean([float(t) for t in turns]),
            "clean_pass_rate": clean_pass_rate,
            "false_positive_rate_on_clean": clean_fp_rate,
        },
    }


def _score_detection_weighted(
    pred: list[dict[str, Any]], oracle: list[dict[str, Any]]
) -> tuple[float, float, float]:
    """Weighted precision/recall/F1."""
    o_ids = {
        v.get("id", v.get("rule_id", "")): SEV_WEIGHT.get(_normalize_severity(v.get("severity")), 0.6)
        for v in oracle
        if v.get("id") or v.get("rule_id")
    }
    p_ids = {
        v.get("id", v.get("rule_id", "")): SEV_WEIGHT.get(_normalize_severity(v.get("severity")), 0.6)
        for v in pred
        if v.get("id") or v.get("rule_id")
    }

    tp = sum(o_ids.get(vid, 0) for vid in p_ids if vid in o_ids)
    fp = sum(weight for vid, weight in p_ids.items() if vid not in o_ids)
    fn = sum(weight for vid, weight in o_ids.items() if vid not in p_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def _score_detection_unweighted(
    pred: list[dict[str, Any]], oracle: list[dict[str, Any]]
) -> tuple[float, float, float]:
    """Unweighted precision/recall/F1."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle if v.get("id") or v.get("rule_id")}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in pred if v.get("id") or v.get("rule_id")}

    tp = len(p_ids & o_ids)
    fp = len(p_ids - o_ids)
    fn = len(o_ids - p_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def _count_violations_fixed(oracle: list[dict[str, Any]], post: list[dict[str, Any]]) -> int:
    """Count violations fixed by patch."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle if v.get("id") or v.get("rule_id")}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in post if v.get("id") or v.get("rule_id")}
    return len(o_ids - p_ids)


def _count_violations_fixed_weighted(oracle: list[dict[str, Any]], post: list[dict[str, Any]]) -> float:
    """Weighted count of oracle violations fixed by patch."""
    post_ids = {v.get("id", v.get("rule_id", "")) for v in post if v.get("id") or v.get("rule_id")}
    return sum(
        SEV_WEIGHT.get(_normalize_severity(v.get("severity")), 0.6)
        for v in oracle
        if (v.get("id") or v.get("rule_id")) and (v.get("id", v.get("rule_id", "")) not in post_ids)
    )


def _total_violation_weight(oracle: list[dict[str, Any]]) -> float:
    """Sum severity weights for oracle violations."""
    return sum(
        SEV_WEIGHT.get(_normalize_severity(v.get("severity")), 0.6)
        for v in oracle
        if v.get("id") or v.get("rule_id")
    )


def _count_new_violations(oracle: list[dict[str, Any]], post: list[dict[str, Any]]) -> int:
    """Count new violations introduced by patch."""
    o_ids = {v.get("id", v.get("rule_id", "")) for v in oracle if v.get("id") or v.get("rule_id")}
    p_ids = {v.get("id", v.get("rule_id", "")) for v in post if v.get("id") or v.get("rule_id")}
    return len(p_ids - o_ids)


def _compute_severity_breakdown(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Compute total/found/fixed counts per severity."""
    breakdown = {sev: {"total": 0, "found": 0, "fixed": 0} for sev in SEV_WEIGHT}
    for record in results:
        oracle = record.get("oracle_violations", [])
        predicted = record.get("predicted_violations", [])
        post = record.get("post_patch_violations", [])
        oracle_by_id = {v["id"]: v["severity"] for v in oracle if "id" in v}
        pred_ids = {v["id"] for v in predicted if "id" in v}
        post_ids = {v["id"] for v in post if "id" in v}

        for violation in oracle:
            sev = violation.get("severity", "med")
            sev = _normalize_severity(sev)
            breakdown[sev]["total"] += 1

        for vid in pred_ids:
            if vid in oracle_by_id:
                sev = _normalize_severity(oracle_by_id[vid])
                breakdown[sev]["found"] += 1

        if record.get("patch_applied"):
            for violation in oracle:
                vid = violation.get("id")
                if not vid or vid in post_ids:
                    continue
                sev = _normalize_severity(violation.get("severity", "med"))
                breakdown[sev]["fixed"] += 1

    return breakdown


# ============================================================================
# Report Generation
# ============================================================================


def load_results(input_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load results.jsonl and metadata.json from input path."""
    results_file = input_path / "results.jsonl"
    metadata_file = input_path / "metadata.json"

    results: list[dict[str, Any]] = []
    if results_file.exists():
        with open(results_file) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))

    metadata: dict[str, Any] = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    return results, metadata


def generate_summary(
    env: str,
    results: list[dict[str, Any]],
    metadata: dict[str, Any],
    run_id: str | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Generate summary.json content."""
    if env in ("e1", "network-logs", "sv-env-network-logs"):
        env_name = "sv-env-network-logs"
        normalized = _normalize_e1_results(results, strict)
        metrics = compute_e1_metrics(normalized)
        severity_breakdown = None
    elif env in ("e2", "config-verification", "sv-env-config-verification"):
        env_name = "sv-env-config-verification"
        normalized = _normalize_e2_results(results, strict)
        metrics = compute_e2_metrics(normalized)
        severity_breakdown = _compute_severity_breakdown(normalized)
    else:
        raise ValueError(f"Unknown environment: {env}")

    metadata_fields = {
        "git_sha": metadata.get("git_sha") or metadata.get("git_commit"),
        "env_version": metadata.get("env_version"),
        "python_version": metadata.get("python_version"),
        "verifiers_version": metadata.get("verifiers_version"),
        "seed": metadata.get("seed"),
    }
    metadata_clean = {key: value for key, value in metadata_fields.items() if value is not None}

    summary = {
        "environment": env_name,
        "version": "0.1.0",
        "run_id": run_id or metadata.get("run_id", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": metadata.get("model", "unknown"),
        "dataset": metadata.get("dataset", "unknown"),
        "n_examples": len(results),
        "metrics": metrics,
        "metadata": metadata_clean,
    }

    if severity_breakdown is not None:
        summary["severity_breakdown"] = severity_breakdown
    _validate_summary(summary)

    return summary


def generate_report_md(summary: dict[str, Any]) -> str:
    """Generate human-readable report.md content."""
    lines = [
        f"# SV-Bench Report: {summary['environment']}",
        "",
        "## Run Information",
        "",
        f"- **Model:** {summary['model']}",
        f"- **Dataset:** {summary['dataset']}",
        f"- **Examples:** {summary['n_examples']}",
        f"- **Run ID:** {summary['run_id']}",
        f"- **Timestamp:** {summary['timestamp']}",
        "",
    ]

    metrics = summary["metrics"]

    if summary["environment"] == "sv-env-network-logs":
        lines.extend(_format_e1_report(metrics))
    else:
        lines.extend(_format_e2_report(metrics, summary.get("severity_breakdown")))

    return "\n".join(lines)


def _format_e1_report(metrics: dict[str, Any]) -> list[str]:
    """Format E1 metrics as markdown."""
    d = metrics["detection"]
    c = metrics["calibration"]
    cost = metrics["cost"]
    a = metrics["abstention"]
    cm = metrics.get("confusion_matrix", {})

    return [
        "## Detection Performance",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| TPR (Recall) | {d['tpr']:.3f} |",
        f"| FPR | {d['fpr']:.3f} |",
        f"| FNR | {d['fnr']:.3f} |",
        f"| Precision | {d['precision']:.3f} |",
        f"| F1 Score | {d['f1']:.3f} |",
        f"| Accuracy | {d['accuracy']:.3f} |",
        "",
        "## Calibration",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| ECE | {c['ece']:.4f} |",
        f"| Brier Score | {c['brier']:.4f} |",
        "",
        "## Cost Analysis",
        "",
        f"- FN Cost Weight: {cost['fn_cost_weight']}",
        f"- FP Cost Weight: {cost['fp_cost_weight']}",
        f"- Total Cost: {cost['total_cost']:.1f}",
        f"- Cost-Weighted Accuracy: {cost['cost_weighted_accuracy']:.3f}",
        "",
        "## Abstention",
        "",
        f"- Abstain Rate: {a['abstain_rate']:.3f}",
        f"- Accuracy (non-abstained): {a['accuracy_non_abstained']:.3f}",
        f"- AURC: {a['aurc']:.4f}",
        "",
        "## Confusion Matrix",
        "",
        f"- TP: {cm.get('tp', 'N/A')}",
        f"- TN: {cm.get('tn', 'N/A')}",
        f"- FP: {cm.get('fp', 'N/A')}",
        f"- FN: {cm.get('fn', 'N/A')}",
        f"- Abstain: {cm.get('abstain', 'N/A')}",
        "",
    ]


def _format_e2_report(metrics: dict[str, Any], severity_breakdown: dict[str, Any] | None) -> list[str]:
    """Format E2 metrics as markdown."""
    fq = metrics["finding_quality"]
    p = metrics["patch"]
    te = metrics["tool_economy"]
    ep = metrics.get("episode", {})

    lines = [
        "## Finding Quality",
        "",
        "| Metric | Weighted | Unweighted |",
        "|--------|----------|------------|",
        f"| Precision | {fq['precision_weighted']:.3f} | {fq['precision_unweighted']:.3f} |",
        f"| Recall | {fq['recall_weighted']:.3f} | {fq['recall_unweighted']:.3f} |",
        f"| F1 | {fq['f1_weighted']:.3f} | {fq['f1_unweighted']:.3f} |",
        (
            f"| F1 (positive-only) | {fq.get('f1_weighted_positive_only', 0):.3f} | "
            f"{fq.get('f1_unweighted_positive_only', 0):.3f} |"
        ),
        "",
        "## Patch Analysis",
        "",
        f"- Patch Provided Rate: {p['patch_provided_rate']:.3f}",
        f"- Patch Success Rate: {p['patch_success_rate']:.3f}",
        f"- Patch Fix Rate: {p['patch_fix_rate']:.3f}",
        f"- Mean Violations Fixed: {p['mean_violations_fixed']:.2f}",
        f"- New Violations Introduced: {p['new_violations_introduced']:.2f}",
        "",
        "## Tool Economy",
        "",
        f"- Mean Tool Calls: {te['mean_tool_calls']:.2f}",
        f"- Mean Tool Time (ms): {te['mean_tool_time_ms']:.1f}",
        f"- Calls Per Finding: {te['calls_per_finding']:.2f}",
        "",
        "### Tool Distribution",
        "",
        "| Tool | Calls | Time (ms) |",
        "|------|-------|-----------|",
    ]
    lines.extend(
        [
            f"| {tool} | {stats['calls']} | {stats['time_ms']:.0f} |"
            for tool, stats in te.get("tool_distribution", {}).items()
        ]
    )
    lines.extend(
        [
            "",
            "## Episode Metrics",
            "",
            f"- Format Valid Rate: {ep.get('format_valid_rate', 0):.3f}",
            f"- Mean Turns: {ep.get('mean_turns', 0):.2f}",
            f"- Clean Pass Rate: {ep.get('clean_pass_rate', 0):.3f}",
            f"- False Positive Rate (clean): {ep.get('false_positive_rate_on_clean', 0):.3f}",
            "",
        ]
    )

    if severity_breakdown:
        lines.extend(
            [
                "## Severity Breakdown",
                "",
                "| Severity | Total | Found | Fixed |",
                "|----------|-------|-------|-------|",
            ]
        )
        for sev in ["high", "med", "low"]:
            stats = severity_breakdown.get(sev, {})
            lines.append(
                f"| {sev} | {stats.get('total', 0)} | {stats.get('found', 0)} | {stats.get('fixed', 0)} |"
            )
        lines.append("")

    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SV-Bench evaluation reports")
    parser.add_argument(
        "--env",
        required=True,
        choices=["e1", "e2", "network-logs", "config-verification"],
        help="Environment type",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to evaluation output directory (contains results.jsonl and metadata.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if required fields are missing",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    results, metadata = load_results(input_path)

    if not results:
        print(f"Error: No results found in {input_path}/results.jsonl", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(results)} results from {input_path}")

    run_id = input_path.name if input_path.name != "." else None
    try:
        summary = generate_summary(args.env, results, metadata, run_id, strict=args.strict)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    report_md = generate_report_md(summary)

    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {summary_file}")

    report_file = output_path / "report.md"
    with open(report_file, "w") as f:
        f.write(report_md)
    print(f"Wrote {report_file}")


if __name__ == "__main__":
    main()
