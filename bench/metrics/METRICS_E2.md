# E2 Config Verification Metrics Specification

**Environment:** `sv-env-config-verification`  
**Task:** Security auditing of Kubernetes/Terraform configs with tool-grounded verification  
**Version:** v0.1.0

---

## Overview

E2 metrics evaluate configuration auditing performance with emphasis on:
- Finding quality (precision/recall on security violations)
- Patch effectiveness (do patches fix the issues?)
- Severity-weighted scoring (high severity issues matter more)
- Tool economy (efficient use of verification tools)

---

## Core Metrics

### 1. Finding Quality Metrics

#### Severity Weights

Findings are weighted by severity:
```python
SEV_WEIGHT = {"low": 0.3, "med": 0.6, "high": 1.0}
```

#### Weighted Precision
$$\text{Precision}_w = \frac{\sum_{v \in TP} w(v)}{\sum_{v \in TP} w(v) + \sum_{v \in FP} w(v)}$$

Where:
- $w(v)$ = severity weight of violation $v$
- TP = predicted violations that match oracle violations (by violation ID)
- FP = predicted violations not in oracle

#### Weighted Recall
$$\text{Recall}_w = \frac{\sum_{v \in TP} w(v)}{\sum_{v \in TP} w(v) + \sum_{v \in FN} w(v)}$$

Where:
- FN = oracle violations not predicted

#### Weighted F1
$$\text{F1}_w = 2 \cdot \frac{\text{Precision}_w \cdot \text{Recall}_w}{\text{Precision}_w + \text{Recall}_w}$$

**Implementation (from `reward.py`):**
```python
def score_detection(pred: List[Violation], oracle: List[Violation]):
    o_ids = {v.id: SEV_WEIGHT[v.severity] for v in oracle}
    p_ids = {v.id: SEV_WEIGHT[v.severity] for v in pred}
    tp = sum(o_ids[v.id] for v in pred if v.id in o_ids)
    fp = sum(SEV_WEIGHT[v.severity] for v in pred if v.id not in o_ids)
    fn = sum(w for vid, w in o_ids.items() if vid not in p_ids)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
```

---

### 2. Patch Metrics

#### Patch Success Rate

Fraction of episodes where the model's patch was syntactically valid and applicable.

$$\text{PatchSuccess} = \frac{|\{e : \text{patch}_e \text{ applied successfully}\}|}{|\{e : \text{patch}_e \text{ provided}\}|}$$

#### Weighted Violations Fixed

Measures how many oracle violations are eliminated after applying the patch.

$$\text{FixedWeight} = \sum_{v \in \text{Oracle} \setminus \text{PostPatch}} w(v)$$

**Implementation (from `reward.py`):**
```python
def score_patch_delta(oracle: List[Violation], post: List[Violation]) -> float:
    o = {v.id: SEV_WEIGHT[v.severity] for v in oracle}
    p = {v.id for v in post}
    return sum(w for vid, w in o.items() if vid not in p)
```

#### Patch Fix Rate

Fraction of weighted oracle violations fixed by the patch.

$$\text{PatchFixRate} = \frac{\text{FixedWeight}}{\sum_{v \in \text{Oracle}} w(v)}$$

#### New Violations Introduced

Count of violations in post-patch analysis that weren't in the original oracle.

$$\text{NewViolations} = |\text{PostPatch} \setminus \text{Oracle}|$$

---

### 3. Tool Economy Metrics

Measures efficient use of verification tools (OPA, KubeLinter, Semgrep).

#### Tool Call Count

Total number of tool invocations per episode.

$$\text{ToolCalls} = \sum_{t \in \text{tools}} \text{count}(t)$$

#### Tool Time

Total wall-clock time spent in tool execution.

$$\text{ToolTime} = \sum_{t \in \text{tools}} \text{duration}(t)$$

#### Calls Per Finding

Efficiency metric: fewer calls per finding is better.

$$\text{CallsPerFinding} = \frac{\text{ToolCalls}}{|\text{Findings}|}$$

#### Tool Distribution

Breakdown of tool usage:
```json
{
  "opa": {"calls": 5, "time_ms": 120},
  "kube-linter": {"calls": 3, "time_ms": 80},
  "semgrep": {"calls": 2, "time_ms": 150}
}
```

---

### 4. Episode-Level Metrics

#### Format Validity Rate

Fraction of model responses with valid JSON output matching expected schema.

$$\text{FormatValid} = \frac{|\{e : \text{valid JSON}\}|}{N}$$

#### Mean Turns Per Episode

Average number of conversation turns (tool calls + responses).

$$\text{MeanTurns} = \frac{\sum_e \text{turns}_e}{N}$$

---

## Summary JSON Schema

The report generator produces a `summary.json` with these fields for E2:

```json
{
  "environment": "sv-env-config-verification",
  "version": "0.1.0",
  "run_id": "<uuid>",
  "timestamp": "<ISO8601>",
  "model": "<model_name>",
  "dataset": "<dataset_name>",
  "n_examples": 50,
  "metrics": {
    "finding_quality": {
      "precision_weighted": 0.82,
      "recall_weighted": 0.75,
      "f1_weighted": 0.78,
      "precision_unweighted": 0.80,
      "recall_unweighted": 0.72,
      "f1_unweighted": 0.76
    },
    "patch": {
      "patch_provided_rate": 0.90,
      "patch_success_rate": 0.85,
      "patch_fix_rate": 0.70,
      "mean_violations_fixed": 2.3,
      "new_violations_introduced": 0.1
    },
    "tool_economy": {
      "mean_tool_calls": 4.2,
      "mean_tool_time_ms": 350,
      "calls_per_finding": 1.8,
      "tool_distribution": {
        "opa": {"calls": 100, "time_ms": 2400},
        "kube-linter": {"calls": 80, "time_ms": 1600},
        "semgrep": {"calls": 30, "time_ms": 1500}
      }
    },
    "episode": {
      "format_valid_rate": 0.95,
      "mean_turns": 3.2
    }
  },
  "severity_breakdown": {
    "high": {"total": 50, "found": 45, "fixed": 35},
    "med": {"total": 80, "found": 60, "fixed": 40},
    "low": {"total": 120, "found": 70, "fixed": 30}
  }
}
```

---

## Report Markdown Format

The `report.md` should include:

1. **Header** with run metadata
2. **Summary table** of key metrics
3. **Finding quality** section with P/R/F1 breakdown by severity
4. **Patch analysis** section with success rates and fix rates
5. **Tool economy** section with usage statistics
6. **Per-severity breakdown** table

---

## Reward Function Reference

From `reward.py`:

| Component | Formula | Default Weight |
|-----------|---------|----------------|
| Detection F1 | Weighted F1 score | 1.0 (base) |
| Patch delta | Weighted violations fixed | 1.0 |
| Format bonus | +0.05 if valid JSON | 0.05 |
| Invalid penalty | -0.25 if invalid JSON | -0.25 |

**Final reward formula:**
```python
reward = f1 + patch_removed_weight * patch_delta + format_bonus
reward = max(-1.0, min(2.0, reward))  # Clamp to [-1, 2]
```

---

## Tool Verification Details

### OPA (Open Policy Agent)
- Evaluates Rego policies against config data
- Outputs: rule violations with severity
- Policies location: `environments/sv-env-config-verification/policies/`

### KubeLinter
- Static analysis for Kubernetes manifests
- Detects security misconfigurations
- Outputs: rule ID, severity, message, location

### Semgrep
- Pattern-based static analysis
- Supports custom security rules
- Outputs: rule ID, severity, message, file location
