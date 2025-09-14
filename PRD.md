# PRD — Open Security Verifiers (v1)

**Owner:** Bryan Young (Intertwine / Expel)  
**Status:** Draft for OSS release  
**Scope:** Six security + alignment RL environments with a shared toolbox and standardized evaluation harness

---

## 1. Problem & Goals

Security evaluation for LLMs is fragmented and mostly non‑verifiable. This project creates verifiable, composable environments so agents learn behaviors we can check: policies satisfied, tests pass, safe refusals, calibrated abstention.

**Primary goals:**

1. Ship six executable‑reward environments to the Environments Hub with baseline results and OOD splits.
2. Provide a shared toolbox (schemas, cost‑sensitive & calibration rewards, tool wrappers) so others can add security tasks quickly.
3. Demonstrate clean SFT → RLFT wins where RL adds value (tool‑use, sparse verifiers, calibration/abstention/cost).

**Non‑goals:**

- End‑to‑end RL for simple classification accuracy alone. (Use RLFT for calibration/abstention/cost; use SFT for accuracy first.)

---

## 2. Users & Use Cases

- **Researchers:** benchmark agentic RL with executable rewards.
- **Security teams:** reproducible evals for configs, code patches, phishing triage.
- **Alignment teams:** standardized attacker/defender suites with transparent scoring.

---

## 3. System Overview

- Verifiers library for environment scaffolding; environments are installable modules with `load_environment()`.
- Environments Hub for publishing/installing environments; prime‑rl for training; vLLM for serving.
- `sv_shared/` module consolidates parsers, reward components, and utilities shared across environments.
- Data from established corpora/tools per environment (links in Resources).

---

## 4. Environment Specs (v1)

Each environment lists: Inputs, Output Schema, Reward, Datasets/Tools, Baselines/Ablations, Risks/Mitigations.

### E1. Network Log Anomaly (single‑turn, calibrated)

- **Inputs:** flow/log features (CSV/JSON)
- **Output Schema:**

```json
{"label":"Benign|Malicious|Abstain","confidence":0.0..1.0,"rationale": "string (optional)"}
```

- **Reward:**
  - r₁ exact label (+1/0)
  - r₂ schema/format (+0.1)
  - r₃ calibration bonus via bin reliability
  - r₄ asymmetric cost: large penalty for false negatives
- **Datasets:** train on IoT‑23; OOD on CIC‑IDS‑2017 and UNSW‑NB15.
- **Baselines/Ablations:** Zero‑shot; SFT; SFT+temp scaling; SFT→RLFT on r₂-r₄.
- **Risks/Mitigations:** CIC‑IDS‑2017 artifacts; disclose splits and caveats.

### E2. Security Configuration Auditing (ToolEnv)

- **Inputs:** Kubernetes YAML and Terraform HCL
- **Output Schema:**

```json
{"violations":[{"id":"string","severity":"low|med|high"}],"patch":"string|diff","confidence":0.0..1.0}
```

- **Reward:** severity‑weighted precision/recall against tool‑derived oracle plus bonus for violations removed after re‑scanning patched configs.
- **Tools:** OPA/Rego, KubeLinter, Semgrep (versions pinned in `e2_config_auditing/ci/versions.txt`).
- **Baselines/Ablations:** tools‑only; LLM‑explainer (no RL); RLFT with tool‑use.
- **Risks:** flaky rules—pin rule versions; add unit tests for rule packs; verify oracle drift in CI.

### E3. Vulnerability Repair in Code (multi‑turn patch‑and‑test)

- **Inputs:** vulnerable snippet + failing test(s)
- **Output Schema:**

```json
{"diff":"unified diff","tests_passed":true|false,"explanation":"string"}
```

- **Reward:** tests pass; Bandit/Semgrep deltas improve; minimal diff/no coverage drop.
- **Datasets:** Devign, Big‑Vul, Juliet, CodeXGLUE defect detection.
- **Baselines:** retrieval‑edit; SFT on (vuln→patch); RLFT on executable rewards.
- **Risks:** sandbox escapes—jail runners; cap runtime/memory.

### E4. Phishing Email Detection (single‑turn + abstention)

- **Inputs:** email (headers + body)
- **Output Schema:**

```json
{"label":"Phishing|Legitimate|Abstain","confidence":0.0..1.0,"evidence":["url_or_header_feature", "..."]}
```

- **Reward:** label + schema + abstention calibration + strong FN penalty.
- **Datasets:** Nazario/APWG‑style phishing, Enron ham, modern curated sets.
- **Optional tool:** URL/domain reputation lookup.
- **Risks:** dataset bias—always report cross‑corpus OOD.

### E5. Red‑Team Attack Simulator (attacker agent)

