# SDPO: Self-Distillation Policy Optimization for Security Verifiers

**Paper:** [Reinforcement Learning via Self-Distillation](https://arxiv.org/abs/2601.20802)
**Authors:** Gerstenberger et al. (lasgroup)
**Date Reviewed:** 2026-02-18
**Status:** Future experiment candidate

---

## TL;DR

SDPO formalizes **RL with Rich Feedback (RLRF)**, where environments return tokenized textual feedback (runtime errors, judge evaluations, linter outputs) instead of (or in addition to) scalar rewards. The current policy itself, conditioned on the feedback, acts as a "self-teacher." SDPO distills the teacher's feedback-informed next-token predictions back into the student policy via a logit-level KL loss, delivering **dense, per-token credit assignment** without any external reward model or teacher.

**Key wins vs. GRPO:**

- 4-6x sample efficiency / wall-clock speedup
- Higher final accuracy (e.g. +7.6% on LiveCodeBench v6)
- 3-11x shorter, more concise outputs
- Better retention on holdout tasks (less catastrophic forgetting)
- Works even in pure scalar-reward settings by treating successful rollouts as implicit feedback for failed ones
- **Test-time SDPO** achieves the same discovery probability on hard binary-reward tasks with **3x fewer attempts** than best-of-k or multi-turn

**Key insight for SV-Bench:** Our environments (E1-E6) are built on executable, verifiable rewards from real security tools (Semgrep, OPA, KubeLinter, network-log parsers) that naturally produce rich textual feedback. SDPO is a drop-in upgrade that turns this rich feedback into dense learning signals.

---

## Core Insight

### The Credit Assignment Bottleneck

Standard RLVR only sees a scalar outcome per full rollout, creating a severe credit-assignment bottleneck. Yet verifiable environments (code execution, security scanners, math judges) already emit rich tokenized feedback explaining *why* an attempt failed.

### The SDPO Algorithm

1. Sample G rollouts y ~ pi_theta(- | x) for question x
2. Obtain rich feedback f (or use successful y_success as implicit f for failures)
3. Self-teacher = pi_theta(- | x, f, y_<t) (same model, conditioned on feedback)
4. Minimize logit-level KL(pi_theta(- | x, y_<t) || stopgrad(teacher)) per token
5. Optional stabilizations: EMA teacher, trust-region constraint, top-K approximation for memory

### Loss Function

```
L_SDPO(theta) = sum_t KL( pi_theta(-|x,y_<t) || stopgrad(pi_theta(-|x,f,y_<t)) )
```

This is a pure logit-level policy gradient where the advantage at each token is implicitly the log-ratio of teacher vs. student probability.

### Test-Time Mode

For a single hard question, iteratively apply self-distillation using the accumulating feedback. This achieves the same discovery probability with **3x fewer attempts** than best-of-k or multi-turn.

---

## Key Results

| Setting | Metric | SDPO | GRPO (baseline) | Gain |
|---------|--------|------|-----------------|------|
| Scientific reasoning (no rich f) | Avg@16 accuracy (Chemistry) | 73.2% | 65.9% | +7.3% + 6x speedup |
| LiveCodeBench v6 (rich f) | Overall pass@1 accuracy | 48.8% | 41.2% | +7.6% + 4x fewer gens |
| Hard questions (pass@64 <0.03) | Discovery probability @2750 attempts | 53.2% | ~35-41% | 3x fewer attempts |
| Response length | Tokens per answer | ~1/11th | baseline | 11x shorter |
| Holdout tasks | Forgetting on IFEval/ArenaHard | Minimal | Noticeable | Better retention |

### Additional Findings

- Scales with model size (Qwen3-0.6B to 8B)
- Even sequence-level SDPO beats GRPO; logit-level is best
- Hybrid SDPO+GRPO helps weaker models

---

## Relevance to Security Verifiers

Our environments already provide exactly the "rich feedback" the paper assumes:

| Environment | Rich Feedback Available Today | SDPO Benefit |
|-------------|-------------------------------|--------------|
| E1: network-logs | Parser error messages, anomaly confidence scores, feature attributions | Dense credit to specific log-line reasoning |
| E2: config-verif | OPA/Semgrep/KubeLinter violation texts + line numbers | Per-token fixes for policy violations |
| E3: code-vuln | Scanner diff outputs, CWE explanations, patch suggestions | Self-correction of vuln repair steps |
| E4: phishing | Evidence extraction feedback, URL reputation details | Calibrated confidence + abstention |
| E5/E6: redteam | Simulation logs, exploit success/failure traces | Test-time SDPO for faster attack/defense discovery |

### Strategic Advantages

- **Executable + dense:** Keep our gold-standard verifiable rewards while adding token-level learning from tool outputs
- **Self-correction without external judges:** Perfect alignment with "no LLM-as-judge" philosophy
- **Concise reasoning:** Security reports and audit logs must be short and actionable -- SDPO naturally produces this
- **Test-time acceleration:** Red-team scenarios and complex config audits are "hard binary-reward" problems; 3x fewer rollouts = huge cost savings on Prime Lab
- **Reduced forgetting:** Critical when we want one model strong on both E1 anomaly detection *and* E2 config auditing

### Complementarity with MaxRL and SOAR

- **MaxRL:** MaxRL-style max-likelihood framing can be layered on top of SDPO's distillation loss
- **SOAR:** SOAR-style self-curricula can feed the hardest questions into test-time SDPO loops
- **Result:** A unified RL pipeline that is simultaneously maximum-likelihood, self-orchestrated, and self-distilled

---

## Integration Path

### Phase 1: Low Effort (Immediate)

1. Deploy existing environments to Prime Intellect Hub (already supported)
2. Swap GRPO trainer for SDPO ([paper repo](https://github.com/lasgroup/SDPO) -- built on verl, same stack Prime uses)
3. Add optional `rich_feedback` flag to `env.step()` that returns full tool stdout/stderr (already partially present in E2/E3)

### Phase 2: Medium-Term Experiments (WP3a/b Extension)

1. Run hosted RL proof-of-concept on E1 + E2 with SDPO vs. GRPO (target: 4x faster convergence to same accuracy)
2. Ablation: scalar-only vs. rich-feedback SDPO on E3 code-vuln
3. Test-time SDPO on red-team hard instances (E5/E6)
4. Measure forgetting on holdout security + general capabilities (IFEval-style)

### Phase 3: Longer-Term

1. Hybrid SDPO + multi-reward (WP4) for calibrated confidence + cost-aware penalties
2. Off-policy SDPO extensions (paper already sketches PPO-style clipping)
3. Publish SDPO baselines on SV-Bench v0.1 alongside MaxRL/SOAR results

### Code Sketch

```python
# In env.step after tool execution
feedback = tool_output.stdout + tool_output.stderr  # tokenized rich f
if success:
    implicit_f = "Previous attempt succeeded"  # for failed siblings
return reward, feedback, done
```

---

## Open Questions

1. **Model size threshold:** Performs best on strong base models (Qwen3-8B+); weaker models may need hybrid GRPO. What is the minimum model size for standalone SDPO on our tasks?

2. **Feedback quality variance:** Our tools already excel at informative feedback, but E4 phishing may need richer evidence prompts. How do we ensure feedback quality across all envs?

3. **Memory overhead:** Minor extra memory for teacher forward pass (mitigated by top-K). Is this problematic for Prime Lab hosted training?

4. **Asymmetric reward interaction:** How does SDPO interact with our cost-aware asymmetric rewards? Can we distill "don't over-alert" behavior at token level?

---

## References

- [SDPO Paper -- Reinforcement Learning via Self-Distillation](https://arxiv.org/abs/2601.20802)
- [SDPO Code (verl-based)](https://github.com/lasgroup/SDPO)
- [GRPO Paper](https://arxiv.org/abs/2402.03300)
- [Security Verifiers repo](https://github.com/intertwine/security-verifiers)
- [Prime Intellect Environments Hub & Lab docs](https://docs.primellect.ai)
- [MaxRL Investigation](MAXRL-INVESTIGATION.md)
- [SOAR Investigation](SOAR-INVESTIGATION.md)

---

## Decision

SDPO is a natural evolution for Security Verifiers. It preserves everything that makes our project unique (executable verifiable rewards, real security tools, no LLM judges) while unlocking the dense credit assignment and self-correction power that verifiable domains deserve. This positions Security Verifiers at the cutting edge of RLVR/RLRF research while delivering immediately usable gains for cybersecurity agent training.

**Recommendation:** Add to future experiment backlog. Low implementation effort (trainer swap + feedback flag), high potential upside for sample efficiency and output conciseness. Natural complement to both MaxRL (gradient weighting) and SOAR (curriculum generation).

**Proposed actions:**

1. Schedule hosted RL proof-of-concept on E1/E2 with SDPO (target: end of Feb 2026)
2. Open issue/PR to add `rich_feedback` support across all envs
3. Cross-reference with MaxRL and SOAR docs for unified RL playbook

**Priority:** Medium-High (after WP3/WP4 GRPO baselines are established)
**Dependency:** WP3 must be complete; SDPO repo must be publicly available
**Effort estimate:** Phase 1 is low (trainer swap); Phase 2 is medium (ablation experiments); Phase 3 is high (multi-reward integration)
