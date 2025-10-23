# Security Verifiers Research Plan

## 1. Vision and Goals

- **Primary outcome:** Benchmark and improve a portfolio of closed- and open-source language models on executable security RL environments (`sv-env-network-logs`, `sv-env-config-verification`, `sv-env-code-vulnerability`, `sv-env-phishing-detection`, `sv-env-redteam-attack`, `sv-env-redteam-defense`).
- **Hypotheses:**
  - Supervised fine-tuning (SFT) followed by RL fine-tuning (RLFT) with verifiable rewards yields measurable gains in calibration, tool-grounded reasoning, and safety responses.
  - Synthetic data targeted to each environment closes coverage gaps in public corpora and accelerates RLFT sample efficiency.
  - Iterative attacker/defender co-training (E5↔E6) reduces red-team success while maintaining assistance quality.
- **Success metrics:** Improvements over published baselines in reward components, calibration gaps <5%, reduced false negatives/unsafe responses, reproducible eval artifacts in `outputs/evals`.

## 2. Model Portfolio and Schedule

- **Closed-source:** `gpt-5` (flagship unified model with improved reasoning and tool routing[^1]), `gpt-5-mini`, `gpt-5-mini`, `Claude Sonnet 4.5` (latest coding-optimized Claude tier with extended context and safety tooling[^2][^3]). Run monthly baselines and quarterly RLFT (via Prime or Vertex endpoints, depending on provider SLAs).
- **Open-source base models:** `Qwen3-72B` and `Qwen3-235B-A22B` (Apache-2.0, hybrid reasoning modes[^4]), `Llama-3.1-8B`, `Llama-3-70B`, `Mixtral-8x22B` (for MoE comparisons). Serve via vLLM on A100s; nightly regression evals on unmodified checkpoints.
- **Intermediate checkpoints:** Track SFT-only, RLFT stage-1 (single environment), RLFT stage-2 (multi-environment curriculum), attacker/defender co-training cycles.
- **Evaluation cadence:**
  - Weekly quick sweep on E1–E4 using `make eval-e{1..4} MODELS="..." N=10` (subset for trend tracking).
  - Bi-weekly full eval including E5/E6 tournament (`make eval-e5`, `make eval-e6`).
  - Monthly consolidated benchmark report.

## 3. Environment Methodology Overview

| Env                     | Objective                        | Key Tools & Rewards                                                                                     | Baseline Actions                                                                   |
| ----------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| E1: Network Logs        | Calibrated anomaly detection     | `sv_shared.JsonClassificationParser`, `reward_accuracy`, `reward_calibration`, `reward_asymmetric_cost` | Zero-shot, IoT-23 SFT, RLFT with cost-aware rewards                                |
| E2: Config Verification | Tool-grounded policy enforcement | OPA/Rego, KubeLinter, Semgrep adapters (`environments/sv-env-config-verification/adapters`)             | Tool-oracle baseline, chain-of-thought SFT, RLFT on precision/recall + patch bonus |
| E3: Code Vulnerability  | Patch + test repairs             | Unified diff schema, pytest runners, Bandit/Semgrep checks                                              | Retrieval-augmented SFT, RLFT with executable test rewards                         |
| E4: Phishing Detection  | Evidence-seeking classification  | Evidence list schema, optional URL reputation tool                                                      | Cross-corpus SFT, RLFT for abstention calibration                                  |
| E5: Red-Team Attack     | Unsafe elicitation               | Llama Guard 3 scoring, novelty/length penalties                                                         | Prompt engineering baseline, RLFT with novelty rewards                             |
| E6: Red-Team Defense    | Helpful harmless responses       | Cost-balanced reward, attacker pairings                                                                 | Refusal-tuned SFT, defensive RLFT with offense-conditioning                        |

## 4. Data Strategy

### 4.1 Existing Datasets

- **E1:** IoT-23 (Hugging Face `19kmunz/iot-23-preprocessed`, updated Zeek features[^5]) for training; CIC-IDS-2017 + UNSW-NB15 for OOD.
- **E2:** GenKubeSec misconfiguration corpus (LLM-generated + expert-validated YAML/HCL pairs[^6]), Kubernetes policy samples (Datree, Kubesec), Terraform corpora, rule oracles (`datasets/oracle`).
- **E3:** Devign, Big-Vul, Juliet, CodeXGLUE defect detection, plus modern commit-level corpora from The Stack v2 (BigCode 67.5TB release[^7]); align failing tests with patches.
- **E4:** Enron ham, APWG phishing, and Hugging Face `zefang-liu/phishing-email-dataset` (18.7k labeled emails[^8]); include multilingual samples.
- **E5/E6:** JailbreakBench `JBB-Behaviors` (2025 refresh[^9]), HarmBench (Hugging Face `walledai/HarmBench` 2025 update[^10]), internal red-team transcripts (sanitized).

