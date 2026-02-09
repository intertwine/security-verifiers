# SOAR: Self-Optimization via Asymmetric RL for Security Curriculum Generation

**Paper:** [Teaching Models to Teach Themselves: Reasoning at the Edge of Learnability](https://arxiv.org/abs/2601.18778)
**Project:** https://ssundaram21.github.io/soar/
**Authors:** Sundaram, Quan, Kwiatkowski, Ahuja, Ollivier, Kempe (MIT, Meta FAIR, NYU)
**Date Reviewed:** 2026-02-09
**Status:** Future experiment candidate

---

## TL;DR

Standard RLVR stalls when initial success rates are near-zero. SOAR uses a bilevel meta-RL loop — a **teacher** LLM generates synthetic "stepping-stone" problems, a **student** trains on them, and the teacher is rewarded based on **measured student improvement** on real hard problems. On fail@128 math benchmarks (0% initial success), SOAR achieves **4x pass@1** and **2x pass@32** over direct hard-problem training.

**Key insight for SV-Bench:** Security tasks (especially E2 config remediation and future E3-E6) have very low initial pass rates on hard instances. SOAR's curriculum generation could bootstrap RL training where GRPO alone produces no learning signal.

---

## Core Insight

### The Cold-Start Problem in RLVR

Reinforcement Learning from Verifiable Rewards (RLVR) requires the model to occasionally succeed in order to receive gradient signal. When pass rates are near zero, the RL objective becomes degenerate:

```
J_RL = E[r(y|x) * log pi(y|x)]
```

If r(y|x) = 0 for all sampled y, then the gradient is zero and no learning occurs. This is the **cold-start problem** — the model needs to already partially solve a problem to learn from it.

Standard mitigations (more rollouts, curriculum from easy→hard) require either massive compute budgets or hand-curated difficulty progressions.

### SOAR's Key Question

> Can a pretrained LLM leverage **latent knowledge** to generate an automated stepping-stone curriculum for problems it cannot yet solve?

The answer is yes — and surprisingly, the generated problems don't even need correct answers. Only 32.8% of SOAR-generated stepping-stone problems have fully correct solutions, yet they produce significant learning gains. What matters is **structural quality and well-posedness** (63% are mathematically well-posed), not answer correctness.

---

## The SOAR Framework

### Architecture: Asymmetric Teacher-Student Meta-RL

Both teacher and student are initialized from the same pretrained model. The system operates in two nested loops:

```
┌─────────────────────────────────────────────────────┐
│  OUTER LOOP (Teacher Training via RLOO)             │
│                                                     │
│  Teacher generates g·n question-answer pairs        │
│  Partitioned into g datasets                        │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  INNER LOOP (Student Training via RLOO)     │    │
│  │                                             │    │
│  │  r parallel students train on each dataset  │    │
│  │  ~10 RL steps on teacher-generated QA pairs │    │
│  │  Standard RLVR with symbolic math checker   │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  Teacher reward = Δ(student performance on D_hard)  │
│  = avg_success_after - avg_success_before            │
│  Averaged across r parallel students for stability   │
└─────────────────────────────────────────────────────┘
```

### Bilevel Optimization Formulation

The problem is formally a bilevel optimization:

```
Outer:  max_θ_teacher  E[ R(θ_student*(D_teacher), D_hard) ]
Inner:  θ_student*(D) = argmin_θ  L_RLVR(θ; D_teacher)
```

Where:
- `θ_teacher` parameterizes the teacher policy (generates QA pairs)
- `θ_student*` is the result of training a fresh student on teacher-generated data
- `R(·, D_hard)` measures improvement on the real hard problem set
- `D_teacher` is the teacher-generated stepping-stone dataset

Directly differentiating through the inner loop (backprop through gradient descent) is intractable. SOAR avoids this by using **RLOO in both loops** — the outer loop treats each teacher-generated dataset as an "action" and uses the student's improvement as a scalar reward signal.

### Promotion Mechanism

SOAR uses a staged promotion system:
1. Teacher generates stepping stones for current difficulty level
2. Student trains and improves on those
3. If student passes a threshold on the hard set, "promote" — advance to harder problems
4. Teacher adapts: early-stage questions are word problems with basic formulas; later-stage questions shift to concise, equation-heavy algebra/calculus

This progressive difficulty scaling emerges naturally from the grounded reward signal.

### Grounded vs. Intrinsic Rewards

A critical design choice: the teacher's reward is **grounded** in actual student improvement on D_hard, not in intrinsic proxy metrics (novelty, diversity, difficulty estimates).

| Reward Type | Description | Outcome |
|-------------|-------------|---------|
| **Grounded** (SOAR) | Δ(student pass rate on D_hard) | Stable, diverse questions, reliable gains |
| **Intrinsic** | Self-assessed novelty/difficulty | High variance, diversity collapse, unstable |
| **None** (base teacher) | Use pretrained model directly | Weak, unguided generation |

Grounded rewards reliably avoid the instability and diversity collapse modes that intrinsic reward schemes exhibit. Intrinsic-trained teachers achieve higher answer correctness (55% vs 32.8%) but perform worse — they sacrifice diversity for surface-level quality.

---

## Empirical Results

### Setup

- **Model:** Llama-3.2-3B-Instruct
- **Benchmarks:** MATH, HARP, OlympiadBench (fail@128 subsets — 0/128 success)
- **Inner loop:** ~10 RLOO steps per student per dataset
- **Parallel students:** r students trained per dataset for reward stability
- **Teacher generates:** g·n QA pairs partitioned into g datasets

### Key Results

| Method | MATH pass@1 | MATH pass@32 | HARP pass@1 | HARP pass@32 |
|--------|-------------|--------------|-------------|--------------|
| Hard-Only (baseline) | 1x | 1x | 1x | 1x |
| Intrinsic-T | Mixed | Mixed | Mixed | Mixed |
| **SOAR (Grounded-T)** | **~4x** | **~2x** | **~2x** | **~4x** |

### Critical Findings

1. **Stepping stones unlock zero-signal settings:** Bilevel meta-RL produces learning where direct RLVR gives zero gradient.

2. **Structure > correctness:** Only 32.8% of generated problems have correct answers, yet 63% are well-posed. The structural and conceptual content provides sufficient signal.

3. **Transfer across benchmarks:** Problems generated for MATH also improve performance on HARP and OlympiadBench, suggesting general reasoning gains.

4. **Mixed > curriculum training on fail@128:** Training on teacher-generated problems mixed with real hard problems shows more stable dynamics than curriculum approaches (which spike then crash).

5. **Compute ablation:** Reallocating SOAR's compute budget to additional direct-training rollouts does not recover the same improvements. The bilevel structure provides qualitatively different signal.

---

## Relevance to Security Verifiers

### Why This Matters for SV-Bench

SOAR addresses a problem that directly maps to the security verification setting:

#### 1. Cold-Start on Hard Security Tasks

Security tasks have low initial pass rates, especially for smaller models:

| Environment | Task | Expected Initial Pass Rate | Cold-Start Risk |
|-------------|------|---------------------------|-----------------|
| **E1** | Network log classification | 30-60% (varies by difficulty) | Low-Medium |
| **E2** | Config audit + remediation | 5-20% (multi-turn tool use) | **High** |
| **E3** (WIP) | Vulnerability detection + fix | <10% (code reasoning) | **Very High** |
| **E5/E6** (WIP) | Red-team attack/defense | Near-zero (adversarial) | **Critical** |

E2's multi-turn config remediation — where the model must invoke tools (KubeLinter, Semgrep, OPA), interpret results, generate patches, and re-verify — has very low initial success rates with small models. E3-E6 will be even harder. SOAR could bootstrap training signal where direct GRPO produces no learning.

#### 2. Security "Stepping Stones" are a Natural Fit

Unlike math (where stepping stones are intermediate-difficulty problems), security has a natural difficulty progression:

- **E1 stepping stones:** Ambiguous-but-classifiable logs → noisy multi-protocol logs → adversarial evasion patterns
- **E2 stepping stones:** Single-tool single-violation configs → multi-tool configs → configs requiring patches → configs with subtle misconfigurations
- **E3 stepping stones:** Obvious buffer overflows → subtle type confusion → cross-function vulnerabilities

A teacher LLM could generate synthetic security scenarios at the right difficulty level. Crucially, the SOAR insight that **answer correctness is less important than structural quality** means the teacher doesn't need to be a security expert — it just needs to generate well-formed, structurally relevant examples.

#### 3. Executable Rewards Enable Grounded Signal

SOAR's key advantage over intrinsic-reward self-play is **grounded rewards** — the teacher is rewarded based on measured student improvement on real problems. SV-Bench's entire design philosophy is built on executable verification:

- **E1:** Binary classification checked against ground-truth labels
- **E2:** Tool outputs (KubeLinter, Semgrep, OPA) mechanically verify correctness
- **E3-E6:** Test suites, vulnerability scanners, and other deterministic checkers

This means SOAR's grounded reward loop integrates naturally with the existing reward infrastructure. The teacher generates security problems, the student trains, and improvement is measured via the same executable verifiers that already exist.

#### 4. Multi-Turn Tool Calling = Navigation

SOAR showed strong results on maze navigation (sequential decisions, binary success). E2's tool-calling workflow has the same structure:

```
Model → decide tool → interpret result → decide next tool → ... → generate patch → verify
```

Each step is a decision with delayed, sparse reward. Stepping-stone problems could teach partial skills (e.g., "interpret this KubeLinter output" or "fix this single violation") before composing them into full multi-turn episodes.

#### 5. Complementary to MaxRL

MaxRL (our other future experiment candidate) addresses a different aspect of the same problem:

| Aspect | MaxRL | SOAR |
|--------|-------|------|
| **Problem** | Underweighting hard problems during training | No signal at all on hard problems |
| **Solution** | Better gradient weighting (1/K normalization) | Generate learnable stepping stones |
| **When useful** | Pass rate > 0 but low | Pass rate = 0 (cold start) |
| **Mechanism** | Loss function change | Data/curriculum generation |
| **Compatibility** | Can use as inner-loop optimizer | Can use MaxRL in the inner loop |

**They are composable:** Use SOAR to bootstrap from zero to non-zero pass rates, then use MaxRL to efficiently train on the now-partially-solvable problems. This is a natural two-phase training strategy.

---

## Potential Experiment Design

### Research Question

Can a bilevel meta-RL curriculum (SOAR) bootstrap security verification training where direct RLVR fails due to cold-start, and does it compose with MaxRL for continued improvement?

### Proposed Experiment Matrix

| Phase | Variant | Method | Notes |
|-------|---------|--------|-------|
| 1 | A | GRPO baseline | Direct training on hard E2 problems (WP3) |
| 1 | B | SOAR (E1 stepping stones) | Teacher generates classification problems |
| 2 | C | SOAR (E2 stepping stones) | Teacher generates config audit problems |
| 2 | D | SOAR + MaxRL inner loop | Compose stepping stones with better weighting |
| 3 | E | SOAR cross-env transfer | Train on E1 stepping stones, evaluate on E2 |

### Concrete Instantiation for E1

**Why start with E1:** Single-turn, fast rollouts, existing reward functions, lower compute cost. Serves as proof-of-concept before tackling E2.

**Setup:**
1. Identify fail@K subset of E1: samples where model achieves 0/K success
2. Teacher generates synthetic network log classification problems:
   - Input: A system prompt describing the task + few-shot examples of the generation format
   - Output: Synthetic log entries + label + confidence
3. Student trains on teacher-generated logs using GRPO (inner loop, ~10 steps)
4. Teacher reward = Δ(student accuracy on fail@K subset)

**Key Metrics:**
1. **Cold-start escape rate:** % of fail@K problems where pass@1 > 0 after SOAR vs. after direct training
2. **Sample efficiency:** Steps to reach X% accuracy on hard subset
3. **Pass@K curves:** Does SOAR improve test-time scaling (pass@8, pass@16)?
4. **Calibration stability:** Does the stepping-stone curriculum help or hurt ECE?
5. **Transfer:** Do E1 stepping stones help on E1-OOD (CIC-IDS, UNSW-NB15)?

### Concrete Instantiation for E2

**Why E2 matters most:** Multi-turn tool calling with very low initial pass rates. This is the highest-impact setting.

**Setup:**
1. Identify fail@K subset: configs where model fails all K attempts at full audit+patch
2. Teacher generates synthetic config files with known violations:
   - Decompose into sub-skills: single-tool invocation, output interpretation, patch generation
   - Generate configs of controlled complexity (1 violation → 2 → 3 → multi-tool)
3. Student trains on teacher-generated configs (inner loop)
4. Teacher reward = Δ(student F1 + patch delta on fail@K configs)

**Key Metrics:**
1. **Cold-start escape:** Same as E1
2. **Sub-skill acquisition:** Can we measure which sub-skills the stepping stones teach?
3. **Tool economy:** Does SOAR produce more efficient tool usage than direct training?
4. **Severity-weighted F1:** Improvement stratified by violation severity

### Adaptation: Security-Specific Grounded Rewards

SOAR's original paper uses a binary math checker. Our rewards are richer:

| Component | E1 Reward | E2 Reward |
|-----------|-----------|-----------|
| Correctness | `reward_accuracy` (binary) | Severity-weighted F1 |
| Calibration | `reward_calibration` (1 - \|conf - correct\|) | Format validity |
| Cost | `reward_asymmetric_cost` (FN >> FP) | Patch delta (severity-weighted) |
| Format | JSON schema compliance | JSON schema compliance |

**Question:** Should the teacher's grounded reward use the full multi-component reward, or only the correctness component?

**Hypothesis:** Start with correctness-only for teacher grounding (simpler signal), then investigate multi-component grounding in Phase 2. The student should always train with the full rubric.

---

## Integration Path

### Phase 0: Infrastructure Prerequisites (Blocked on WP3)

SOAR requires a working RL training loop. This is currently blocked on WP3 (canonical GRPO runs).

**Prerequisites:**
- `train/run_train.py` exists and can do basic GRPO on E1/E2
- Inner-loop training can be invoked programmatically (not just via CLI)
- Reward functions can be called independently of full evaluation pipeline

### Phase 1: Cold-Start Analysis (Low Effort)

Before implementing SOAR, quantify the cold-start problem:

1. Run `make eval-e1` and `make eval-e2` with small open-weight models (Llama-3.2-3B, Qwen3-4B)
2. Compute fail@K subsets for K = 8, 16, 32, 64, 128
3. Characterize: what fraction of examples have zero pass rate? How does this vary by difficulty?
4. Document the cold-start gap: is it severe enough to warrant SOAR?

**Artifacts:**
- `research/experiments/soar/cold_start_analysis.py`
- `research/experiments/soar/results/cold_start_report.md`

### Phase 2: Teacher Prototype (Medium Effort)

Implement the teacher generation pipeline:

1. Design teacher prompts for E1 (network log generation) and E2 (config generation)
2. Generate synthetic stepping-stone datasets using the teacher
3. Validate: are generated problems structurally well-formed? Do tools (KubeLinter, etc.) produce valid outputs on generated configs?
4. Evaluate: does training on teacher-generated data improve performance on real data?

**Artifacts:**
- `research/experiments/soar/teacher_prompts/e1_network_log_teacher.txt`
- `research/experiments/soar/teacher_prompts/e2_config_audit_teacher.txt`
- `research/experiments/soar/generate_stepping_stones.py`
- `research/experiments/soar/validate_stepping_stones.py`

### Phase 3: Full Bilevel Loop (High Effort)

Implement the complete SOAR framework:

1. Inner loop: student GRPO/RLOO on teacher-generated data (~10 steps)
2. Outer loop: teacher RLOO with grounded reward (student improvement on D_hard)
3. Promotion mechanism: progressive difficulty advancement
4. Run full experiment matrix on E1 and E2

**Artifacts:**
- `research/experiments/soar/soar_trainer.py`
- `research/experiments/soar/configs/e1_soar.yaml`
- `research/experiments/soar/configs/e2_soar.yaml`
- `results/ablations/soar_vs_grpo/<date>/`

### Phase 4: Composition with MaxRL (Stretch)

1. Replace inner-loop GRPO with MaxRL estimator
2. Compare: SOAR+GRPO vs. SOAR+MaxRL
3. Test two-phase strategy: SOAR phase (cold-start → non-zero) then MaxRL phase (non-zero → high)

---

## Open Questions

1. **Security stepping-stone quality:** In math, structural well-posedness is sufficient. Do security stepping stones need more domain fidelity? E.g., will a teacher-generated K8s config with unrealistic fields still teach useful remediation skills?

2. **Tool interaction in generated data:** E2's value comes from tool grounding. If the teacher generates a config file, can we run KubeLinter/Semgrep/OPA on it to get real tool outputs? Or do we need the teacher to also generate plausible tool outputs?

3. **Multi-component reward grounding:** Should the teacher be grounded on full multi-component reward improvement, or only correctness? Multi-component grounding is richer but noisier.

4. **Compute budget:** SOAR requires training r parallel students per outer-loop step. With expensive E2 tool calls, this may be prohibitive. Can we reduce r while maintaining reward stability?

5. **Promotion criteria for security:** In math, "solving a problem" is binary. In security, rewards are graded (partial credit for detecting some violations). What promotion threshold is appropriate?

6. **Interaction with abstention:** E1 rewards abstention on uncertain inputs. Will SOAR's curriculum teach the model to abstain on hard problems (good) or to never abstain (bad)?

7. **Teacher model scale:** The paper uses the same model for teacher and student (Llama-3.2-3B). Would using a larger teacher (e.g., Qwen3-14B) with a small student (3-4B) work better in the security domain, where domain knowledge matters more?

8. **Synthetic data contamination:** If the teacher generates problems similar to the test set, we get inflated metrics. Need to ensure stepping stones are structurally distinct from held-out evaluation data.

---

## Comparison with Related Approaches

| Approach | Mechanism | Cold-Start? | Compute Cost | Security Fit |
|----------|-----------|-------------|--------------|--------------|
| **GRPO** (WP3 baseline) | Direct RL on hard problems | Fails | Low | Good if pass rate > 0 |
| **MaxRL** | Better gradient weighting | Fails at 0% | Low | Good for hard-but-solvable |
| **SOAR** | Meta-RL curriculum generation | **Solves** | High | Strong for E2-E6 |
| **SOAR + MaxRL** | Curriculum + efficient weighting | **Solves** | Medium-High | Optimal composition |
| **Manual curriculum** | Hand-curated easy→hard progression | Solves | Low (human time) | Labor-intensive, not scalable |
| **Synthetic data augmentation** | Generate training data without RL | Partial | Medium | No grounded feedback loop |

---

## References

- [SOAR Paper — Teaching Models to Teach Themselves](https://arxiv.org/abs/2601.18778)
- [SOAR Project Page](https://ssundaram21.github.io/soar/)
- [MaxRL Paper](https://arxiv.org/abs/2602.02710)
- [GRPO Paper](https://arxiv.org/abs/2402.03300)
- [GDPO (Decoupled Normalization)](https://nvlabs.github.io/GDPO/)
- [RLOO — REINFORCE Leave-One-Out](https://arxiv.org/abs/2402.14740)
- [Verifiers Framework (Prime Intellect)](https://github.com/PrimeIntellect/verifiers)

---

## Decision

**Recommendation:** Add to future experiment backlog as a **Phase 2 priority** — after WP3 (GRPO baselines) establishes the training infrastructure, and after cold-start analysis (Phase 1) confirms the severity of the problem on SV-Bench tasks.

SOAR is the strongest candidate we've identified for solving the cold-start problem that will likely emerge when training small models on E2 (and eventually E3-E6). It composes naturally with MaxRL (our other future experiment candidate), and its grounded-reward philosophy aligns perfectly with SV-Bench's executable-verification design.

**Priority:** High for E2+ environments (after WP3 infrastructure exists)
**Effort estimate:** Phase 1 (cold-start analysis) is low; Phase 2 (teacher prototype) is medium; Phase 3 (full bilevel loop) is high
**Dependency:** WP3 must be complete before Phase 2+
