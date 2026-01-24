# Research Plan: Codex-Driven Security Model Benchmarking & Improvement

**Version:** 1.0
**Date:** 2025-09-30
**Project:** Security Verifiers RL Environments (Codex Program)

## Executive Summary

This plan defines a 24-week research program to benchmark and systematically improve both closed-source and open-source language models across the Security Verifiers reinforcement-learning environments. The work emphasizes reproducibility, state-of-the-art model coverage, data-backed insights, and iterative improvement via supervised fine-tuning (SFT) and reinforcement learning from task feedback (RLFT). All experiments reuse the repo's evaluation harness (`make eval-*`, `scripts/eval_*.py`) and roll out logging utilities in `sv_shared/`.

### Key Deliverables

- Baseline scorecard covering closed models (GPT-5, GPT-4.1, Claude Sonnet 4.5, Gemini 2.5 Pro) and open models (Qwen3-Omni-30B, Qwen3-VL-235B, DeepSeek-R1, DeepSeek-R1-Distill-Qwen-1.5B/14B, Llama-3.1 Instruct family, Mistral-Small-3) using the repo's six environments
- Synthetic and curated datasets aligned with each environment's reward schema, including ground-truth labels and metadata
- Fine-tuned checkpoints (open-source models) with verifiable gains over baselines, plus ablation studies
- RLFT recipes demonstrating safety-aware tool use and calibration improvements
- Rolling dashboards, weekly summaries, and a final executive report with recommendations

### Latest Model Landscape (as of 2025-09-30)

- **Closed source:** GPT-5 (OpenAI frontier, 2M context), GPT-4.1 (128K context, stable tool APIs), GPT-4o-mini (low-latency baseline), Claude Sonnet 4.5 (Anthropic, safety-optimized reasoning), Claude Opus 4.1 (1M context), Gemini 2.5 Pro (Google, multimodal security reasoning)
- **Open source:**
  - `Qwen/Qwen3-Omni-30B-A3B-Instruct`, `Qwen/Qwen3-VL-235B-A22B-Instruct`, `Qwen/Qwen3-VL-235B-A22B-Thinking` (Hugging Face API search, 2025-09-30)
  - `deepseek-ai/DeepSeek-R1`, `deepseek-ai/DeepSeek-R1-0528`, `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`, `deepseek-ai/DeepSeek-R1-0528-Qwen3-8B` (HF API search, 2025-09-30)
  - `meta-llama/Llama-3.1-8B-Instruct`, `meta-llama/Llama-3.1-8B` (HF API search, 2025-09-30) with larger 70B/405B checkpoints for multi-node runs
  - Complementary models for ablations: Mistral-Small-3 (24B), Phi-4-Mini (14B) for lightweight baselines

### Priority Public Datasets (Hugging Face, sampled 2025-09-30)

- **Network / Log Analysis (E1):** `baalajimaestro/DDoS-CICIoT2023` (last updated 2024-10-17), `jeype/CICIoT2023-Filtered` (2025-05-21), `Nora9029/NF-ToN-IoT-v2` (2024-04-01)
- **Config Verification (E2):** `walledai/CyberSecEval` (2024-10-18), `facebook/cyberseceval3-visual-prompt-injection` (2025-03-13) for tool-hard prompts, GitHub corpora of IaC manifests (Terraform, Helm) curated via GH Archive
- **Code Vulnerability (E3):** `DetectVul/CVEFixes` (2024-09-15), `MickyMike/cvefixes_bigvul` (2022-10-12), `neuralsentry/bigvul_devign_cvefixes_neuralsentry_commits` (2023-08-02)
- **Phishing Detection (E4):** `ealvaradob/phishing-dataset` (2024-01-31), `pirocheto/phishing-url` (2024-02-25) plus brand-new corporate phishing captures (internal collection via red-team operations)
- **Redteam Attack & Defense (E5/E6):** `JailbreakBench/JBB-Behaviors` (2024-09-26), `walledai/HarmBench` (2024-07-31), `davisrbr/jailbreakbench-goal-embeddings-augmented` (2024-11-22) for embedding-based augmentation

---

## 1. Research Goals

### Primary Objectives

1. Establish reproducible baselines across all environments for the selected closed/open models using `make eval-e1`/`make eval-e2` and custom eval scripts.
2. Close the performance gap between open and closed models via environment-aligned SFT and RLFT.
3. Achieve measurable improvements in reward (≥ +10% relative) and calibration metrics (Brier score, abstention) without regression on safety metrics.
4. Deliver reusable data generation pipelines and documentation to support future evaluations.