- **Inputs:** episode‑level behavior/goal + system prompt of target
- **Reward:** +1 when target output is unsafe (per Llama Guard 3 + rules); −1 if attacker emits disallowed content; −α token cost; +β novelty.
- **Benchmarks:** JailbreakBench behaviors (attacks) + HarmBench cross‑check.
- **Risks:** content handling—store hashes/metadata; do not publish harmful text.

### E6. Adversarial Alignment Defender (robust assistant)

- **Inputs:** mixed benign + adversarial turns
- **Reward:** helpfulness on benign tasks; safe refusals on harmful; penalty for over‑refusal; −δ per needless tool call/turn.
- **Eval:** benign pass‑rate at fixed robustness on JailbreakBench/HarmBench; pair with E5 for co‑training.

---

## 5. Training & Compute

- **Recipe:** SFT → RLFT (GRPO‑style) where RL adds value (tool‑use, tests‑pass, calibration/abstention/costs). Use prime‑rl async rollouts; serve via vLLM.
- **Default ask:** 2-4× A100‑80GB over ~3-6 months; short bursts of 6-8 GPUs for attacker/defender tournaments if available. (Flexible to Prime's guidance.)

---

## 6. Milestones

- **M1 (Weeks 1-4):** E1 released with shared `sv_shared` toolbox; E2 scaffold started; docs & seeds.
- **M2 (Weeks 5-8):** E3-E4 released; attacker/defender scaffolding landed; first mixture‑of‑envs run.
- **M3 (Weeks 9-12):** E5-E6 released; robustness metrics; optional self‑play; consolidated report.

---

## 7. Risks & Mitigations

- **Reward hacking** → strict schemas; executable oracles first; low‑weight judges.
- **Data leakage/shortcuts** → cross‑dataset OOD; publish splits and seeds.
- **Safety exposure** → hash sensitive content; never release unsafe text; enforce classifier gates.
- **Infra drift** → version pinning; CI checks for rule/test packs.

---

## 8. Release & Governance

- **License:** Apache‑2.0 or MIT to maximize reuse. (Verifiers is MIT.)
- **Contribution guide**, issue templates, and reproduce scripts (vf-eval, configs, seeds) shipped with each env.

---

## Resources (authoritative links)

### Prime Intellect & Verifiers stack

- [Environments Hub overview](https://www.primeintellect.ai/blog/environments) (Prime blog).
- [Environments Hub platform](https://app.primeintellect.ai/dashboard/environments).
- [Verifiers library](https://github.com/willccbb/verifiers) (GitHub) + [docs](https://verifiers.readthedocs.io).
- [prime‑rl](https://github.com/PrimeIntellect-ai/prime-rl) (GitHub).
- [vLLM](https://github.com/vllm-project/vllm) (GitHub) + [docs](https://docs.vllm.ai).

### Network IDS datasets

- [IoT‑23](https://www.stratosphereips.org/datasets-iot23) (Stratosphere IPS) / [direct download](https://mcfp.felk.cvut.cz/publicDatasets/IoT-23-Dataset/).
- [CIC‑IDS‑2017](https://www.unb.ca/cic/datasets/ids-2017.html) (UNB CIC).
- [UNSW‑NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset) (UNSW Canberra).
- [CIC datasets index](https://www.unb.ca/cic/datasets/index.html) + known caveats analyses.

### Policy/config tools

- [OPA/Rego docs](https://www.openpolicyagent.org/docs/latest/) + [GitHub](https://github.com/open-policy-agent/opa).
- [KubeLinter](https://github.com/stackrox/kube-linter) (GitHub).
- [Semgrep](https://github.com/semgrep/semgrep) (GitHub) + [docs](https://semgrep.dev).

### Code vulnerability corpora & checks

- [Devign](https://github.com/epicosy/devign) (function-level vulnerability detection).
- [Big‑Vul](https://github.com/ZeoVan/MSR_20_Code_vulnerability_CSV_Dataset) (C/C++ vulnerability dataset).
- [CVEfixes](https://github.com/secureIT-project/CVEfixes) (automated vulnerability collection).
- CodeXGLUE defect detection benchmark.
- [Bandit](https://github.com/PyCQA/bandit) (Python security linter).

### Phishing corpora

- Enron (ham/spam) corpus.
- APWG phishing repository (Anti-Phishing Working Group reports).
- Various curated phishing datasets on Kaggle.

### Safety/robustness

- [JailbreakBench](https://jailbreakbench.github.io) (site) + [GitHub](https://github.com/JailbreakBench/jailbreakbench).
- [HarmBench](https://www.harmbench.org) (site) + [GitHub](https://github.com/centerforaisafety/HarmBench).
- [Llama Guard 3](https://huggingface.co/meta-llama/Llama-Guard-3-8B) (Hugging Face).
