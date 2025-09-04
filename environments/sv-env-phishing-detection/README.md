# Phishing Email Detection (Work in Progress)

Security Verifiers RL environment for **Phishing Email Detection with Evidence-Seeking and Calibrated Abstention** - implementing Environment E4 from the [PRD](../../PRD.md).

## Overview

This environment (currently in development) will implement advanced phishing detection with:

- Classification as Phishing / Legitimate / **Abstain** (when uncertain)
- Calibrated confidence scores for risk-aware decision making
- Optional evidence extraction via tool calls (URL/domain reputation lookups)
- Strong penalties for false negatives reflecting real operational costs

## Planned Features (Per PRD Specification)

### Input/Output Schema

- **Input**: Email headers + body content
- **Output Schema**:

```json
{
  "label": "Phishing|Legitimate|Abstain",
  "confidence": 0.0..1.0,
  "evidence": ["url_or_header_feature", "..."]
}
```

### Reward Structure

- Exact label match reward
- Schema compliance bonus
- Calibration rewards for well-calibrated confidence
- Asymmetric cost penalties (false negatives >> false positives)
- Evidence quality bonus when tool calls provide verification

### Datasets

- Primary: Nazario/APWG-style phishing samples
- Legitimate baseline: Enron ham corpus
- Modern curated sets for OOD evaluation
- Cross-corpus testing to avoid overfitting

## Key Innovations

1. **Abstention Mechanism**: Unlike simple binary classification, the model can safely abstain when uncertain, critical for deployment where false positives have costs

2. **Evidence-Seeking**: Optional tool integration for URL/domain reputation lookups, encouraging verifiable reasoning

3. **Calibration Focus**: Rewards well-calibrated confidence scores, not just accuracy

4. **Operational Metrics**: Asymmetric penalties reflecting that missing a phishing email is worse than flagging a legitimate one

## Current Status

This environment is a work in progress. The current implementation provides basic phishing classification as a foundation. Future development will add:

- Abstention support with appropriate rewards
- Confidence calibration scoring
- Tool integration for evidence gathering
- Advanced reward shaping for operational priorities

See [PRD.md](../../PRD.md) Environment E4 for full specifications.

## Structure

- `sv_env_phishing_detection.py`: Main implementation file
- `sv_env_phishing_detection_test.py`: Test suite

## Local Install (editable)

From repo root after creating a uv venv:

```bash
uv pip install -e environments/sv-env-phishing-detection
```

## Related Work

This environment is part of the Open Security Verifiers suite. For the complete vision, see:

- [EXECUTIVE_SUMMARY.md](../../EXECUTIVE_SUMMARY.md) - Project overview
- [PRD.md](../../PRD.md) - Detailed specifications for all six environments