### Secondary Objectives

- Quantify model generalization with cross-environment transfer testing and held-out datasets (e.g., TON_IoT for E1, unseen IaC repos for E2).
- Explore tool-use strategies (`include_tools=True`) to maximize reward while controlling latency and cost.
- Provide decision support for deployment teams via dashboards and weekly reports.

### Non-Goals

- Training foundation models from scratch.
- Re-implementing third-party tools already encapsulated in the environments (e.g., kube-linter, semgrep).
- Publishing sensitive corporate data; synthetic pipelines must anonymize outputs.

---

## 2. Experimental Stack & Tooling

- **Environment Harness:** Use `make setup` (once), activate `.venv`, then rely on `make eval-e{1,2}` and `scripts/eval_*.py` for reproducible evals. Artifacts land in `outputs/evals/sv-env-{name}--{model}/...`.
- **Shared Utilities:** `sv_shared/parsers.py` for JSON strict parsing, `sv_shared/rewards.py` for accuracy/calibration utilities, `sv_shared/rollout_logging.py` for structured logs; integrate logging via `build_rollout_logger` when running long sweeps.
- **Model Adapters:** Closed models via hosted APIs (OpenAI, Anthropic, Google) with tool-calling toggles; open models served through vLLM / Text Generation Inference (TGI) with 8xA100 or H200 cluster.
- **Experiment Tracking:** Use Weights & Biases (or equivalent) for training runs; mirror evaluation metadata from `metadata.json` into tracking dashboards.
- **CI Safety:** Run `make check` before publishing results; enforce `make lint` and `make test` for custom scripts.

---

## 3. Program Timeline (24 Weeks)

1. **Phase 0 (Week 0):** Environment validation, `.env` provisioning, API credential setup.
2. **Phase 1 (Weeks 1-4): Baseline Evaluations**
   - Execute `make eval-e{1..6}` for each model; capture reward, latency, tool usage, cost.
   - Perform failure clustering and qualitative analysis of transcripts; log in shared Obsidian vault.
3. **Phase 2 (Weeks 5-8): Data Curation & Synthetic Pipelines**
   - Harvest public datasets listed above; build cleaning scripts under `scripts/data/` (new module) with documented provenance.
   - Launch synthetic data jobs per environment (details in Section 4) with dataset cards.
4. **Phase 3 (Weeks 9-14): SFT Training**
   - Run instruction-tuning on open models using curated + synthetic corpora; iterate with `sv_shared` format validators.
   - Evaluate after each epoch subset via `make eval-e*` nightly.
5. **Phase 4 (Weeks 15-19): RLFT**
   - Apply PPO/DPO-style reward optimization using environment signals; integrate tool-calling policies and log safety metrics.
6. **Phase 5 (Weeks 20-22): Transfer & Stress Testing**
   - Cross-evaluate SFT/RLFT models on OOD datasets; run multi-env episodes mixing tasks.
7. **Phase 6 (Weeks 23-24): Reporting & Handoff**
   - Compile executive summary, technical appendix, and release candidate datasets/models.

Milestones include go/no-go reviews at the ends of Phases 1, 3, and 5.

---

## 4. Environment-Specific Strategies

### E1: Network Log Classification (`sv-env-network-logs`)

- **Baseline Eval:** Use `make eval-e1 MODELS="..."` to batch-run logs. Capture class confusion, detection thresholds.
- **Data Curation:** Merge CICIoT2023 variants (`baalajimaestro/DDoS-CICIoT2023`, `jeype/CICIoT2023-Filtered`) with `Nora9029/NF-ToN-IoT-v2`. Normalize features (flow stats, payload signatures) to match environment parser expectations.
- **Synthetic Generation:**
  - Simulate IoT attack flows via open IDS simulators (e.g., `scapy`, `kitsune`) producing labeled PCAPs; transform to CSV features.
  - Use generative models to augment descriptive metadata (attack types, asset context) for natural-language log summaries consumed by models.
  - Introduce controlled noise (timestamp jitter, missing fields) to improve robustness.
- **Fine-Tuning:** Train SFT on mixture of curated + synthetic logs; for RLFT, reward on correct classification + calibrated confidence from environment's reward function.
- **Evaluation:** Track F1, false-positive rate per attack family, and cost-sensitive metrics. Use `scripts/eval_network_logs.py` with `--rollout-log` to capture trajectory detail.

### E2: Config Verification (`sv-env-config-verification`)

