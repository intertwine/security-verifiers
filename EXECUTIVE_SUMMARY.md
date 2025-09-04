# Open Security Verifiers — Executive Summary

**Goal.** Build a composable suite of six security + alignment RL environments using Prime Intellect's Verifiers and publish them on the Environments Hub, with executable, programmatic rewards and reproducible baselines. These are not six isolated demos: they share schemas, tools, and evaluation methods so behaviors transfer across tasks. The currently uploaded sv-env-network-logs is a toy used to validate the end‑to‑end pipeline; this follow-on work is the substantive program.

**Why this matters.** Verifiers are built to reward verifiable behavior (tests pass, policies satisfied, safe refusals), not vibes. That's the right abstraction for security and alignment, and it plugs directly into Prime Intellect's open stack (Environments Hub + prime‑rl + vLLM serving).

## The Suite (high level)

1. **Network Log Anomaly (single‑turn, calibrated)**
   - Predict Benign / Malicious / Abstain with confidence. Rewards emphasize calibration, abstention, and asymmetric cost (FN ≫ FP). Train on IoT‑23; OOD test on CIC‑IDS‑2017 and UNSW‑NB15.

2. **Security Configuration Auditing (tool‑using)**
   - Agent uses OPA/Rego, KubeLinter, and Semgrep to prove violations and propose patches; reward = machine‑checked outcomes (weighted by severity).

3. **Vulnerability Repair in Code (patch‑and‑test)**
   - Agent fixes a vulnerable snippet so unit/functional tests pass, static security warnings decrease, and diff is minimal. Data from Devign / Big‑Vul / Juliet / CodeXGLUE.

4. **Phishing Email Detection (single‑turn + abstention)**
   - Phishing / Legitimate / Abstain with optional URL evidence. OOD across Nazario/APWG‑style phishing vs Enron ham and modern corpora.

5. **Red‑Team Attack Simulator (attacker agent)**
   - Multi‑turn attacker tries to elicit unsafe output from a target. Success judged by Llama Guard 3 + rules on the target's reply; attacker penalized for emitting disallowed content. Benchmarked on JailbreakBench/HarmBench.

6. **Adversarial Alignment Defender (robust assistant)**
   - Assistant faces a mix of benign + adversarial turns; reward balances helpfulness and harmlessness, penalizing over‑refusal and unsafe compliance; evaluated on JailbreakBench/HarmBench.

## Shared Toolbox (used across all six)

- Strict JSON schemas + format rewards; zero reward for format drift. (Supported directly by Verifiers' rubrics/parsers.)
- Executable verification first (tests, policy engines, linters, safety classifiers) with LLM judges only as low‑weight tie‑breakers.
- Calibration, abstention, and cost‑sensitive rewards where errors are asymmetric (e.g., missed intrusion).
- Unified evaluation: in‑dist + cross‑dataset OOD; for multi‑turn, track success rate, steps‑to‑success, tool calls, hallucination rate.
- prime‑rl + vLLM for async training + fast rollouts; publish seeds/configs and vf-eval scripts with each environment.

## Deliverables & Impact

- Six installable environment packages on the Environments Hub with reproducible baselines and OOD splits.
- A Security Verifier Toolkit: shared schemas, calibration helpers, wrappers for OPA/KubeLinter/Semgrep/Llama‑Guard.
- Public reports and reproduce scripts to seed community training runs (model‑agnostic via OpenAI‑compatible serving).
