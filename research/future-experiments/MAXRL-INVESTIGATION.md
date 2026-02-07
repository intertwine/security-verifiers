# MaxRL: Maximum Likelihood Reinforcement Learning

**Paper:** [Maximum Likelihood Reinforcement Learning](https://arxiv.org/abs/2602.02710)  
**Project:** https://zanette-labs.github.io/MaxRL/  
**Authors:** Tajwar, Zeng, Zhou, Song, Arora, Jiang, Schneider, Salakhutdinov, Feng, Zanette (CMU, Tsinghua, Zhejiang, Berkeley)  
**Date Reviewed:** 2026-02-07  
**Status:** Future experiment candidate

---

## TL;DR

Standard RL (REINFORCE, GRPO) optimizes **pass@1** — a first-order approximation of maximum likelihood. MaxRL optimizes a **harmonic mixture of pass@k** that converges to true ML as compute increases. The implementation change is trivially simple: normalize by successful samples K instead of total samples N.

**Results:** Pareto-dominates GRPO across all benchmarks with 7.9×–19.2× test-time scaling efficiency gains.

---

## Core Insight

### The Problem with Standard RL

For tasks with binary correctness (code, math, security checks), the model induces a success probability p(x) for each input. Two natural objectives:

| Objective | Formula | What it optimizes |
|-----------|---------|-------------------|
| **RL** | E[p(x)] | Pass@1 |
| **Maximum Likelihood** | E[log p(x)] | Log-likelihood of success |

The key observation: **RL is a linearization of ML**. When p is small (hard problems), RL underweights them. ML's log weighting gives hard problems proportionally more gradient signal.

### Maclaurin Expansion

The ML objective admits an elegant expansion:

```
J_ML(x) = log p = -Σ(k=1→∞) (1-p)^k / k = -Σ(k=1→∞) fail@k(x) / k
```

Differentiating:

```
∇J_ML = Σ(k=1→∞) (1/k) ∇pass@k
```

**ML optimizes a harmonic weighted sum of all pass@k terms.** Standard RL only optimizes the k=1 term.

### The MaxRL Objective

Truncate at level T:

```
J_MaxRL^(T) = -Σ(k=1→T) (1-p)^k / k
```

- T=1 → standard RL (pass@1)
- T→∞ → exact maximum likelihood

---

## The Beautifully Simple Estimator

### Theorem 1: Conditional Form

The ML gradient equals the average score function **over successful trajectories only**:

```
∇J_ML = E[∇log π(z|x) | success]
```

### Practical Estimator

Given N rollouts with K successes:

| Method | Estimator | Targets |
|--------|-----------|---------|
| **REINFORCE** | (1/N) Σ r_i S_i | ∇pass@1 |
| **MaxRL** | (1/K) Σ r_i S_i | Σ(1/k)∇pass@k for k=1..N |

**The only difference is dividing by K (successes) instead of N (total samples).**

### Theorem 2: Estimator-Objective Equivalence

Using N rollouts automatically targets the T=N truncated ML objective. No explicit pass@k estimation needed.

---

## Key Properties

### 1. Weight Function View

All objectives can be written as:
```
∇J = E[w(p) ∇p]
```

The weight function w(p) determines how much gradient signal goes to inputs of varying difficulty:

| Method | Weight w(p) | Behavior |
|--------|-------------|----------|
| RL | 1 | Uniform weighting |
| ML | 1/p | Strong upweighting of hard (low-p) inputs |
| GRPO | ~1/σ | Moderate upweighting, but also upweights easy inputs as p→1 |
| MaxRL(T) | Interpolates | Approaches ML as T→∞ |

**Critical:** MaxRL gives hard problems (low pass rate) proportionally more learning signal.

### 2. Scaling Behavior

- **REINFORCE:** Increasing N only reduces variance of fixed pass@1 objective
- **MaxRL:** Increasing N **improves the objective itself**, approaching ML

### 3. Variance Reduction

Use control variate V_N = (1/N)Σ S_i (unconditional average score, has E[V_N]=0). Subtract from estimator to reduce variance while preserving unbiasedness.

---

## Empirical Results

### Qwen3-4B Results

MaxRL Pareto-dominates GRPO:
- Similar or better Pass@1
- Significantly better Pass@K
- **7.9×–19.2× test-time scaling efficiency**

### Key Findings

1. **ImageNet (exact ML computable):** MaxRL converges to exact cross-entropy training as N increases
2. **Maze Navigation (infinite data):** MaxRL scales better with additional compute than GRPO/RLOO
3. **GSM8K (data-scarce):** MaxRL sustains improvement over more epochs
4. **Hard problems:** MaxRL particularly excels when initial pass rates are low

---

## Relevance to Security Verifiers

### Why This Matters for SV-Bench

1. **Low Initial Pass Rates**
   - Security tasks are hard — E2's config remediation often has <20% initial pass rate
   - MaxRL's upweighting of hard problems should help
   
2. **Multi-Turn Tool Calling = Navigation**
   - The paper shows strong results on maze navigation
   - E2's OPA/Semgrep tool workflows are structurally similar (sequential decisions, binary success)
   
3. **Expensive Rollouts**
   - E2 tool calls are slow/costly
   - MaxRL's better sample efficiency matters more when each rollout is expensive
   
4. **Test-Time Scaling**
   - Security ops often uses best-of-N sampling
   - MaxRL's Pass@K improvements translate to operational gains

### Potential Experiment Design

**Research Question:** Does MaxRL improve sample efficiency and final performance on security verification tasks compared to GRPO?

**Proposed Ablation (future WP):**

| Variant | Method | Notes |
|---------|--------|-------|
| A | GRPO (baseline) | Current WP3/WP4 baseline |
| B | MaxRL (T=N) | Simple estimator swap |
| C | MaxRL + GDPO | Combine with decoupled normalization |

**Key Metrics to Track:**

1. **Sample efficiency:** Steps to reach X% pass@1 on E1/E2
2. **Pass@K curves:** Does MaxRL improve pass@8, pass@16 more than pass@1?
3. **Hard-problem breakdown:** Performance stratified by initial difficulty
4. **Training stability:** Does the 1/K normalization introduce variance issues?

### Implementation Notes

The change is minimal:

```python
# GRPO-style
advantage = (reward - reward.mean()) / (reward.std() + eps)

# MaxRL-style  
mean_reward = reward.mean()  # = K/N
advantage = (reward - mean_reward) / (mean_reward + eps)  # normalize by K/N, not std
```

Or equivalently, in the gradient computation, divide by K (number of successes) instead of N (total samples).

---

## Integration Path

### Phase 1: Validation (Low Effort)

1. Implement MaxRL estimator as a trainer loss variant
2. Run on E1 (simpler, single-turn) to validate implementation
3. Compare learning curves: GRPO vs MaxRL

### Phase 2: Full Experiment (If Phase 1 Promising)

1. Add MaxRL to WP4 ablation matrix
2. Run on both E1 and E2
3. Track Pass@K metrics at multiple K values
4. Analyze by problem difficulty strata

### Phase 3: Research Contribution (Stretch)

1. Combine MaxRL + GDPO for multi-reward security tasks
2. Investigate whether MaxRL's hard-problem focus helps or hurts calibration
3. Write up as security-specific findings

---

## Open Questions

1. **Variance:** Does normalizing by K (which can be small) introduce high variance when pass rates are very low?

2. **Multi-Reward Interaction:** How does MaxRL interact with our multi-reward setup (correctness, calibration, cost)? The paper assumes single binary reward.

3. **Abstention:** Our E1 environment rewards abstention on uncertain inputs. Does MaxRL's hard-problem focus conflict with learning to abstain?

4. **Tool Economy:** E2 rewards efficient tool use. Is there a tension between "keep trying until success" (MaxRL) and "minimize tool calls" (tool economy reward)?

---

## References

- [MaxRL Paper](https://arxiv.org/abs/2602.02710)
- [Project Website](https://zanette-labs.github.io/MaxRL/)
- [GRPO Paper](https://arxiv.org/abs/2402.03300)
- [GDPO (Decoupled Normalization)](https://nvlabs.github.io/GDPO/)

---

## Decision

**Recommendation:** Add to future experiment backlog. Low implementation effort, high potential upside for sample efficiency on hard security tasks. Consider adding as Variant E to WP4 if time permits, or as a dedicated WP in Q2.

**Priority:** Medium-High (after WP3/WP4 GRPO baselines are established)