- **Baseline Eval:** Run `make eval-e2 MODELS="..." INCLUDE_TOOLS=true` to enable kube-linter, semgrep, OPA tools.
- **Data Curation:** Pull IaC manifests from public repos (GitHub security advisories, OpenTofu registry) and align with `walledai/CyberSecEval` & `facebook/cyberseceval3-visual-prompt-injection` prompts.
- **Synthetic Generation:**
  - Programmatically mutate secure configs using `patching.py` helpers to inject vulnerabilities (e.g., open ports, misconfigured RBAC).
  - Use rule-driven generators to produce policy-as-code (OPA, Rego) scenarios with corresponding violation explanations.
  - Auto-generate tool outputs by re-running kube-linter/semgrep on mutated configs to provide ground-truth findings.
- **Fine-Tuning:** Train SFT models to produce `Violation` schemas (matching `schema.py`) and actionable patches. For RLFT, reward both detection accuracy and patch correctness using `reward_config_auditing`.
- **Evaluation:** Evaluate precision/recall per severity, patch success rate (apply patch + re-scan). Track tool usage success/failure and latency for closed vs open models.

### E3: Code Vulnerability Remediation (`sv-env-code-vulnerability`)

- **Baseline Eval:** Execute targeted pytest suites or `make eval-e3` (add Make target if missing) focusing on `dataset/oracle` cases.
- **Data Curation:** Use `DetectVul/CVEFixes`, `MickyMike/cvefixes_bigvul`, and curated GitHub security fix commits. Normalize to environment's patch format.
- **Synthetic Generation:**
  - Leverage symbolic execution or lint tools (Infer, Semgrep) to identify templates; ask top-tier closed models to draft vulnerabilities, then compile with tests.
  - Auto-generate diff-style training pairs using templated bug injection (null deref, auth bypass) with verifying unit tests executed via `pytest` or containers.
  - Distill reasoning traces from closed models (chain-of-thought) into filtered SFT corpora.
- **Fine-Tuning:** Weighted curriculum: start with simple vulnerabilities, progress to complex multi-file fixes. RLFT with reward shaping for passing tests while minimizing diff size.
- **Evaluation:** Run `make test-env E=code-vulnerability` after each checkpoint; track success rate, regression count, and edit distance metrics.

### E4: Phishing Detection (`sv-env-phishing-detection`)

- **Baseline Eval:** Use `make eval-e4` (add new Make target mirroring scripts) or call environment loader directly with `uv run`. Capture classification accuracy and explanation quality.
- **Data Curation:** Combine `ealvaradob/phishing-dataset`, `pirocheto/phishing-url`, corporate security awareness datasets (if accessible) with metadata (URL source, email headers).
- **Synthetic Generation:**
  - Conditioned generation using style transfer: take benign emails, inject phishing markers (urgency language, brand spoof) with templates.
  - Partner with red-team to generate scenario-based emails; annotate using multi-annotator consensus for reliability.
  - Generate explanation/justification fields for training consistent rationales.
- **Fine-Tuning:** Emphasize dual-head outputs (classification + rationales) with label smoothing for borderline cases. RLFT encouraging calibrated abstain when evidence insufficient.
- **Evaluation:** Analyze confusion matrix, cost-sensitive metrics (false negatives weighted higher). Monitor explanation faithfulness using verification heuristics.

### E5: Redteam Attack Simulation (`sv-env-redteam-attack`)

- **Baseline Eval:** Execute `make eval-e5` with `INCLUDE_TOOLS` toggled to test tool-assisted attacks.
- **Data Curation:** Use `JailbreakBench/JBB-Behaviors`, `walledai/HarmBench`, `davisrbr/jailbreakbench-goal-embeddings-augmented`. Augment with internal red-team transcripts (sanitized).
- **Synthetic Generation:**
  - Use adversarial self-play: pair open-source attacker with defender model, collect successful attack transcripts.
  - Apply goal-conditioned generation (embedding prompts from `JBB` augmented sets) to create novel attack strategies.
  - Generate negative samples (defensive refusals) for contrastive training.
- **Fine-Tuning:** SFT attacker models on curated successes to evaluate defenses. RLFT: maximize environment reward while constraining to defined ethical sandbox (simulate but do not execute harmful actions).
- **Evaluation:** Track success rates, step counts, tool invocation patterns. Provide taxonomy of attack vectors per evaluation.

### E6: Redteam Defense (`sv-env-redteam-defense`)

