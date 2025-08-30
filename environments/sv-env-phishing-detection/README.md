# sv-env-phishing-detection

Security Verifiers RL environment for **Phishing Email Detection** - a SingleTurnEnv implementation where models classify emails as phishing attempts or legitimate emails.

## Overview

This environment implements PRD Environment #4: A classification environment where the model must determine if a given email is a phishing attempt or a legitimate email. This is implemented as a single-turn Q&A: the prompt is the text of an email (possibly including subject, sender info, and body), and the model outputs a label like "Phishing" or "Legitimate".

## Task Description

- **Input**: Email text (subject, sender, body content)
- **Output**: Classification label ("Phishing" or "Legitimate")
- **Environment Type**: SingleTurnEnv (one email → one classification)
- **Reward**: Binary reward based on correct classification

## Example

```
Prompt: "Dear user, your account is compromised, click this link to reset password: http://suspicious-site.com/reset"
Expected Output: "Phishing"

Prompt: "Meeting reminder: Our quarterly review is scheduled for tomorrow at 2 PM in Conference Room B."
Expected Output: "Legitimate"
```

## Implementation

Uses the Verifiers framework with:
- Dataset: Phishing email datasets (e.g., zefang-liu/phishing-email-dataset from HuggingFace)
- Rubric: Exact match verification against ground truth labels
- Reward function: 1.0 for correct classification, 0.0 for incorrect
- System prompt: Instructs model to respond with classification label only

## Why This Task is Useful

- **Cybersecurity**: Phishing remains one of the most common cyber threats
- **Email Security**: Can be deployed in email filters or clients to flag phishing attempts
- **Language Understanding**: LLMs can understand context and semantics to catch novel phishing strategies
- **User Protection**: Helps protect users from scams and social engineering attacks
- **Adaptive Detection**: Can learn to recognize new phishing tactics through RL training

## Detection Capabilities

The model learns to identify:
- Deceptive language and urgent calls to action
- Suspicious URLs and domains
- Social engineering cues and manipulation tactics
- Spelling and grammar anomalies
- Requests for credentials or personal information
- Impersonation of trusted organizations

## Structure
- `src/sv_env_phishing_detection/`: Package sources
- `tests/`: Test suite

## Local install (editable)
From repo root after creating a uv venv:
```bash
uv pip install -e environments/sv-env-phishing-detection
```
