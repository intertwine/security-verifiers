# E1 Network Logs Metrics Specification

**Environment:** `sv-env-network-logs`  
**Task:** Binary/ternary classification of network log entries as Malicious, Benign, or Abstain  
**Version:** v0.1.0

---

## Overview

E1 metrics evaluate anomaly detection performance with emphasis on:
- Detection accuracy with asymmetric costs (missed attacks are costly)
- Calibration quality (confidence should match accuracy)
- Abstention behavior (know when to say "I don't know")

---

## Core Metrics

### 1. Detection Metrics

#### True Positive Rate (TPR) / Recall
$$\text{TPR} = \frac{TP}{TP + FN}$$

Where:
- TP = Correctly predicted "Malicious" when ground truth is "Malicious"
- FN = Predicted "Benign" when ground truth is "Malicious"

**Note:** Abstain predictions are excluded from this calculation.

#### False Positive Rate (FPR)
$$\text{FPR} = \frac{FP}{FP + TN}$$

Where:
- FP = Predicted "Malicious" when ground truth is "Benign"
- TN = Correctly predicted "Benign" when ground truth is "Benign"

#### False Negative Rate (FNR)
$$\text{FNR} = 1 - \text{TPR} = \frac{FN}{TP + FN}$$

#### Precision
$$\text{Precision} = \frac{TP}{TP + FP}$$

#### F1 Score
$$\text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

---

### 2. Calibration Metrics

#### Expected Calibration Error (ECE)

Measures how well confidence scores predict accuracy. Bins predictions by confidence and compares to actual accuracy.

$$\text{ECE} = \sum_{b=1}^{B} \frac{|B_b|}{N} \cdot |\text{acc}(B_b) - \text{conf}(B_b)|$$

Where:
- $B$ = number of bins (default: 10)
- $B_b$ = set of predictions in bin $b$
- $\text{acc}(B_b)$ = accuracy of predictions in bin $b$
- $\text{conf}(B_b)$ = mean confidence of predictions in bin $b$
- $N$ = total number of predictions

**Implementation:**
```python
def compute_ece(predictions, actuals, confidences, num_bins=10):
    bins = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    for i in range(num_bins):
        mask = (confidences >= bins[i]) & (confidences < bins[i+1])
        if mask.sum() > 0:
            bin_acc = (predictions[mask] == actuals[mask]).mean()
            bin_conf = confidences[mask].mean()
            ece += mask.sum() / len(predictions) * abs(bin_acc - bin_conf)
    return ece
```

#### Brier Score

Mean squared error between confidence and correctness indicator.

$$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (c_i - y_i)^2$$

Where:
- $c_i$ = confidence for prediction $i$
- $y_i$ = 1 if prediction $i$ is correct, 0 otherwise

**Range:** [0, 1], lower is better

---

### 3. Cost-Weighted Metrics

#### Asymmetric Cost Loss

Security operations have asymmetric costs: missing a real attack (FN) is typically much more costly than a false alarm (FP).

$$\text{Cost} = \alpha \cdot FN + \beta \cdot FP$$

**Default weights:**
- $\alpha$ (FN cost) = 10.0 — Missing malware/attacks is expensive
- $\beta$ (FP cost) = 1.0 — False alarms waste analyst time

#### Cost-Weighted Accuracy
$$\text{CostAcc} = 1 - \frac{\text{Cost}}{N \cdot \max(\alpha, \beta)}$$

Normalized to [0, 1] range.

---

### 4. Abstention Metrics

When model outputs "Abstain", it declines to make a prediction.

#### Abstention Rate
$$\text{AbstainRate} = \frac{|\{i : \text{pred}_i = \text{Abstain}\}|}{N}$$

#### Accuracy on Non-Abstained
$$\text{AccNonAbstain} = \frac{TP + TN}{|\{i : \text{pred}_i \neq \text{Abstain}\}|}$$

#### Risk-Coverage Curve

Shows accuracy at different abstention thresholds based on confidence.

For threshold $\tau$:
- **Coverage** = fraction of examples with confidence ≥ $\tau$
- **Risk** = error rate on covered examples

**Area Under Risk-Coverage Curve (AURC):** Lower is better.

```python
def compute_aurc(predictions, actuals, confidences):
    thresholds = np.linspace(0, 1, 101)
    coverages, risks = [], []
    for tau in thresholds:
        mask = confidences >= tau
        coverage = mask.mean()
        if coverage > 0:
            risk = (predictions[mask] != actuals[mask]).mean()
        else:
            risk = 0.0
        coverages.append(coverage)
        risks.append(risk)
    return np.trapz(risks, coverages)
```

---

## Summary JSON Schema

The report generator produces a `summary.json` with these fields for E1:

```json
{
  "environment": "sv-env-network-logs",
  "version": "0.1.0",
  "run_id": "<uuid>",
  "timestamp": "<ISO8601>",
  "model": "<model_name>",
  "dataset": "<dataset_name>",
  "n_examples": 100,
  "metrics": {
    "detection": {
      "tpr": 0.85,
      "fpr": 0.10,
      "fnr": 0.15,
      "precision": 0.89,
      "f1": 0.87,
      "accuracy": 0.88
    },
    "calibration": {
      "ece": 0.08,
      "brier": 0.12
    },
    "cost": {
      "fn_cost_weight": 10.0,
      "fp_cost_weight": 1.0,
      "total_cost": 25.0,
      "cost_weighted_accuracy": 0.75
    },
    "abstention": {
      "abstain_rate": 0.05,
      "accuracy_non_abstained": 0.92,
      "aurc": 0.08
    }
  },
  "confusion_matrix": {
    "tp": 85,
    "tn": 88,
    "fp": 10,
    "fn": 15,
    "abstain": 5
  }
}
```

---

## Report Markdown Format

The `report.md` should include:

1. **Header** with run metadata
2. **Summary table** of key metrics
3. **Detection performance** section with confusion matrix
4. **Calibration analysis** with reliability diagram data
5. **Cost analysis** with asymmetric penalties
6. **Abstention analysis** with risk-coverage data

---

## Reward Function Reference

From `sv_shared/rewards.py`:

| Function | Formula | Weight |
|----------|---------|--------|
| `reward_accuracy` | 1.0 if correct, 0.0 otherwise | 1.0 |
| `reward_calibration` | 1.0 - \|confidence - correct\| | 0.2 |
| `reward_asymmetric_cost` | 1.0 if correct, -1.0 if FN, 0.0 if FP | 0.5 |
| `format_reward` | 1.0 if valid JSON, 0.0 otherwise | 0.1 |

Total reward = weighted sum, range approximately [-0.5, 1.8]
