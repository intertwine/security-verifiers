# Phishing Email Detection

Security Verifiers RL environment for **Phishing Email Detection with Evidence-Seeking and Calibrated Abstention** — implementing Environment E4 from the [PRD](../../PRD.md).

## Overview

`sv-env-phishing-detection` evaluates single-turn phishing triage. The environment now ships with:

- JSON outputs containing a `label`, `confidence`, and optional `evidence` strings.
- Abstention support for uncertain cases.
- Confidence calibration rewards in addition to accuracy.
- A phishing-specific asymmetric cost function that harshly penalises false negatives while rewarding safe abstentions.
- Evidence-alignment scoring that checks if the cited indicators match artefacts present in the email prompt or metadata.

The synthetic dataset distributed with the environment mixes credential harvesting, fake lottery, and SaaS phishing lures with realistic corporate ham mail. When a remote dataset cannot be downloaded the synthetic corpus is used automatically so the environment remains functional offline.

## Input/Output Schema

- **Input**: Single-turn prompt containing email headers (`From`, `Subject`) and body text.
- **Output** (model):

```json
{
  "label": "Phishing|Legitimate|Abstain",
  "confidence": 0.0–1.0,
  "evidence": ["indicator", "..."]
}
```

`evidence` is optional but rewarded when entries correspond to suspicious URLs, spoofed domains, or urgent phrases highlighted in the prompt metadata.

## Reward Structure

The rubric combines five weighted components:

| Reward | Description | Weight |
| --- | --- | --- |
| Accuracy | Label must match the ground truth. | 1.0 |
| Format | Valid JSON schema with allowed label and bounded confidence. | 0.2 |
| Calibration | Encourages well-calibrated confidence scores. | 0.2 |
| Asymmetric Cost | Strong penalties for missed phishing, moderate penalties for false alarms, reward for safe abstention. | 0.4 |
| Evidence Alignment | Awards supporting evidence that matches prompt indicators or metadata. | 0.2 |

## Dataset Transformation

`transform_dataset` normalises varied phishing corpora into the expected schema by:

1. Constructing a prompt from `sender`, `subject`, and email body.
2. Mapping integer or string labels into `Phishing`, `Legitimate`, or `Abstain`.
3. Extracting phishing indicators (URLs, urgent keywords, suspicious senders) to populate `metadata.phishing_indicators`. These are later used by the evidence reward.
4. Respecting a `max_examples` limit for quick smoke tests.

When a download fails a deterministic synthetic dataset of twelve labelled emails (six phishing, six legitimate) is produced for reliability.

## Local Install (editable)

From the repo root after creating a uv virtual environment:

```bash
uv pip install -e environments/sv-env-phishing-detection
```

## Files

- `sv_env_phishing_detection.py` — environment implementation and reward functions.
- `sv_env_phishing_detection_test.py` — test suite covering parser behaviour, rewards, dataset transformation, and environment wiring.

## Related Work

This environment is part of the Open Security Verifiers suite. For the complete vision, see:

- [EXECUTIVE_SUMMARY.md](../../EXECUTIVE_SUMMARY.md)
- [PRD.md](../../PRD.md)