### 4.2 Synthetic Data Generation Recipes

- **Common pipeline:** (a) seed prompts from curated templates, (b) sample candidate completions via temperature sweeps, (c) enforce schema validation via `sv_shared.parsers`, (d) auto-label via environment verifiers, (e) human spot-check 5%.
- **E1:** Perturb real flows (IP swapping, random noise within valid ranges), simulate attack playbooks (port scans, exfiltration) with event generators, ensure label balance; augment with scenario tags for curriculum RL.
- **E2:** Programmatically mutate secure configs into vulnerable variants (toggle RBAC, disable encryption). Use tool adapters to confirm severity labels. Generate diff pairs with templated misconfigurations.
- **E3:** Apply mutation operators (off-by-one, missing sanitization) to clean code, generate tests that fail; leverage LLMs to draft plausible vulnerabilities, validate via test harness and Bandit/Semgrep.
- **E4:** Compose phishing campaigns using template libraries (credential harvest, invoice fraud), vary localization and obfuscation, include benign transactional emails; verify via heuristics and rule-based detectors.
- **E5:** Generate attacker goal trees combining jailbreak intents with novelty constraints. Use previous defender failures as seeds; automatically redact unsafe substrings before storage.
- **E6:** Simulate benign support conversations and adversarial probes; pair with synthetic attacker queries from E5; label desired responses via policy library (safe refusal templates, guided helpful completions).
- **Data governance:** Store synthetic corpora under `outputs/datasets/<env>/<date>` with metadata (`metadata.json` documenting provenance, seed models, verifier versions).

## 5. Training and Fine-Tuning Pipeline

1. **Environment setup:** `make setup`, source `.venv`, load `.env` with API keys (`OPENAI_API_KEY`, optional `WANDB_API_KEY`).
2. **SFT stage:**
   - Aggregate curated + synthetic datasets per env; convert to instruction format compatible with verifiers schemas.
   - Train with sequence-to-sequence or chat format depending on env; log to W&B project `security-verifiers-sft`.
3. **RLFT stage:**
   - Use Prime RL (`prime-rl`) with verifiers environments. For each env, run `prime-rl rollout --env sv-env-<name> --config configs/rlft/<env>.yaml`.
   - Apply reward shaping weights from environment configs; enable Weave auto-tracing for auditability.
   - Curriculum approach: single-env RLFT → mixed batches across envs → joint fine-tuning for attacker/defender.
4. **Checkpoints:** Save to `outputs/checkpoints/<model>/<stage>/<timestamp>`. Maintain config + reward weights snapshot.
5. **Safety reviews:** Before promoting checkpoints, run automated safe-content scanners and human review per risk guidelines (hash unsafe text, store metadata only).

## 6. Evaluation and Benchmarking

- **Automated evals:**
  - `make eval-e1 MODELS="..." N=32`, `make eval-e2 ... INCLUDE_TOOLS=true`, analogous commands for E3–E6 (refer to Makefile targets `e1`..`e6`).
  - Use `scripts/eval_<env>.py` for custom sweeps (e.g., larger N, tool toggles).
  - Store artifacts automatically in `outputs/evals/sv-env-<name>--<model>/<run_id>/` (`metadata.json`, `results.jsonl`).
- **Metrics tracking:**
  - Parse reward components into dashboards (calibration bins, patch success rate, jailbreak success). Feed into W&B / Weave dashboards via RolloutLogger.
  - Monitor false negative rates, abstention usage, tool invocation counts.
- **Cross-model comparisons:** Standardize seeds (`--seed 42`) and dataset slices. Use paired statistical tests (bootstrap over example rewards) to confirm deltas.
- **Regression gating:** Fail CI if reward drops >3% on core metrics; integrate into `make check` pipeline.

## 7. Iteration Loop and Ablations