- **Baseline Eval:** Run `make eval-e6` to score refusal quality and threat classification.
- **Data Curation:** Mirror E5 transcripts, plus curated safety corpora (Anthropic Responsible Scaling dataset, `walledai/HarmBench` refusal annotations).
- **Synthetic Generation:**
  - Counterfactual augmentation: transform known harmful prompts into benign variants to reduce over-refusal.
  - Use closed models (Claude Sonnet 4.5, GPT-5) to draft high-quality defensive responses; filter via reward model for policy compliance.
  - Build taxonomy-aligned prompts (policy categories) ensuring coverage of security-related threats.
- **Fine-Tuning:** Multi-task SFT balancing refusal strength and helpful fallback guidance. RLFT targeting environment reward + penalty for false positives.
- **Evaluation:** Monitor refusal accuracy, helpful alternative suggestions, calibration on ambiguous prompts, and alignment with policy categories.

---

## 5. Training & Optimization Pipelines

1. **Data Processing**

   - Implement standardized schema validators per environment (`pydantic` models matching `schema.py`).
   - Version datasets via DVC or LakeFS; include README with provenance, license, and hashing.
   - Split into train/dev/test (70/15/15) with environment-specific stratification.

2. **Supervised Fine-Tuning**

   - Use LoRA/QLoRA for 8B-32B models; full finetuning for 70B+ on multi-node cluster.
   - For each environment, train single-task and multi-task variants; document hyperparameters (lr, warmup, sequence length).
   - Validate outputs with repo parsers (`JsonClassificationParser`) to ensure format compliance.

3. **RLFT (Reward Modeling & Policy Optimization)**

   - Reuse environment reward functions as online scorers via API wrappers.
   - Optionally train learned reward models on environment logs to accelerate offline RL.
   - Apply PPO/SFT mixture, evaluating stability with gradient clipping and KL penalties to maintain instruction adherence.

4. **Tool-Use Optimization**
   - For tool-enabled environments, distill tool-calling strategies by logging tool invocation success/failure and training policy head to predict when to call each tool.
   - Evaluate costs (latency, API usage) to guide production deployment decisions.

---

## 6. Evaluation, Diagnostics, and QA

- **Automation:** Integrate eval runs into nightly cron (GitHub Actions or internal scheduler) invoking `make eval-e*` for changed checkpoints.
- **Metrics Dashboard:** Aggregate reward, precision/recall, calibration scores, cost metrics (latency, tokens) into a single dashboard (Grafana/W&B).
- **Qualitative Review:** Weekly manual inspection of 50 random rollouts per environment to spot systematic failures.
- **Regression Testing:** Maintain golden baselines; if new checkpoint underperforms by >2% on any metric, auto-create investigation ticket.
- **Safety QA:** For E5/E6, run additional Red Team harness (e.g., `CyberSecEval` categories) to ensure no regressions in safety posture.

---

## 7. Iteration & Reporting Cadence

- **Weekly:** Publish updates summarizing dataset additions, training progress, eval deltas, blockers.
- **Biweekly Tech Review:** Present deep dives on failure modes, synthetic data QA outcomes, and planned mitigations.
- **Phase Gates:** Structured reviews at Phases 1, 3, and 5 with go/no-go decisions and budget updates.
- **Final Deliverables:**
  - Technical report with methodology, results, ablations, and reproducibility checklist.
  - Executive briefing focusing on risk reductions, cost-benefit analysis, and deployment readiness.
  - Repository updates: new data scripts, evaluation configs, README additions documenting new capabilities.

---

## 8. Risk Assessment & Mitigations

- **Data Quality Drift:** Mitigate via automated validation suites and manual spot checks; track dataset versions.
- **Compute Bottlenecks:** Schedule GPU usage, prioritize LoRA adapters, and pre-filter data for lightweight ablations.
- **API Rate Limits (Closed Models):** Cache eval results, stagger runs, coordinate tokens with vendor SLAs.
- **Safety Concerns:** Ensure synthetic data generation adheres to internal policies; run defensive alignment checks before releasing artifacts.
- **Tool Breakage:** Monitor adapter versions (`environments/sv-env-config-verification/ci/versions.txt`); pin container images used in evals.

---

## 9. Next Steps

1. Provision credentials, confirm `make setup` success, and run a smoke test with `make eval-e1 MODELS="gpt-5-mini" N=2`.
2. Stand up evaluation job templates (one per environment) in the internal orchestrator.
3. Kick off baseline data pulls from the highlighted Hugging Face datasets; log provenance in `docs/data-sources.md`.
4. Draft detailed SOPs for synthetic data pipelines; review with security & legal stakeholders before execution.
