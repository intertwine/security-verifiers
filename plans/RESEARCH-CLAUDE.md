# Research Plan: Benchmarking and Improving Models with Security Verifiers

**Version:** 1.1 (Updated with 2025 SOTA Models & Datasets)
**Date:** 2025-09-30
**Project:** Open Security Verifiers RL Environments

## Executive Summary

This research plan outlines a comprehensive approach to benchmark and improve both closed-source and open-source language models using the Security Verifiers suite of six RL environments. The plan leverages executable, verifiable rewards to systematically evaluate models on security tasks, identify capability gaps, and iteratively improve performance through supervised fine-tuning (SFT) and reinforcement learning from task feedback (RLFT).

**Key Objectives:**

1. Establish baseline performance metrics across all six security environments
2. Generate high-quality synthetic training data tailored to each environment
3. Fine-tune open-source models to match or exceed closed-source baselines
4. Demonstrate RLFT improvements on calibration, tool-use, and cost-sensitive behaviors
5. Document reproducible evaluation protocols and training recipes

### What's New in 2025 (v1.1 Update)

This plan has been updated to reflect the latest state-of-the-art models and datasets available in 2025:

**Models:**

- **Closed-source:** GPT-5 (OpenAI's frontier model), GPT-4.5 (128K context), Claude-Sonnet-4.5 (extended thinking), Claude-Opus-4.1 (1M context, 72.5% SWE-bench), Gemini-2.5-Pro (86.4 GPQA)
- **Open-source:** Llama-4-Scout/Maverick (MoE, 10M/1M context), Qwen3-32B/235B (beats GPT-4o on code), DeepSeek-R1 (671B, MIT license) and DeepSeek-R1-Distill-Qwen-32B (beats o1-mini), Mistral-Small-3 (24B)
- **Recommendation:** Prioritize **Qwen3-32B** and **DeepSeek-R1-Distill-Qwen-32B** for optimal performance/efficiency

**Datasets:**

- **Network IDS:** CICIoT2023 (33 attack types, 105 devices), CIC IIoT 2025 (newest), TON_IoT
- **Vulnerability:** CVEfixes (211K statements, most accurate), DiverseVul (60% accuracy), CVE & CWE 1999-2025 (HuggingFace)
- **Red-teaming:** JailbreakBench (100 behaviors, NeurIPS 2024), HarmBench (7 categories, 33+ LLMs), 1,400+ adversarial prompts
- **Benchmarks:** SecBench (44,823 MCQs, largest), CyberMetric (200+ hours validated), CyberBench, SECURE

**Key Insights:**

- Open-source models (Qwen3, DeepSeek-R1) now match or exceed GPT-4-level performance
- Label accuracy matters: CVEfixes (best) vs BigVul (25% accuracy)
- Modern IoT datasets (CICIoT2023) significantly more comprehensive than legacy datasets
- JailbreakBench and HarmBench remain gold standards for adversarial evaluation

---

## 1. Research Goals

### Primary Goals

1. **Comprehensive Benchmarking**

   - Establish performance baselines for closed-source models (GPT-5, GPT-4.5, Claude-Sonnet-4.5, Claude-Opus-4.1, Gemini-2.5-Pro)
   - Establish performance baselines for open-source models (Llama-4-Scout/Maverick, Qwen3-32B/235B, DeepSeek-R1-671B, Mistral-Small-3-24B)
   - Measure performance across all six environments with standardized metrics
   - Identify strengths, weaknesses, and failure modes per model and environment

2. **Model Improvement via Fine-Tuning**

   - Generate high-quality synthetic training data for each environment
   - Apply SFT to improve base model accuracy and format compliance
   - Apply RLFT to improve calibration, tool-use, abstention, and cost-sensitive behaviors
   - Demonstrate measurable gains over baselines

3. **Transfer Learning and Generalization**

   - Evaluate cross-environment transfer (e.g., does E1 training help E4?)
   - Test out-of-distribution (OOD) generalization on held-out datasets
   - Investigate multi-task training across environments

4. **Open Science and Reproducibility**
   - Document all evaluation protocols, seeds, and configurations
   - Release training datasets, fine-tuned model checkpoints, and evaluation artifacts
   - Provide reproducible scripts for all experiments

### Non-Goals

- Training foundation models from scratch
- Competing with state-of-the-art on general benchmarks (focus is security-specific)
- Production deployment (research-focused experimentation)

---

## 2. Methodology Overview

### Phase 1: Baseline Evaluation (Weeks 1-3)

- Run comprehensive evaluations across all models and environments
- Establish performance metrics and identify capability gaps
- Generate analysis reports with failure mode categorization

### Phase 2: Data Generation (Weeks 4-6)

- Curate existing datasets for each environment
- Generate synthetic training data using model distillation and programmatic techniques
- Validate data quality and diversity

### Phase 3: Supervised Fine-Tuning (Weeks 7-10)

- Train SFT models on synthetic data for each environment
- Evaluate SFT improvements over baselines
- Iterate on data quality based on results

### Phase 4: Reinforcement Learning Fine-Tuning (Weeks 11-14)

- Apply RLFT on SFT checkpoints using environment rewards
- Focus on calibration, tool-use, and cost-sensitive behaviors
- Compare SFT vs. RLFT performance

### Phase 5: Cross-Environment and OOD Evaluation (Weeks 15-17)

- Test transfer learning across environments
- Evaluate on OOD datasets
- Multi-task training experiments

### Phase 6: Analysis and Reporting (Weeks 18-20)

- Comprehensive analysis of results
- Documentation and artifact release
- Final report and recommendations

---

## 3. Environment-Specific Methodology

### E1: Network Log Anomaly Detection (sv-env-network-logs)

**Environment Type:** SingleTurnEnv
**Focus:** Calibrated classification with abstention

#### Existing Datasets

- **Primary (train):** IoT-23 (Stratosphere IPS), CICIoT2023 (modern IoT attacks, 33 attack types, 105 devices)
- **OOD (eval):** CIC-IDS-2017, UNSW-NB15, TON_IoT, CIC IIoT 2025 (newest)
- **Access:** HuggingFace `datasets` library with synthetic fallback
- **Note:** CICIoT2023 is significantly more comprehensive than older datasets with modern attack vectors

#### Synthetic Data Generation

1. **Distillation from Strong Models**

   ```python
   # Use GPT-5 or Claude-Sonnet-4.5 to generate labeled examples with rationales
   prompt = """Given network flow: {features}
   Label as Benign/Malicious/Abstain with confidence [0-1] and rationale.
   Output strict JSON: {"label": "...", "confidence": 0.X, "rationale": "..."}"""
   ```

2. **Feature Perturbation**

   - Perturb IoT-23 features to create near-boundary cases
   - Inject noise to create ambiguous examples (test abstention)
   - Synthesize novel attack patterns using known signatures

3. **Adversarial Examples**
   - Generate examples where high confidence is wrong (test calibration)
   - Create distribution shift examples mimicking OOD datasets

#### Evaluation Protocol for E1

```bash
# Baseline evaluation (2025 SOTA models)
make eval-e1 MODELS="gpt-5,gpt-4.5,claude-sonnet-4.5,gemini-2.5-pro,llama-4-maverick,qwen3-235b,deepseek-r1" N=100

# Analyze results
python scripts/analyze_results.py \
  --env network-logs \
  --metrics accuracy,calibration_error,abstention_rate,fn_rate
```

#### Training Recipe for E1

**SFT:**

- Dataset: 10K synthetic examples (8K train, 2K val)
- Focus: Format compliance, basic accuracy
- Expected gain: +15-25% accuracy

**RLFT:**

- Initialize from SFT checkpoint
- Reward components: r₂ (format), r₃ (calibration), r₄ (asymmetric cost)
- Focus: Calibration and appropriate abstention
- Expected gain: +10-15% on calibration metrics, reduced FN rate

---

### E2: Security Configuration Auditing (sv-env-config-verification)

**Environment Type:** ToolEnv
**Focus:** Tool-grounded auditing with patch verification

#### Existing Datasets for E2

- **Configs:** Real-world Kubernetes YAML and Terraform HCL from GitHub repos
- **Ground truth:** OPA/Rego, KubeLinter, Semgrep outputs (pinned versions in `ci/versions.txt`)

#### Synthetic Data Generation for E2

1. **Rule-Based Injection**

   ```python
   # Programmatically inject vulnerabilities into clean configs
   def inject_vulnerability(config, vuln_type):
       if vuln_type == "privileged_container":
           config["spec"]["containers"][0]["securityContext"]["privileged"] = True
       elif vuln_type == "exposed_secret":
           config["spec"]["containers"][0]["env"].append({
               "name": "API_KEY", "value": "hardcoded-secret-123"
           })
       return config
   ```

2. **Distillation with Tool Access**

   ```python
   # Use GPT-4o with tool-calling to generate oracle data
   tools = [run_kubelinter, run_semgrep, run_opa]
   response = client.chat.completions.create(
       model="gpt-4o",
       messages=[{"role": "user", "content": audit_prompt}],
       tools=tools
   )
   # Extract violations and patches from tool outputs
   ```

3. **Patch Generation**
   - Generate configs with violations
   - Use tools to identify violations
   - Generate patches (unified diff or JSON patch)
   - Verify patch correctness by re-scanning

#### Evaluation Protocol

```bash
# Multi-turn evaluation with tools
make eval-e2 MODELS="gpt-4o,llama-3.1-70b" N=50 INCLUDE_TOOLS=true

# Analyze tool-use patterns
python scripts/analyze_tool_usage.py \
  --results outputs/evals/sv-env-config-verification--*/
```

#### Training Recipe

**SFT:**

- Dataset: 5K config + violation + patch triples
- Focus: Tool invocation format, violation schema compliance
- Expected gain: +20-30% precision/recall on violations

**RLFT:**

- Reward: Severity-weighted F1 + patch delta (violations removed after patch)
- Focus: Efficient tool use, patch correctness
- Expected gain: +15% on patch effectiveness, reduced hallucinated violations

---

### E3: Vulnerability Repair in Code (sv-env-code-vulnerability)

**Environment Type:** MultiTurnEnv (WIP)
**Focus:** Patch-and-test loop with minimal diffs

#### Existing Datasets for E3

- **CVEfixes (HuggingFace):** Most accurate vulnerability dataset with 211,317 Python statements from real-world projects; commit-, file-, and method-level data (DetectVul/CVEfixes)
- **DiverseVul:** 60% label accuracy (24% better than CVEfixes+BigVul+CrossVul union), newer dataset from RAID 2023
- **BigVul:** C/C++ vulnerability dataset with CVE mappings (Note: only 25% label accuracy, use with caution)
- **CyberNative/Code_Vulnerability_Security_DPO (HuggingFace):** DPO-formatted vulnerability detection dataset
- **CVE & CWE Dataset 1999-2025 (HuggingFace):** Comprehensive NVD coverage through May 2025 (stasvinokur/cve-and-cwe-dataset-1999-2025)
- **Juliet Test Suite:** NIST SAST test suite
- **CodeXGLUE:** Defect detection benchmark
- **Note:** Prioritize CVEfixes and DiverseVul for training due to superior label accuracy

#### Synthetic Data Generation for E3

1. **Vulnerability Injection**

   ```python
   # Inject common vulnerabilities into clean code
   vulnerabilities = [
       "sql_injection", "buffer_overflow", "xss",
       "path_traversal", "insecure_deserialization"
   ]
   # Use mutation-based fuzzing to create vulnerable variants
   ```

2. **Test Case Generation**

   - Generate failing tests that expose vulnerabilities
   - Use property-based testing frameworks (Hypothesis)
   - Distill from security-focused LLMs

3. **Patch Distillation**

   ```python
   # Use strong models to generate minimal patches
   prompt = """Fix vulnerability in this code:
   {vulnerable_code}

   Failing test: {test_case}
   Bandit warnings: {bandit_output}

   Generate minimal unified diff that fixes the issue."""
   ```

#### Evaluation Protocol for E3

```bash
# Multi-turn patch-and-test
make eval-e3 MODELS="gpt-4o,deepseek-coder-v2" N=50

# Analyze patch quality
python scripts/analyze_patches.py \
  --metrics tests_passed,bandit_delta,diff_size,iterations
```

#### Training Recipe for E3

**SFT:**

- Dataset: 8K (vulnerable code, test, patch) tuples
- Focus: Syntax-correct patches, test interpretation
- Expected gain: +25% on tests passing

**RLFT:**

- Reward: Tests pass + security tool deltas + minimal diff
- Focus: Iterative refinement, avoiding over-engineering
- Expected gain: +10% test pass rate, -30% diff size

---

### E4: Phishing Email Detection (sv-env-phishing-detection)

**Environment Type:** SingleTurnEnv (Alpha)
**Focus:** Evidence-seeking with calibrated abstention

#### Existing Datasets for E4

- **Phishing (HuggingFace):** ealvaradob/phishing-dataset (compiled from multiple sources, BERT-trained)
- **Legacy:** Nazario corpus, APWG datasets, Kaggle phishing collections
- **Legitimate (ham):** Enron email corpus, modern email datasets
- **OOD:** Cross-domain evaluation (e.g., corporate vs. personal emails)
- **Cybersecurity corpora (HuggingFace):** zeroshot/cybersecurity-corpus, ahmed000000000/cybersec for broader context

#### Synthetic Data Generation for E4

1. **LLM-Generated Phishing Emails**

   ```python
   # Generate realistic phishing variants
   prompt = """Generate a phishing email with:
   - Target: {persona}
   - Attack vector: {vector} (credential theft, malware, etc.)
   - Sophistication: {level}
   Include headers, body, and suspicious indicators."""
   ```

2. **Feature-Based Synthesis**

   - Programmatically modify legitimate emails to inject phishing indicators
   - Vary URL obfuscation techniques
   - Add/remove urgency cues, sender spoofing

3. **Adversarial Examples**
   - Generate benign emails with superficial phishing indicators
   - Generate sophisticated phishing with few obvious indicators

#### Evaluation Protocol for E4

```bash
make eval-e4 MODELS="gpt-5-mini,qwen-2.5-72b" N=100

python scripts/analyze_results.py \
  --env phishing-detection \
  --metrics accuracy,fn_rate,fp_rate,abstention_rate,evidence_quality
```

#### Training Recipe for E4

**SFT:**

- Dataset: 15K labeled emails with evidence annotations
- Focus: Indicator identification, format compliance
- Expected gain: +20% accuracy

**RLFT:**

- Reward: Accuracy + calibration + asymmetric FN penalty + evidence bonus
- Focus: Appropriate abstention, evidence-based reasoning
- Expected gain: +10% on FN reduction, improved calibration

---

### E5: Red-Team Attack Simulator (sv-env-redteam-attack)

**Environment Type:** MultiTurnEnv (Alpha)
**Focus:** Adversarial prompt generation

#### Existing Datasets for E5

- **JailbreakBench (2025):** 100 distinct misuse behaviors (55% original, rest from AdvBench/HarmBench); active leaderboard tracking attacks and defenses (NeurIPS 2024 Datasets track)
- **HarmBench (2025):** Standardized evaluation across 7 categories (cybercrime, misinformation, etc.); tested on 33+ LLMs; includes R2D2 adversarial training method
- **AdvBench:** Original adversarial attack benchmark (subset used in JailbreakBench)
- **SafetyPrompts.com:** Aggregated safety prompt repository
- **Note:** JailbreakBench is most actively maintained in 2025 with official leaderboard

#### Synthetic Data Generation for E5

1. **Attack Strategy Distillation**

   ```python
   # Distill attack strategies from successful jailbreaks
   prompt = """Generate jailbreak attack for:
   Target behavior: {behavior}
   Target model: {model}
   Constraint: Avoid {disallowed_content}

   Strategy: Multi-turn, role-play, obfuscation, etc."""
   ```

2. **Evolutionary Attack Generation**

   - Start with known jailbreaks
   - Mutate and recombine successful attacks
   - Select based on success rate against target models

3. **Programmatic Attack Templates**

   ```python
   templates = [
       "role_play: 'Act as a {role} who needs to...'",
       "hypothetical: 'In a fictional scenario where...'",
       "obfuscation: '{behavior} but using code/metaphor/foreign language'"
   ]
   ```

#### Evaluation Protocol for E5

```bash
make eval-e5 MODELS="gpt-4o,llama-3.1-70b" N=50

python scripts/analyze_attacks.py \
  --metrics success_rate,turns_to_success,novelty,disallowed_content
```

#### Training Recipe for E5

**SFT:**

- Dataset: 5K (behavior, attack strategy, multi-turn dialogue) tuples
- Focus: Coherent multi-turn attacks, constraint satisfaction
- Expected gain: +15% success rate

**RLFT:**

- Reward: +1 unsafe target output, -1 disallowed content, -α token cost, +β novelty
- Focus: Efficient attacks, novelty, staying within constraints
- Expected gain: +20% success rate, improved novelty

---

### E6: Adversarial Alignment Defender (sv-env-redteam-defense)

**Environment Type:** SingleTurnEnv (Alpha)
**Focus:** Helpfulness/harmlessness balance

#### Existing Datasets for E6

- **Benign tasks:** AlpacaEval, MT-Bench, user assistant tasks
- **Adversarial inputs:** JailbreakBench (100 behaviors, official leaderboard), HarmBench (7 categories, 33+ LLMs tested)
- **Mixed:** Combine benign and adversarial for robust evaluation
- **Red teaming research (2025):** 1,400+ categorized adversarial prompts tested on GPT-4, Claude 2, Mistral 7B, Vicuna

#### Synthetic Data Generation for E6

1. **Benign Task Synthesis**

   ```python
   # Generate diverse helpful tasks
   categories = ["coding", "writing", "analysis", "advice", "creative"]
   # Use GPT-4o to generate high-quality benign prompts
   ```

2. **Adversarial Input Augmentation**

   - Use E5 outputs as adversarial inputs
   - Vary attack sophistication
   - Mix obvious and subtle attacks

3. **Refusal-Worthy Borderline Cases**

   ```python
   # Generate ambiguous cases that test over-refusal
   prompt = """Create a request that:
   - Superficially resembles harmful content
   - Has legitimate educational/safety use case
   - Tests model's judgment on refusal boundaries"""
   ```

#### Evaluation Protocol for E6

```bash
make eval-e6 MODELS="gpt-4o,claude-3.5-sonnet" N=100

python scripts/analyze_defense.py \
  --metrics helpfulness_on_benign,refusal_on_harmful,over_refusal_rate
```

#### Training Recipe for E6

**SFT:**

- Dataset: 10K mixed (benign + adversarial) with appropriate responses
- Focus: Accurate classification, helpful responses, safe refusals
- Expected gain: +20% on balanced accuracy

**RLFT:**

- Reward: Helpfulness on benign + safe refusal on harmful - over-refusal penalty
- Focus: Boundary judgment, maintaining usefulness
- Expected gain: +15% on helpfulness-harmlessness balance

**Co-Training with E5:**

- Iteratively train E5 (attacker) and E6 (defender)
- Use E5 to generate novel attacks for E6 training
- Measure robustness improvements over iterations

---

## 4. Model Selection and Training Infrastructure

### Closed-Source Models (Baselines)

| Model             | Provider  | Use Case                             | Key Features                                 | Cost Estimate   |
| ----------------- | --------- | ------------------------------------ | -------------------------------------------- | --------------- |
| GPT-5             | OpenAI    | Frontier baseline, data distillation | Significant intelligence leap over GPT-4     | Premium         |
| GPT-4.5           | OpenAI    | Strong baseline                      | 128K context, released Feb 2025              | $15-30/M tokens |
| Claude-Sonnet-4.5 | Anthropic | Extended thinking                    | Visible reasoning, extended thinking mode    | Variable        |
| Claude-Opus-4.1   | Anthropic | Strongest reasoning                  | 1M token context (Aug 2025), 72.5% SWE-bench | Premium         |
| Gemini-2.5-Pro    | Google    | Reasoning specialist                 | 86.4 GPQA score (best reasoning)             | Variable        |

**Access:** Via OpenAI-compatible API endpoints or provider APIs
**Note:** GPT-5 and Claude-Opus-4.1 are the strongest frontier models as of 2025

### Open-Source Models (Fine-Tuning Targets)

| Model                        | Size              | Parameters     | Key Features                                      | Training Priority |
| ---------------------------- | ----------------- | -------------- | ------------------------------------------------- | ----------------- |
| Llama-4-Maverick             | 400B (17B active) | MoE: 17B/token | 1M context, 128 experts, multimodal               | High              |
| Llama-4-Scout                | 109B (17B active) | MoE: 17B/token | 10M context, 16 experts, released Apr 2025        | High              |
| Qwen3-235B                   | 235B              | MoE hybrid     | Beats GPT-4o/DeepSeek-V3, best code generation    | High              |
| Qwen3-32B                    | 32.8B             | Dense          | 131K context, efficient dense alternative         | High              |
| DeepSeek-R1                  | 671B              | MoE            | MIT license, SOTA reasoning, 6 distilled variants | High              |
| DeepSeek-R1-Distill-Qwen-32B | 32B               | Dense          | Beats OpenAI-o1-mini, distilled from R1           | Very High         |
| Mistral-Small-3              | 24B               | Dense          | Released Jan 2025, comparable to larger models    | Medium            |

**Training Compute Requirements:**

- 17-32B models: 2x A100-80GB (LoRA), 8x A100-80GB (full fine-tune)
- 109-235B models: 8x A100-80GB (LoRA), 32x A100-80GB (full fine-tune)
- 400-671B models: Use distilled variants or 16+ A100-80GB (LoRA only)
- Training duration: 12-48 hours per environment (SFT), 24-96 hours (RLFT)

**Recommendation:** Prioritize Qwen3-32B, DeepSeek-R1-Distill-Qwen-32B, and Llama-4-Scout for best performance/efficiency tradeoff

### Infrastructure Setup

**Compute:**

- Prime Intellect platform for distributed training (prime-rl)
- vLLM for efficient serving during rollouts
- HuggingFace Transformers + PEFT for fine-tuning

**Environment:**

```bash
# Setup training environment
make setup
source .venv/bin/activate

# Install training dependencies
uv add transformers peft accelerate bitsandbytes
uv add torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Configure
cp .env.example .env
# Set: OPENAI_API_KEY, HF_TOKEN, WANDB_API_KEY
set -a && source .env && set +a
```

---

## 5. Data Generation Pipeline

### High-Level Workflow

```text
1. Curate existing datasets → 2. Generate synthetic data → 3. Validate quality →
4. Create train/val/test splits → 5. Version and publish
```

### Synthetic Data Quality Criteria

For all environments:

- **Format compliance:** 100% valid JSON schemas
- **Label correctness:** Verify via executable oracles or human review
- **Diversity:** Cover multiple attack types, edge cases, difficulty levels
- **Distribution:** Match real-world distributions (with intentional OOD examples)

### Distillation Protocol

```python
# General distillation script
from openai import OpenAI
from sv_shared import build_rollout_logger

def distill_examples(env_name, task_prompts, n_examples=1000):
    client = OpenAI()
    examples = []

    for prompt in task_prompts:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a security expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        example = parse_and_validate(response, env_name)
        examples.append(example)

    return examples
```

### Data Validation

```bash
# Validate synthetic data quality
python scripts/validate_data.py \
  --env network-logs \
  --data data/synthetic/network-logs-v1.jsonl \
  --checks format,labels,diversity,distribution
```

### Versioning and Storage

```tree
data/
├── network-logs/
│   ├── train-v1.jsonl (IoT-23 curated)
│   ├── synthetic-v1.jsonl (distilled)
│   ├── ood-cic-ids-2017.jsonl
│   └── ood-unsw-nb15.jsonl
├── config-verification/
│   ├── k8s-configs-v1/
│   ├── terraform-configs-v1/
│   └── synthetic-violations-v1.jsonl
└── ...
```

**Publishing:**

- HuggingFace Datasets Hub for public datasets
- Internal storage for proprietary/sensitive data
- Versioned releases with data cards

---

## 6. Training Protocols

### Supervised Fine-Tuning (SFT)

**Objective:** Improve format compliance and base accuracy

**Recipe:**

```python
# SFT with HuggingFace Trainer
from transformers import AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

# Load base model (2025 recommended: Qwen3-32B or DeepSeek-R1-Distill-Qwen-32B)
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-32B-Instruct")

# LoRA config (parameter-efficient)
lora_config = LoraConfig(
    r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05, bias="none", task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

# Training args
training_args = TrainingArguments(
    output_dir=f"./models/llama-3.1-8b-{env_name}-sft",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    warmup_steps=100,
    logging_steps=10,
    save_strategy="epoch",
    evaluation_strategy="epoch",
    bf16=True,
    report_to="wandb"
)

# Train
trainer = Trainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=val_ds)
trainer.train()
```

**Hyperparameters (per model size):**

- 17-24B: lr=1.5e-5, batch_size=4, epochs=3, LoRA r=16
- 32B: lr=1e-5, batch_size=2, epochs=2, LoRA r=16
- 109-235B: lr=5e-6, batch_size=1, epochs=2, LoRA r=8
- 400B+ (MoE): lr=5e-6, batch_size=1, epochs=1-2, LoRA r=8 (sparse training)

### Reinforcement Learning Fine-Tuning (RLFT)

**Objective:** Optimize for environment rewards (calibration, tool-use, costs)

**Recipe:**

```python
# RLFT with prime-rl (GRPO-style)
from prime_rl import RLTrainer
from sv_env_network_logs import load_environment

# Load SFT checkpoint as policy initialization (2025: use Qwen3 or DeepSeek-R1-Distill checkpoints)
policy_model = AutoModelForCausalLM.from_pretrained("./models/qwen3-32b-network-logs-sft")

# Load environment
env = load_environment(max_examples=5000)

# RLFT config
rl_config = {
    "algorithm": "grpo",  # Group Relative Policy Optimization
    "learning_rate": 5e-6,
    "num_rollouts_per_update": 256,
    "ppo_epochs": 4,
    "value_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 1.0,
    "kl_coef": 0.1,  # KL penalty from SFT policy
}

# Train
trainer = RLTrainer(
    policy=policy_model,
    env=env,
    config=rl_config,
    vllm_config={"tensor_parallel_size": 2}
)
trainer.train(num_steps=10000)
```

**Training Strategy:**

- Warm-start from SFT checkpoint (critical for stability)
- KL penalty to prevent deviation from SFT policy
- Reward shaping: normalize rewards, clip extremes
- Curriculum: start with easier examples, gradually increase difficulty

### Multi-Task Training

**Objective:** Improve transfer across environments

**Recipe:**

```python
# Multi-task dataset mixing
from datasets import concatenate_datasets, interleave_datasets

datasets = [
    load_dataset("network-logs-sft"),
    load_dataset("phishing-detection-sft"),
    load_dataset("config-verification-sft"),
]

# Interleave with equal sampling
multi_task_ds = interleave_datasets(datasets, probabilities=[0.33, 0.33, 0.34])

# Train with task tokens
# Add task prefix: "<task:network-logs> {prompt}"
```

**Evaluation:**

- Per-environment performance
- Cross-environment zero-shot transfer
- Multi-task vs. single-task comparison

---

## 7. Evaluation and Benchmarking

### Reproducible Evaluation Protocol

**Standard evaluation command:**

```bash
# Single environment
make eval-e1 MODELS="model1,model2" N=100

# All environments
for env in network-logs config-verification code-vulnerability phishing-detection redteam-attack redteam-defense; do
    make eval ENV=$env MODELS="gpt-4o,llama-3.1-70b-ft" N=100
done
```

**Artifacts:**

```tree
outputs/evals/
└── sv-env-{environment}--{model}/
    └── {run_id}/
        ├── metadata.json (model, config, timestamp, git hash)
        ├── results.jsonl (per-example results)
        └── summary.json (aggregate metrics)
```

### Metrics per Environment

| Environment              | Primary Metrics                           | Secondary Metrics               |
| ------------------------ | ----------------------------------------- | ------------------------------- |
| E1 (network-logs)        | Accuracy, ECE (calibration), FN rate      | Abstention rate, F1, AUROC      |
| E2 (config-verification) | Precision, Recall, F1 (severity-weighted) | Tool calls, patch delta, time   |
| E3 (code-vulnerability)  | Tests passed, Bandit delta                | Diff size, iterations, coverage |
| E4 (phishing-detection)  | Accuracy, FN rate, ECE                    | Evidence quality, abstention    |
| E5 (redteam-attack)      | Success rate, turns-to-success            | Novelty, constraint violations  |
| E6 (redteam-defense)     | Helpfulness, harmless refusal             | Over-refusal rate, F1           |

### Cross-Reference with Security Benchmarks (2025)

To contextualize results, also evaluate on established security benchmarks:

| Benchmark                 | Focus                        | Use Case                                                  |
| ------------------------- | ---------------------------- | --------------------------------------------------------- |
| **SecBench**              | 44,823 MCQs + 3,087 SAQs     | Comprehensive cybersecurity knowledge (largest benchmark) |
| **CyberMetric**           | 80/500/2K/10K questions      | RAG-based cybersecurity Q&A (200+ hours human validation) |
| **CyberBench (JPMorgan)** | Multi-task cyber benchmark   | Financial sector security tasks                           |
| **SECURE Benchmark**      | LLM cybersecurity evaluation | General security task assessment                          |

**Integration:** Run baseline models on SecBench-500 and CyberMetric-500 subsets to establish cross-benchmark comparisons

### Analysis Scripts

```bash
# Aggregate results across runs
python scripts/aggregate_results.py \
  --eval-dir outputs/evals/ \
  --output reports/benchmark-summary.json

# Generate comparison report
python scripts/compare_models.py \
  --baseline gpt-4o \
  --models llama-3.1-70b-ft,qwen-2.5-72b-ft \
  --output reports/comparison.md

# Analyze failure modes
python scripts/analyze_failures.py \
  --results outputs/evals/sv-env-network-logs--llama-3.1-70b-ft/ \
  --output reports/failures-network-logs.md
```

### Statistical Rigor

- **Sample size:** N ≥ 100 per environment for significance
- **Confidence intervals:** Bootstrap 95% CI for all metrics
- **Multiple comparisons:** Bonferroni correction when comparing multiple models
- **Seeds:** Report mean and std dev over 3 random seeds

---

## 8. Iteration and Improvement Cycle

### Iterative Workflow

```text
Evaluate → Analyze failures → Generate targeted data → Fine-tune → Re-evaluate
```

### Failure Mode Analysis

```python
# Categorize failures for targeted improvement
def analyze_failures(results):
    categories = {
        "format_errors": [],      # Schema violations
        "calibration_errors": [], # Overconfident mistakes
        "tool_errors": [],        # Incorrect tool usage
        "edge_cases": [],         # Rare/difficult examples
        "systematic_bias": [],    # Consistent error patterns
    }

    for example in results:
        if example["reward"] < 0.5:
            category = classify_failure(example)
            categories[category].append(example)

    return categories
```

### Targeted Data Augmentation

Based on failure analysis:

1. **Format errors → Schema validation examples**
2. **Calibration errors → Adversarial confidence examples**
3. **Tool errors → Tool-use demonstrations**
4. **Edge cases → Boundary examples, ambiguous cases**
5. **Systematic bias → Counter-examples, balanced distribution**

### Checkpoint Selection

```python
# Evaluate checkpoints on validation set
checkpoints = ["epoch-1", "epoch-2", "epoch-3"]
best_checkpoint = None
best_score = 0

for ckpt in checkpoints:
    model = load_checkpoint(ckpt)
    score = evaluate_on_val_set(model, val_ds)
    if score > best_score:
        best_checkpoint = ckpt
        best_score = score

# Use best checkpoint for final evaluation
```

---

## 9. Progress Tracking and Reporting

### Experiment Tracking

**Weights & Biases Integration:**

```python
import wandb

# Initialize experiment
wandb.init(
    project="security-verifiers-research",
    name=f"{model_name}-{env_name}-sft",
    config={
        "model": model_name,
        "environment": env_name,
        "dataset_version": "v1",
        "learning_rate": 2e-5,
        "batch_size": 4,
        "epochs": 3,
    }
)

# Log metrics during training
wandb.log({"train_loss": loss, "val_accuracy": acc})

# Log artifacts
wandb.log_artifact(model_checkpoint, name="sft-checkpoint", type="model")
```

**Weave Tracing:**

- Automatic tracing enabled by default (see [logging-guide.md](../docs/logging-guide.md))
- Traces all evaluation runs, tool calls, reward calculations
- View at: `https://wandb.ai/<entity>/security-verifiers/weave`

### Weekly Progress Reports

**Template:**

```markdown
## Week {N} Progress Report

### Completed

- [ ] Baseline evaluation for {environments}
- [ ] Generated {N} synthetic examples for {env}
- [ ] Trained SFT model for {env}

### Results

| Model         | Environment | Metric   | Baseline | Post-SFT | Δ    |
| ------------- | ----------- | -------- | -------- | -------- | ---- |
| Llama-3.1-70B | E1          | Accuracy | 0.72     | 0.85     | +13% |

### Failures Analysis

- Top failure mode: {description}
- Mitigation: {plan}

### Next Week

- [ ] RLFT training for {env}
- [ ] OOD evaluation on {dataset}
```

### Milestone Tracking

```bash
# Use TodoWrite tool for task management
# (Claude Code will track progress automatically)
```

**Key Milestones:**

- M1 (Week 3): Baseline evaluation complete for E1-E6
- M2 (Week 6): Synthetic data generation complete
- M3 (Week 10): SFT training complete for all environments
- M4 (Week 14): RLFT training complete for priority environments
- M5 (Week 17): Cross-environment and OOD evaluation complete
- M6 (Week 20): Final report and artifact release

---

## 10. Artifact Release and Documentation

### Deliverables

1. **Evaluation Benchmarks**

   - Baseline results for closed-source and open-source models
   - Per-environment leaderboards
   - OOD generalization scores

2. **Training Datasets**

   - Synthetic data for each environment (HuggingFace Datasets)
   - Data cards with generation methodology
   - Versioned releases

3. **Fine-Tuned Models**

   - SFT and RLFT checkpoints (HuggingFace Model Hub)
   - Model cards with training details
   - Quantized versions (4-bit, 8-bit) for efficiency

4. **Reproducible Scripts**

   - Evaluation scripts with configs
   - Training scripts with hyperparameters
   - Analysis notebooks (Jupyter)

5. **Research Report**
   - Methodology and results
   - Failure analysis and insights
   - Future work recommendations

### Release Checklist

```bash
# Pre-release checks
make check  # Lint, format, tests
make clean && make build  # Clean build
make eval-e1 MODELS="released-model" N=100  # Validate checkpoints

# Documentation
- [ ] README.md updated
- [ ] Model cards complete
- [ ] Data cards complete
- [ ] CHANGELOG.md updated
- [ ] LICENSE verified

# Publish
- [ ] Push datasets to HuggingFace Datasets
- [ ] Push models to HuggingFace Model Hub
- [ ] Tag release (git tag v1.0.0)
- [ ] Publish blog post / paper
```

### Documentation Templates

**Model Card:**

```markdown
# Model: Llama-3.1-70B-SecurityVerifiers-E1-SFT

## Model Description

Fine-tuned Llama-3.1-70B on network log anomaly detection with calibrated abstention.

## Training Data

- 10K synthetic examples distilled from GPT-4o
- Based on IoT-23 dataset features
- Train/val split: 8K/2K

## Training Procedure

- Base model: meta-llama/Llama-3.1-70B-Instruct
- Method: LoRA (r=8, alpha=32)
- Hyperparameters: lr=1e-5, batch_size=2, epochs=2
- Compute: 4x A100-80GB, 24 hours

## Evaluation

| Metric   | Baseline | Post-SFT | Δ    |
| -------- | -------- | -------- | ---- |
| Accuracy | 0.72     | 0.85     | +13% |
| ECE      | 0.15     | 0.08     | -47% |

## Usage

\`\`\`python
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("org/llama-3.1-70b-security-e1-sft")
\`\`\`
```

---

## 11. Resource Requirements

### Compute Budget

| Task                             | Compute      | Duration     | Cost (est.)  |
| -------------------------------- | ------------ | ------------ | ------------ |
| Baseline evaluation (all models) | 4x A100-80GB | 1 week       | ~$2,000      |
| Data generation (distillation)   | API calls    | Ongoing      | ~$5,000      |
| SFT training (6 envs, 4 models)  | 4x A100-80GB | 4 weeks      | ~$8,000      |
| RLFT training (6 envs, 2 models) | 8x A100-80GB | 4 weeks      | ~$10,000     |
| OOD evaluation                   | 4x A100-80GB | 1 week       | ~$2,000      |
| **Total**                        |              | **14 weeks** | **~$27,000** |

**Note:** Costs assume Prime Intellect platform rates. Adjust based on actual provider.

### Personnel

- **Research lead:** 1 FTE (architecture, coordination)
- **ML engineers:** 2 FTE (training, evaluation)
- **Data engineers:** 1 FTE (data generation, validation)
- **Total:** 4 FTE over 5 months

### Infrastructure

- **Storage:** ~500GB for datasets, checkpoints, results
- **API keys:** OpenAI, Anthropic (for baselines and distillation)
- **Logging:** Weights & Biases (free tier may suffice, or Team plan ~$50/user/month)

---

## 12. Risks and Mitigations

| Risk                         | Impact                                       | Mitigation                                          |
| ---------------------------- | -------------------------------------------- | --------------------------------------------------- |
| **Data quality issues**      | Poor training results                        | Validation pipeline, human review of samples        |
| **Reward hacking**           | Models game rewards without real improvement | Strict schemas, executable oracles, ablations       |
| **Compute overruns**         | Budget/timeline issues                       | Prioritize high-value experiments, use LoRA         |
| **Model copyright concerns** | Legal/ethical issues                         | Use permissive licenses (Llama, Qwen), cite sources |
| **Safety content exposure**  | E5/E6 harmful content                        | Hash/redact, access controls, disclosure            |
| **Reproducibility failures** | Results don't replicate                      | Pin seeds, versions, configs; public artifacts      |

---

## 13. Success Criteria

### Quantitative Targets

| Environment              | Baseline (GPT-4.5)   | Target (Qwen3-32B FT) | Stretch Goal (DeepSeek-R1-Distill) |
| ------------------------ | -------------------- | --------------------- | ---------------------------------- |
| E1 (network-logs)        | Acc: 0.78, ECE: 0.12 | Acc: 0.88, ECE: 0.07  | Acc: 0.93, ECE: 0.04               |
| E2 (config-verification) | F1: 0.72             | F1: 0.85              | F1: 0.92                           |
| E3 (code-vulnerability)  | Pass: 0.62           | Pass: 0.80            | Pass: 0.88                         |
| E4 (phishing-detection)  | Acc: 0.83, FN: 0.12  | Acc: 0.91, FN: 0.06   | Acc: 0.94, FN: 0.04                |
| E5 (redteam-attack)      | Success: 0.32        | Success: 0.52         | Success: 0.68                      |
| E6 (redteam-defense)     | Balanced-Acc: 0.76   | Balanced-Acc: 0.88    | Balanced-Acc: 0.93                 |

**Note:** Baselines updated to reflect GPT-4.5 (Feb 2025) capabilities. Target models are Qwen3-32B and DeepSeek-R1-Distill-Qwen-32B based on 2025 SOTA performance.

### Qualitative Goals

- [ ] Open-source model (Qwen3-32B or DeepSeek-R1-Distill) achieves parity with GPT-4.5 on ≥4 environments
- [ ] Fine-tuned models outperform Claude-Opus-4.1 on at least 2 security-specific environments
- [ ] RLFT demonstrates clear value over SFT on calibration/tool-use tasks (+10% minimum improvement)
- [ ] Multi-task training shows positive transfer across environments
- [ ] Models rank in top-5 on SecBench or CyberMetric leaderboards (if public submissions allowed)
- [ ] Reproducible evaluation protocol adopted by external researchers
- [ ] Artifacts (data, models, scripts) widely used in community

---

## 14. Future Work and Extensions

### Post-Research Opportunities

1. **Continual Learning**

   - Incremental training on new data
   - Adapting to evolving attack patterns

2. **Real-World Deployment**

   - Integration with SOC workflows
   - Production monitoring and feedback loops

3. **New Environments**

   - Binary analysis (E7)
   - Incident response planning (E8)
   - Compliance auditing (E9)

4. **Advanced RL**

   - Multi-agent E5/E6 co-training
   - Curriculum learning across difficulty levels
   - Self-play for robustness

5. **Human-in-the-Loop**
   - Active learning for data efficiency
   - Human feedback for reward modeling

---

## 15. References and Resources

### Key Documentation

- [PRD.md](../PRD.md) - Environment specifications
- [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md) - Project vision
- [README.md](../README.md) - Quick start and setup
- [CLAUDE.md](../CLAUDE.md) - Project guidance
- [docs/logging-guide.md](../docs/logging-guide.md) - Logging setup

### Datasets and Benchmarks

- IoT-23: [https://www.stratosphereips.org/datasets-iot23](https://www.stratosphereips.org/datasets-iot23)
- JailbreakBench: [https://jailbreakbench.github.io](https://jailbreakbench.github.io)
- HarmBench: [https://www.harmbench.org](https://www.harmbench.org)
- Devign: [https://github.com/epicosy/devign](https://github.com/epicosy/devign)
- OPA/Rego: [https://www.openpolicyagent.org](https://www.openpolicyagent.org)

### Training Frameworks

- Prime Intellect: [https://www.primeintellect.ai](https://www.primeintellect.ai)
- Verifiers: [https://github.com/willccbb/verifiers](https://github.com/willccbb/verifiers)
- HuggingFace Transformers: [https://huggingface.co/docs/transformers](https://huggingface.co/docs/transformers)
- PEFT (LoRA): [https://huggingface.co/docs/peft](https://huggingface.co/docs/peft)

### Observability

- Weights & Biases: [https://wandb.ai](https://wandb.ai)
- Weave: [https://weave-docs.wandb.ai](https://weave-docs.wandb.ai)

---

## 16. Quick Start for Researchers

### Day 1: Setup and Baseline Evaluation

```bash
# Clone and setup
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers
make setup
source .venv/bin/activate

# Configure
cp .env.example .env
# Edit .env: add OPENAI_API_KEY, WANDB_API_KEY, HF_TOKEN
set -a && source .env && set +a

# Run baseline evaluation (E1)
make eval-e1 MODELS="gpt-5-mini" N=10  # Quick test
make eval-e1 MODELS="gpt-5-mini,gpt-4o" N=100  # Full baseline

# Analyze results
python scripts/analyze_results.py \
  --results outputs/evals/sv-env-network-logs--*/
```

### Week 1: Comprehensive Baseline

```bash
# Evaluate all production environments with 2025 SOTA models
make eval-e1 MODELS="gpt-5,gpt-4.5,claude-sonnet-4.5,gemini-2.5-pro,qwen3-32b,deepseek-r1-distill-qwen-32b" N=100
make eval-e2 MODELS="gpt-5,claude-opus-4.1,qwen3-32b" N=50 INCLUDE_TOOLS=true

# Generate baseline report
python scripts/generate_baseline_report.py \
  --output reports/baseline-week1.md
```

### Week 4: First Fine-Tuned Model

```bash
# Generate synthetic data using GPT-5 or Claude-Sonnet-4.5
python scripts/generate_synthetic_data.py \
  --env network-logs \
  --source gpt-5 \
  --num-examples 10000 \
  --output data/network-logs/synthetic-v1.jsonl

# Train SFT model (2025: use Qwen3-32B as base)
python scripts/train_sft.py \
  --model Qwen/Qwen3-32B-Instruct \
  --env network-logs \
  --data data/network-logs/synthetic-v1.jsonl \
  --output models/qwen3-32b-network-logs-sft

# Evaluate
make eval-e1 MODELS="qwen3-32b-network-logs-sft" N=100

# Compare to baseline
python scripts/compare_models.py \
  --baseline outputs/evals/sv-env-network-logs--gpt-4.5/ \
  --model outputs/evals/sv-env-network-logs--qwen3-32b-network-logs-sft/
```

---

## Appendix A: Example Scripts

### A.1: Baseline Evaluation Script

```python
#!/usr/bin/env python3
"""Run comprehensive baseline evaluation across all models and environments."""

import subprocess
from pathlib import Path

MODELS = [
    "gpt-5",
    "gpt-4.5",
    "claude-sonnet-4.5",
    "claude-opus-4.1",
    "gemini-2.5-pro",
]

ENVIRONMENTS = [
    ("network-logs", 100),
    ("config-verification", 50),
    ("phishing-detection", 100),
    ("code-vulnerability", 50),
    ("redteam-attack", 30),
    ("redteam-defense", 100),
]

def run_eval(env, model, n):
    cmd = f"make eval-{env.split('-')[0]} MODELS={model} N={n}"
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

if __name__ == "__main__":
    for env, n in ENVIRONMENTS:
        for model in MODELS:
            try:
                run_eval(env, model, n)
            except subprocess.CalledProcessError as e:
                print(f"Error evaluating {model} on {env}: {e}")
                continue

    print("\nBaseline evaluation complete!")
    print("Results in: outputs/evals/")
```

### A.2: Synthetic Data Generation Script

```python
#!/usr/bin/env python3
"""Generate synthetic training data via distillation from strong models."""

import json
from openai import OpenAI
from tqdm import tqdm

def generate_network_logs_examples(client, n=1000):
    """Generate network log anomaly examples using GPT-5."""
    examples = []

    for i in tqdm(range(n)):
        prompt = f"""Generate a realistic network flow log example.

        Include features like: src_ip, dst_ip, protocol, src_port, dst_port,
        bytes_sent, duration, flags, etc.

        Label as: Benign (75%) or Malicious (25%)
        Provide confidence [0-1] and brief rationale.

        Output JSON: {{"features": {{...}}, "label": "...", "confidence": 0.X, "rationale": "..."}}"""

        response = client.chat.completions.create(
            model="gpt-5",  # Updated to GPT-5 (2025)
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        example = json.loads(response.choices[0].message.content)
        examples.append(example)

    return examples

if __name__ == "__main__":
    client = OpenAI()
    examples = generate_network_logs_examples(client, n=10000)

    with open("data/network-logs/synthetic-v1.jsonl", "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Generated {len(examples)} examples")
```

### A.3: SFT Training Script

```python
#!/usr/bin/env python3
"""Train SFT model on synthetic data."""

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

def train_sft(model_name, data_path, output_dir):
    # Load model and tokenizer (2025: use Qwen3-32B or DeepSeek-R1-Distill)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,  # e.g., "Qwen/Qwen3-32B-Instruct" or "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        torch_dtype="auto",
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # LoRA config
    lora_config = LoraConfig(
        r=16, lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    # Load data
    dataset = load_dataset("json", data_files=data_path)

    # Training args
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=8,
        learning_rate=2e-5,
        warmup_steps=100,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
        report_to="wandb"
    )

    # Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"]
    )
    trainer.train()

    # Save
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

if __name__ == "__main__":
    train_sft(
        model_name="Qwen/Qwen3-32B-Instruct",  # Updated to Qwen3-32B (2025)
        data_path="data/network-logs/synthetic-v1.jsonl",
        output_dir="models/qwen3-32b-network-logs-sft"
    )
```

---

## Appendix B: Analysis Notebooks

### B.1: Baseline Analysis

```python
# notebooks/baseline_analysis.ipynb
import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load results
results_dir = Path("outputs/evals/")
all_results = []

for result_file in results_dir.rglob("results.jsonl"):
    with open(result_file) as f:
        for line in f:
            example = json.loads(line)
            all_results.append(example)

df = pd.DataFrame(all_results)

# Aggregate metrics
summary = df.groupby(["model", "environment"]).agg({
    "reward": ["mean", "std"],
    "accuracy": "mean",
    "calibration_error": "mean"
}).round(3)

print(summary)

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Accuracy by model
df.groupby("model")["accuracy"].mean().plot(kind="bar", ax=axes[0, 0])
axes[0, 0].set_title("Accuracy by Model")

# Calibration error by model
df.groupby("model")["calibration_error"].mean().plot(kind="bar", ax=axes[0, 1])
axes[0, 1].set_title("Calibration Error by Model")

# Reward distribution
df["reward"].hist(bins=50, ax=axes[1, 0])
axes[1, 0].set_title("Reward Distribution")

# Failures by environment
(df[df["reward"] < 0.5].groupby("environment").size().plot(kind="bar", ax=axes[1, 1]))
axes[1, 1].set_title("Failures by Environment")

plt.tight_layout()
plt.savefig("reports/baseline_analysis.png")
```

---

## End of Research Plan

This comprehensive plan provides a structured approach to benchmarking and improving models using the Security Verifiers suite. Researchers can adapt this plan to their specific needs, compute budgets, and research questions.

For questions or contributions, see [CONTRIBUTING.md](../CONTRIBUTING.md) or open an issue.