1. **Triage:** Inspect low-reward trajectories via Weave traces; categorize errors (schema violations, reasoning gaps, tool misuse).
2. **Hypothesis formulation:** Create targeted synthetic batches or reward tweaks; document in `outputs/notes/<date>-iteration.md`.
3. **Fast eval:** Run `make eval-e<env> MODELS="candidate" N=10` to validate hypotheses.
4. **Full training:** Re-run SFT/RLFT as needed; record hyperparameters in `configs/experiments/<env>/<date>.yaml`.
5. **Ablations:**
   - Remove calibration bonus (E1/E4) to measure impact.
   - Disable patch reward (E2/E3) to quantify tool contributions.
   - Vary novelty weights (E5) and refusal penalties (E6).
6. **Attacker/Defender tournaments:** Alternate updates (E5 RLFT while freezing E6, then vice versa) until convergence or oscillation stabilizes.

## 8. Reporting and Governance

- **Weekly update:** Summary table (reward deltas, notable regressions), new synthetic data volumes, outstanding risks; share via internal memo and commit under `docs-internal/reports/<week>.md`.
- **Monthly report:** Comprehensive benchmark including closed + open models, calibration charts, attacker success curves. Export sanitized results for external sharing.
- **Audit trail:** Retain Weave runs, W&B experiments, dataset provenance metadata. Ensure reproducibility via pinned `uv.lock`, `configs/` versions, and `git tag` per milestone.
- **Risk & safety:** Apply content redaction pipeline before publishing artifacts; follow PRD risk mitigations. Document any reward model adjustments impacting safety.

## 9. Compute and Resource Planning

- **Infrastructure:** A100 80GB cluster for RLFT/vLLM serving; commodity GPUs (A10/A40) for SFT where feasible. Schedule attacker/defender tournaments during low-usage windows.
- **Throughput targets:**
  - E1/E4 single-turn rollouts: ≥2k trajectories/hour/model.
  - E2/E3 tool/coding loops: ≥500 trajectories/hour with caching of tool outputs.
  - E5/E6 multi-turn: ≥200 dialogues/hour due to length; leverage distributed rollout actors.
- **Cost tracking:** Attribute GPU hours per model/environment; evaluate cost-benefit of closed vs open checkpoints.

## 10. Next Actions

1. Stand up data pipelines for IoT-23 and config corpora; log provenance in `outputs/datasets`.
2. Establish baseline evals for all models via Make targets; publish initial benchmark sheet.
3. Kick off SFT runs for open-source models, prioritize E1/E2 coverage.
4. Plan RLFT experiment queue with curriculum schedule and safety reviews.
5. Begin synthetic data generation pilots for E2 and E5, validating verifiers before scaling.

## References

[^1]: Maxwell Zeff, "OpenAI says GPT-5 stacks up to humans in a wide range of jobs," _TechCrunch_, Sept 25, 2025. <https://techcrunch.com/2025/09/25/openai-says-gpt-5-stacks-up-to-humans-in-a-wide-range-of-jobs/>
[^2]: Frederic Lardinois, "Anthropic Launches Claude Sonnet 4.5," _The New Stack_, Sept 29, 2025. <https://thenewstack.io/anthropic-launches-claude-sonnet-4-5/>
[^3]: Google Cloud, "Claude Sonnet 4.5 | Generative AI on Vertex AI," Sept 29, 2025. <https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/sonnet-4-5>
[^4]: Qwen Team, "Qwen3: Think Deeper, Act Faster," Apr 28, 2025. <https://qwenlm.github.io/blog/qwen3/>
[^5]: Hugging Face, "19kmunz/iot-23-preprocessed," Oct 27, 2023. <https://huggingface.co/datasets/19kmunz/iot-23-preprocessed>
[^6]: Orel Mizrahi et al., "GenKubeSec: LLM-Based Kubernetes Misconfiguration Detection...," May 28, 2024. <https://arxiv.org/html/2405.19954v1>
[^7]: Hugging Face, "bigcode/the-stack-v2," Dec 5, 2024. <https://huggingface.co/datasets/bigcode/the-stack-v2>
[^8]: Hugging Face, "zefang-liu/phishing-email-dataset," Dec 5, 2024. <https://huggingface.co/datasets/zefang-liu/phishing-email-dataset>
[^9]: Hugging Face, "JailbreakBench/JBB-Behaviors," May 6, 2025. <https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors>
[^10]: Hugging Face, "walledai/HarmBench," Apr 23, 2025. <https://huggingface.co/datasets/walledai/HarmBench>
