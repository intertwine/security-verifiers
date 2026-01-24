# E3 Code Vulnerability Environment: Productionization Plan

**Status:** WIP → Production-Ready
**Target Completion:** 4-6 weeks
**Last Updated:** 2025-11-06

## Executive Summary

This document unifies three separate research visions (RESEARCH-CODEX.md, RESEARCH-CLAUDE.md, RESEARCH-DROID.md) and outlines the concrete steps to bring the E3 code vulnerability environment from its current WIP state to production-ready status, matching the quality and completeness of E1 (network-logs) and E2 (config-verification).

**Current State:**
- ✅ Core ToolEnv implementation with sandboxed execution
- ✅ Two high-quality synthetic examples (SQL injection, unsafe YAML)
- ✅ Comprehensive test suite (100% passing)
- ✅ Tool infrastructure (`run_python_static_scan`, `run_patch_and_tests`)
- ✅ Reward function with multiple components
- ✅ Basic README documentation

**Missing for Production:**
- ❌ Real vulnerability dataset (currently only 2 synthetic examples)
- ❌ Data building infrastructure (`make data-e3`, `make data-e3-test`)
- ❌ Evaluation scripts (`scripts/eval_code_vulnerability.py`)
- ❌ HuggingFace dataset integration (gated access)
- ❌ Dataset validation scripts
- ❌ Evaluation report generation
- ❌ Makefile integration for common workflows
- ❌ Hub deployment validation

## 1. Vision Synthesis: Three Research Plans

### 1.1 Common Themes Across All Plans

All three research documents (Codex, Claude, Droid) converge on:

1. **Dataset Sources:**
   - **CVEFixes** (DetectVul/CVEFixes on HF): 211K Python statements, highest accuracy
   - **DiverseVul**: 60% label accuracy, 24% better than union of CVEfixes+BigVul+CrossVul
   - **BigVul**: C/C++ vulnerabilities, but only 25% label accuracy (use cautiously)
   - **Juliet Test Suite**: NIST SAST benchmark
   - **CodeXGLUE**: Defect detection tasks
   - **The Stack v2**: 67.5TB BigCode release for commit-level vulnerabilities

2. **Model Portfolio (2025 SOTA):**
   - Closed: GPT-5, GPT-4.5, Claude Sonnet 4.5, Claude Opus 4.1, Gemini 2.5 Pro
   - Open: Qwen3-32B/235B, DeepSeek-R1-Distill-Qwen-32B, Llama-4-Scout/Maverick
   - **Recommendation:** Prioritize Qwen3-32B and DeepSeek-R1-Distill for efficiency

3. **Training Approach:**
   - SFT on curated + synthetic vulnerability datasets
   - RLFT with executable test rewards + security validation
   - Curriculum learning: simple → complex vulnerabilities
   - Multi-task training across security environments

4. **Synthetic Data Generation:**
   - Mutation-based: Inject vulnerabilities into clean code
   - Test-driven: Generate failing tests that expose vulnerabilities
   - Distillation: Use GPT-5/Claude-Opus to generate patches
   - Property-based: Use hypothesis/fuzzing frameworks

5. **Evaluation Metrics:**
   - Test pass rate (primary)
   - Patch quality (diff similarity, minimal changes)
   - Security validation (Bandit/Semgrep deltas)
   - Explanation quality

### 1.2 Unified Research Recommendations

**Phase 1 (Weeks 1-4): Baseline Evaluation**
- Establish baselines for closed models (GPT-5, Claude Opus 4.1) and open models (Qwen3-32B)
- Run `make eval-e3 MODELS="gpt-5,qwen3-32b" N=100` after building infrastructure
- Track: test pass rate, patch success rate, security improvements, diff size

**Phase 2 (Weeks 5-8): Dataset Curation**
- Build production dataset from CVEFixes + DiverseVul (prioritize label accuracy)
- Generate synthetic vulnerabilities (10 CWE categories minimum)
- Create OOD test sets for cross-language generalization
- Validate with Pydantic schemas

**Phase 3 (Weeks 9-14): Training**
- SFT on curated dataset: expect +25% test pass improvement
- RLFT with executable rewards: expect +10% additional gain, -30% diff size
- Multi-task with E2 for transfer learning experiments

**Phase 4 (Weeks 15-20): Deployment & Iteration**
- Hub deployment with gated dataset access
- Continuous evaluation on OOD datasets
- Weekly progress reports with W&B/Weave integration

## 2. Current E3 Implementation Analysis

### 2.1 Strengths

**Architecture:**
```python
# sv_env_code_vulnerability.py structure
- CodeVulnerabilityParser: JSON schema enforcement
- reward_patch_and_test: 60% tests + 20% diff + 10% consistency + 10% explanation
- run_patch_and_tests: Sandboxed patch application with behavioral + security tests
- run_python_static_scan: Heuristic SAST (SQL injection, unsafe YAML, weak crypto)
- ToolEnv with 2 tools
```

**Sandbox Security:**
- Restricted imports (only yaml, json, re, math, datetime, typing)
- No eval/exec/open/compile/__import__
- Safe builtins only
- AST-based validation before execution

**Test Coverage:**
- SQL injection parameterization
- Unsafe YAML loading → safe_load
- Diff application validation
- Sandbox constraint enforcement
- Reward function correctness
- Format compliance

### 2.2 Gaps vs E1/E2 Production Standards

| Feature | E1 | E2 | E3 Current | E3 Needed |
|---------|----|----|------------|-----------|
| Real dataset | ✅ IoT-23 (1800) | ✅ K8s+TF (combined) | ❌ 2 synthetic | Build from CVEFixes |
| Data builder script | ✅ `build_e1_iot23.py` | ✅ `build_e2_k8s_tf.py` | ❌ None | `build_e3_vulnerabilities.py` |
| Test fixtures (CI) | ✅ ~30 examples | ✅ ~20 examples | ✅ 2 examples | Expand to ~20-30 |
| OOD datasets | ✅ CIC-IDS, UNSW | ✅ Multiple repos | ❌ None | Cross-language, CWE types |
| Eval script | ✅ `eval_network_logs.py` | ✅ `eval_config_verification.py` | ❌ None | `eval_code_vulnerability.py` |
| Report generation | ✅ `generate_e1_eval_report.py` | ✅ `generate_e2_eval_report.py` | ❌ None | `generate_e3_eval_report.py` |
| Makefile targets | ✅ `data-e1`, `eval-e1` | ✅ `data-e2`, `eval-e2` | ✅ `test-env E=code-vulnerability` | Add data/eval targets |
| HF integration | ✅ Gated private repo | ✅ Gated private repo | ❌ None | Create E3_HF_REPO |
| Validation script | ✅ `validate_splits_e1.py` | ✅ `validate_splits_e2.py` | ❌ None | `validate_splits_e3.py` |
| Metadata export | ✅ Flat schema | ✅ Flat schema | ❌ None | `export_metadata_flat.py` |
| Tool versioning | N/A | ✅ `ci/versions.txt` | ⚠️ Implicit | Pin Bandit/Semgrep if used |
| README completeness | ✅ Hub-ready | ✅ Hub-ready | ⚠️ Basic | Expand with examples |
| Early error detection | ✅ MAX_CONSECUTIVE_ERRORS | ✅ MAX_CONSECUTIVE_ERRORS | ❌ None | Add to eval script |

## 3. Productionization Roadmap

### Phase 1: Data Infrastructure (Week 1-2)

#### 3.1.1 Dataset Builder Script

Create `scripts/data/build_e3_vulnerabilities.py`:

```python
"""Build E3 code vulnerability dataset from CVEFixes and synthetic generation."""

Key features:
- Load CVEFixes from HuggingFace (DetectVul/CVEFixes)
- Filter for Python vulnerabilities with high confidence labels
- Extract: vulnerable_code, patched_code, test_spec, CWE mapping
- Generate synthetic vulnerabilities via mutation operators:
  * SQL injection (string concat → parameterized)
  * Command injection (os.system → subprocess with shell=False)
  * Path traversal (user input → sanitize)
  * Unsafe deserialization (pickle → json)
  * YAML unsafe loading (yaml.load → yaml.safe_load)
  * Weak crypto (random → secrets)
  * Hardcoded secrets (detect and require env vars)
  * XML external entities (etree → defusedxml)
  * LDAP injection
  * Insecure file permissions
- Create test specs with behavioral + security test cases
- Split: 70% train, 15% dev, 15% test
- Output: data/vulnerabilities-train-v1.jsonl, vulnerabilities-dev-v1.jsonl, vulnerabilities-test-v1.jsonl
- Modes: --mode full (N=500-1000), --mode test (N=20-30 for CI)
```

**Dataset Schema:**
```python
class VulnerabilityExample(BaseModel):
    """Pydantic model for vulnerability dataset entries."""
    id: str  # e.g., "cve-2023-12345-sql-injection"
    language: Literal["python"]  # Expand later: "javascript", "java", "go"
    cwe_id: Optional[str]  # e.g., "CWE-89"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    original_code: str
    patched_code: str
    expected_diff: str
    test_spec: TestSpec  # Behavioral + security tests
    explanation_keywords: List[str]
    metadata: Dict[str, Any]  # Source, dataset provenance
```

**CWE Coverage Target (Minimum 10):**
1. CWE-89: SQL Injection
2. CWE-78: OS Command Injection
3. CWE-22: Path Traversal
4. CWE-502: Insecure Deserialization
5. CWE-611: XML External Entities (XXE)
6. CWE-327: Weak Cryptography
7. CWE-798: Hardcoded Credentials
8. CWE-77: Command Injection (LDAP)
9. CWE-915: Unsafe YAML Deserialization
10. CWE-330: Weak Random Number Generation

#### 3.1.2 Test Fixtures for CI

Extend `data/` directory:
```
environments/sv-env-code-vulnerability/data/
├── vulnerabilities-train-v1.jsonl        (N=500-1000, not committed)
├── vulnerabilities-dev-v1.jsonl          (N=150-200, not committed)
├── vulnerabilities-test-v1.jsonl         (N=150-200, not committed)
├── test-fixtures-v1.jsonl                (N=20-30, committed for CI)
└── ood/
    ├── javascript-vulns-v1.jsonl         (Future: cross-language OOD)
    └── cwe-specific-v1.jsonl             (Future: per-CWE evaluation)
```

#### 3.1.3 Makefile Targets

Add to main Makefile:
```makefile
# E3 data building (production)
data-e3: venv
	@LIMIT=$${LIMIT:-1000}; \
	CVEFIXES_ID=$${CVEFIXES_ID:-DetectVul/CVEFixes}; \
	$(ECHO) "$(YELLOW)Building E3 vulnerability dataset (LIMIT=$$LIMIT)...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e3_vulnerabilities.py --limit $$LIMIT --hf-id "$$CVEFIXES_ID" --mode full
	@$(ECHO) "$(GREEN)✓ E3 vulnerability dataset built$(NC)"

# E3 test fixtures (CI)
data-e3-test: venv
	@$(ECHO) "$(YELLOW)Building E3 test fixtures for CI...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e3_vulnerabilities.py --mode test
	@$(ECHO) "$(GREEN)✓ E3 test fixtures built$(NC)"

# E3 validation
validate-e3-data: venv
	@$(ECHO) "$(YELLOW)Validating E3 vulnerability splits with Pydantic...$(NC)"
	@$(ACTIVATE) && uv run python scripts/data/validate_splits_e3.py \
		--dir environments/sv-env-code-vulnerability/data
	@$(ECHO) "$(GREEN)✓ E3 validation passed$(NC)"
```

### Phase 2: Evaluation Infrastructure (Week 2-3)

#### 3.2.1 Evaluation Script

Create `scripts/eval_code_vulnerability.py`:

```python
"""
Reproducible evaluation script for E3 code vulnerability environment.

Features:
- Multi-model evaluation (CSV input: "gpt-5,qwen3-32b,claude-opus-4.1")
- Early stopping (MAX_CONSECUTIVE_ERRORS)
- Tool usage tracking
- Per-CWE category breakdown
- Output to outputs/evals/sv-env-code-vulnerability--{model}/{run_id}/
- Metadata: model, dataset, timestamp, git hash, config
- Results: per-example JSONL with test pass, patch quality, security delta
- Summary: aggregate metrics (test pass rate, avg diff size, CWE coverage)

Metrics:
- tests_passed_rate: % examples where all tests pass
- patch_success_rate: % examples with successful patch application
- security_improvement: avg Bandit/Semgrep delta
- diff_size_avg: avg number of changed lines
- cwe_coverage: % CWE categories detected
- explanation_quality: keyword match score
"""

Usage:
  python scripts/eval_code_vulnerability.py \
    --models "gpt-5,qwen3-32b" \
    --num-examples 100 \
    --dataset "vulnerabilities-test-v1.jsonl" \
    --max-consecutive-errors 3 \
    --include-tools
```

#### 3.2.2 Report Generation

Create `scripts/generate_e3_eval_report.py`:

```python
"""
Generate comprehensive E3 evaluation report from results.

Aggregates:
- Per-model summary (test pass, patch success, security delta)
- Per-CWE breakdown (which vulnerability types are hardest?)
- Tool usage patterns (how often do models use static scan?)
- Diff size distribution (are patches minimal?)
- Error analysis (what causes test failures?)

Output formats:
- JSON: Structured metrics for automation
- Markdown: Human-readable report with tables
- CSV: Per-example results for analysis
"""

Usage:
  make report-code-vulnerability RUN_IDS="id1 id2"
  make report-code-vulnerability OUTPUT="e3-report-2025-11-06.json"
```

#### 3.2.3 Makefile Integration

```makefile
# E3 evaluation
eval-e3: venv
	@if [ -z "$(MODELS)" ]; then \
		$(ECHO) "$(RED)Error: Provide MODELS=\"gpt-5,qwen3-32b\"$(NC)"; \
		exit 1; \
	fi
	@N=$${N:-50}; \
	DATASET=$${DATASET:-vulnerabilities-test-v1.jsonl}; \
	MAX_ERRORS=$${MAX_CONSECUTIVE_ERRORS:-3}; \
	INCLUDE_TOOLS=$${INCLUDE_TOOLS:-true}; \
	$(ECHO) "$(YELLOW)Evaluating E3 (code-vulnerability) for models: $(MODELS) (N=$$N, dataset=$$DATASET)$(NC)"; \
	$(ACTIVATE) && set -a && source .env && set +a && \
	python scripts/eval_code_vulnerability.py --models "$(MODELS)" --num-examples $$N --dataset "$$DATASET" --max-consecutive-errors $$MAX_ERRORS --include-tools $$INCLUDE_TOOLS

# E3 report generation
report-code-vulnerability: venv
	@EVAL_DIR=$${EVAL_DIR:-outputs/evals}; \
	OUTPUT=$${OUTPUT}; \
	RUN_IDS=$${RUN_IDS}; \
	$(ECHO) "$(YELLOW)Generating E3 (code-vulnerability) evaluation report...$(NC)"; \
	if [ -n "$$RUN_IDS" ]; then \
		$(ECHO) "  Run IDs: $$RUN_IDS"; \
		if [ -n "$$OUTPUT" ]; then \
			$(ACTIVATE) && uv run python scripts/generate_e3_eval_report.py \
				--eval-dir "$$EVAL_DIR" --output "$$OUTPUT" --run-ids $$RUN_IDS --pretty; \
		else \
			$(ACTIVATE) && uv run python scripts/generate_e3_eval_report.py \
				--eval-dir "$$EVAL_DIR" --run-ids $$RUN_IDS --pretty; \
		fi; \
	else \
		$(ECHO) "  Analyzing all non-archived runs in $$EVAL_DIR"; \
		if [ -n "$$OUTPUT" ]; then \
			$(ACTIVATE) && uv run python scripts/generate_e3_eval_report.py \
				--eval-dir "$$EVAL_DIR" --output "$$OUTPUT" --pretty; \
		else \
			$(ACTIVATE) && uv run python scripts/generate_e3_eval_report.py \
				--eval-dir "$$EVAL_DIR" --pretty; \
		fi; \
	fi
	@$(ECHO) "$(GREEN)✓ Report generated$(NC)"
```

### Phase 3: HuggingFace Integration (Week 3-4)

#### 3.3.1 Multi-Tiered Dataset Loading

Update `sv_env_code_vulnerability.py`:

```python
def load_environment(
    dataset_name: str | None = None,
    dataset_source: Literal["auto", "local", "hub", "synthetic"] = "auto",
    max_examples: int | None = None,
    include_tools: bool = True,
    logger: RolloutLogger | None = None,
) -> vf.ToolEnv:
    """
    Load the vulnerability repair environment with flexible dataset sources.

    Dataset loading strategy:
    - auto: Try local → hub → synthetic (default)
    - local: Require local JSONL files in data/ directory
    - hub: Load from HuggingFace Hub (requires HF_TOKEN and E3_HF_REPO)
    - synthetic: Use builtin test fixtures

    Args:
        dataset_name: Specific dataset to load (e.g., "vulnerabilities-test-v1.jsonl")
        dataset_source: Loading strategy
        max_examples: Limit dataset size
        include_tools: Enable tool access
        logger: Optional rollout logger
    """
    dataset = load_vulnerability_dataset(
        name=dataset_name,
        source=dataset_source,
        max_examples=max_examples
    )
    # ... rest of environment setup
```

#### 3.3.2 HuggingFace Repository Setup

**Repository Structure:**
```
intertwine-ai/security-verifiers-e3 (PRIVATE, gated)
├── train/
│   └── vulnerabilities-train-v1.jsonl
├── dev/
│   └── vulnerabilities-dev-v1.jsonl
├── test/
│   └── vulnerabilities-test-v1.jsonl
├── README.md (gated access instructions)
└── dataset_card.md (metadata, CWE coverage, tool versions)

intertwine-ai/security-verifiers-e3-metadata (PUBLIC)
├── meta/
│   └── meta.jsonl (flat schema for Dataset Viewer)
└── README.md (public metadata, request access instructions)
```

**Gated Access README:**
```markdown
# Security Verifiers E3: Code Vulnerability Dataset

This dataset contains real-world inspired Python vulnerabilities for training and evaluating code repair models. Access is gated to prevent training contamination.

## Request Access

To request access, open an issue at:
https://github.com/intertwine/security-verifiers/issues

Include:
- Your name and affiliation
- Research purpose (evaluation only)
- HuggingFace username

## Dataset Statistics

- Total examples: 1000 (700 train, 150 dev, 150 test)
- CWE categories: 10+ (SQL injection, XSS, path traversal, etc.)
- Languages: Python (with future expansion planned)
- Test coverage: 100% (all examples have behavioral + security tests)

## Evaluation-Only License

This dataset is licensed for evaluation purposes only. See LICENSE for details.
```

#### 3.3.3 Metadata Export

Create `scripts/hf/export_e3_metadata_flat.py`:
```python
"""Export E3 metadata in flat schema for HuggingFace Dataset Viewer."""

Exports:
- Dataset size per split
- CWE coverage statistics
- Tool versions (if applicable)
- Example complexity distribution
- Vulnerability type breakdown
```

Add to Makefile:
```makefile
# E3 metadata export
hf-e3-meta: venv
	@$(ECHO) "$(YELLOW)Building E3 metadata (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e3 --out build/hf/e3/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E3 metadata built: build/hf/e3/meta.jsonl$(NC)"

hf-e3-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E3 metadata to PUBLIC repo: $$HF_ORG/security-verifiers-e3-metadata$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e3 --out build/hf/e3/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e3-metadata" --split meta --push
	@$(ECHO) "$(GREEN)✓ E3 metadata pushed to PUBLIC repo$(NC)"

hf-e3p-push-canonical: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E3 canonical splits to PRIVATE repo: $$HF_ORG/security-verifiers-e3$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e3 \
		--repo "$$HF_ORG/security-verifiers-e3" \
		--data-dir environments/sv-env-code-vulnerability/data \
		--push \
		--force
	@$(ECHO) "$(GREEN)✓ E3 canonical splits pushed$(NC)"
```

### Phase 4: Enhanced Vulnerability Coverage (Week 4-5)

#### 3.4.1 Expand Static Scanner

Enhance `run_python_static_scan`:

```python
def run_python_static_scan(code: str) -> Dict[str, Any]:
    """Enhanced SAST for Python snippets."""
    vulnerabilities: List[str] = []

    # Existing checks:
    # - SQL injection patterns
    # - Unsafe YAML loading
    # - Weak randomness

    # NEW checks:
    # - Command injection (os.system, subprocess with shell=True)
    # - Path traversal (os.path.join with user input)
    # - Pickle deserialization
    # - XML external entities (etree without defusedxml)
    # - Hardcoded secrets (regex patterns for API keys)
    # - Insecure file permissions (os.chmod with 0o777)
    # - LDAP injection
    # - Eval/exec usage
    # - Assert usage in production code
    # - Use of dangerous functions (input → eval chains)

    return {
        "language": "python",
        "vulnerabilities_found": len(vulnerabilities),
        "vulnerabilities": vulnerabilities,
        "cwe_mappings": [...],  # Map findings to CWE IDs
        "severity": "LOW|MEDIUM|HIGH|CRITICAL",
        "verdict": "Vulnerable" if vulnerabilities else "Secure",
    }
```

#### 3.4.2 Bandit/Semgrep Integration (Optional)

If enabling real security tools:

Create `environments/sv-env-code-vulnerability/ci/versions.txt`:
```
BANDIT_VERSION=1.7.5
SEMGREP_VERSION=1.45.0
```

Add tool installation to CI:
```bash
# .github/workflows/ci.yml
- name: Install E3 security tools
  run: |
    pip install bandit==1.7.5 semgrep==1.45.0
```

Create adapters:
```python
# environments/sv-env-code-vulnerability/adapters/bandit_adapter.py
def run_bandit(code: str) -> Dict[str, Any]:
    """Run Bandit SAST on Python code snippet."""
    # Write to temp file, run bandit, parse JSON output
    # Return normalized findings with CWE mappings

# environments/sv-env-code-vulnerability/adapters/semgrep_adapter.py
def run_semgrep(code: str, rules: str = "p/python") -> Dict[str, Any]:
    """Run Semgrep on Python code snippet."""
    # Write to temp file, run semgrep with rules, parse JSON
    # Return normalized findings
```

### Phase 5: Documentation & Hub Readiness (Week 5-6)

#### 3.5.1 README Enhancements

Expand `environments/sv-env-code-vulnerability/README.md`:

**Add sections:**
1. Dataset Access (gated HF instructions)
2. Dataset Loading Strategies (local/hub/synthetic examples)
3. Building Datasets (`make data-e3`, `make data-e3-test`)
4. Evaluation (`make eval-e3 MODELS="..." N=100`)
5. Report Generation (`make report-code-vulnerability`)
6. Performance Benchmarks (include baseline results)
7. CWE Coverage Table
8. Tool Versions (if using Bandit/Semgrep)
9. Early Stopping Configuration
10. Training Examples (SFT/RLFT code snippets)

#### 3.5.2 Hub Deployment Checklist

```bash
# 1. Validate environment
make hub-validate E=code-vulnerability

# 2. Build datasets
make data-e3

# 3. Run baseline evaluation
make eval-e3 MODELS="gpt-5-mini" N=50

# 4. Generate report
make report-code-vulnerability

# 5. Validate data
make validate-e3-data

# 6. Push to HF (optional, for users)
export HF_TOKEN=...
export E3_HF_REPO=your-org/security-verifiers-e3-private
make hf-e3p-push-canonical

# 7. Deploy to Hub
make hub-deploy E=code-vulnerability BUMP=minor
```

#### 3.5.3 CLAUDE.md Updates

Add E3 sections:
```markdown
## Quick commands (Makefile-backed)

# E3 commands
make data-e3              # Build E3 vulnerability dataset (LIMIT=1000, full mode)
make data-e3-test         # Build E3 test fixtures (~20-30 samples)
make eval-e3 MODELS="gpt-5,qwen3-32b" N=100  # Evaluate code vulnerability
make report-code-vulnerability RUN_IDS="id1"  # Generate E3 metrics report

# E3 dataset selection
make eval-e3 MODELS="gpt-5-mini" N=100 DATASET="vulnerabilities-test-v1.jsonl"
make eval-e3 MODELS="gpt-5-mini" N=2 DATASET="synthetic"  # Test fixtures

# E3 HuggingFace
make hf-e3-meta         # Build E3 metadata locally
make hf-e3-push         # Push E3 metadata to PUBLIC repo
make hf-e3p-push-canonical  # Push E3 canonical with Features (PRIVATE)
```

## 4. Dataset Specifications

### 4.1 Production Dataset Composition

**Target Size:** 1000 examples total (700 train, 150 dev, 150 test)

**Sources (Priority Order):**
1. **CVEFixes** (60%): Real-world Python vulnerabilities with high label accuracy
2. **DiverseVul** (20%): Supplement with validated examples
3. **Synthetic Generation** (20%): Mutation-based vulnerability injection

**CWE Distribution (Target):**
```
CWE-89  (SQL Injection):              15%
CWE-78  (OS Command Injection):       12%
CWE-22  (Path Traversal):             10%
CWE-502 (Insecure Deserialization):   10%
CWE-611 (XXE):                        8%
CWE-327 (Weak Crypto):                8%
CWE-798 (Hardcoded Credentials):      8%
CWE-77  (LDAP Injection):             7%
CWE-915 (Unsafe YAML):                7%
CWE-330 (Weak RNG):                   7%
Other CWEs:                           8%
```

**Difficulty Distribution:**
- Easy (single-line fix):              30%
- Medium (2-5 line fix):               50%
- Hard (multi-function refactor):      20%

### 4.2 Test Fixture Composition (CI)

**Size:** 20-30 examples (committed to repo)

**Coverage:**
- 2-3 examples per major CWE category
- Mix of difficulty levels
- All must pass tests within 2 seconds (fast CI)
- Include edge cases (empty input, malformed code, etc.)

## 5. Evaluation Metrics & Baselines

### 5.1 Primary Metrics

1. **Test Pass Rate** (60% weight)
   - % examples where all behavioral + security tests pass
   - Target: 70-80% for GPT-4o, 85-90% for GPT-5

2. **Patch Success Rate** (20% weight)
   - % examples where patch applies cleanly
   - Target: 90%+ (most models should apply patches correctly)

3. **Security Improvement** (10% weight)
   - Average reduction in Bandit/static scan findings
   - Target: 100% elimination of flagged vulnerability

4. **Diff Quality** (10% weight)
   - Average diff size (prefer minimal changes)
   - Similarity to reference patch
   - Target: <10 lines changed on average

### 5.2 Secondary Metrics

- **CWE Coverage:** % CWE categories correctly identified
- **Explanation Quality:** Keyword match with security concepts
- **Tool Usage:** % examples using `run_python_static_scan`
- **Error Rate:** API failures, malformed outputs

### 5.3 Expected Baselines (Projected)

| Model | Test Pass | Patch Success | Security Δ | Diff Size | Overall |
|-------|-----------|---------------|------------|-----------|---------|
| GPT-5-mini | 65% | 88% | 85% | 8 lines | 0.72 |
| GPT-5 | 82% | 94% | 95% | 6 lines | 0.85 |
| Claude Opus 4.1 | 85% | 96% | 98% | 5 lines | 0.88 |
| Qwen3-32B (base) | 45% | 72% | 60% | 12 lines | 0.52 |
| Qwen3-32B (SFT) | 70% | 89% | 85% | 8 lines | 0.76 |
| Qwen3-32B (RLFT) | 78% | 92% | 92% | 7 lines | 0.82 |

## 6. Implementation Timeline

### Week 1: Data Infrastructure
- [ ] Implement `scripts/data/build_e3_vulnerabilities.py`
- [ ] Create Pydantic schemas for validation
- [ ] Build test fixtures (N=20-30)
- [ ] Add Makefile targets: `data-e3`, `data-e3-test`
- [ ] Test dataset generation pipeline

### Week 2: Dataset Building
- [ ] Extract and validate CVEFixes Python examples
- [ ] Generate synthetic vulnerabilities (10 CWE types)
- [ ] Create test specs for all examples
- [ ] Build train/dev/test splits (70/15/15)
- [ ] Validate with `validate_splits_e3.py`

### Week 3: Evaluation Infrastructure
- [ ] Implement `scripts/eval_code_vulnerability.py`
- [ ] Add early stopping logic
- [ ] Create `scripts/generate_e3_eval_report.py`
- [ ] Add Makefile targets: `eval-e3`, `report-code-vulnerability`
- [ ] Run smoke tests on synthetic fixtures

### Week 4: Baseline Evaluation
- [ ] Run baselines: GPT-5-mini, GPT-4o, Claude Sonnet 4.5
- [ ] Generate first evaluation report
- [ ] Analyze failure modes
- [ ] Document baseline metrics in README

### Week 5: HuggingFace Integration
- [ ] Create HF repositories (public + private)
- [ ] Implement metadata export scripts
- [ ] Push datasets to HF with gated access
- [ ] Update environment loader for hub/local/synthetic
- [ ] Test multi-tiered loading

### Week 6: Documentation & Deployment
- [ ] Update README with all new features
- [ ] Add Hub deployment examples
- [ ] Update CLAUDE.md with E3 commands
- [ ] Run `make hub-validate E=code-vulnerability`
- [ ] Deploy to Prime Intellect Hub

## 7. Success Criteria

### Minimum Viable Production (MVP)
- ✅ Dataset: 500+ examples (train/dev/test splits)
- ✅ CWE Coverage: 10+ categories
- ✅ Evaluation: Working eval script with early stopping
- ✅ Reporting: Automated report generation
- ✅ Documentation: Hub-ready README
- ✅ Tests: 100% passing, including new dataset tests
- ✅ Makefile: `data-e3`, `eval-e3`, `report-code-vulnerability` targets

### Full Production (Target)
- ✅ Dataset: 1000+ examples
- ✅ CWE Coverage: 15+ categories
- ✅ HF Integration: Gated private repo + public metadata
- ✅ Multi-tiered loading: local/hub/synthetic
- ✅ Baseline results: 3+ models evaluated
- ✅ Hub deployment: Validated and deployed
- ✅ OOD datasets: Cross-language or CWE-specific test sets

### Research-Ready (Stretch)
- ✅ SFT dataset: Curated training examples with distillation
- ✅ RLFT experiments: Baseline → SFT → RLFT comparison
- ✅ Tool integration: Bandit/Semgrep adapters
- ✅ Multi-language: JavaScript or Java vulnerability examples

## 8. Risks & Mitigations

### 8.1 Dataset Quality Risks

**Risk:** Low-quality labels from public datasets (BigVul 25% accuracy)
**Mitigation:**
- Prioritize CVEFixes (highest accuracy) and DiverseVul (60% accuracy)
- Manual validation of 5% sample from each CWE category
- Pydantic schema validation to catch malformed examples
- Test execution to verify patches actually fix vulnerabilities

**Risk:** Synthetic data too simple, not representative
**Mitigation:**
- Mix 60% real-world (CVEFixes) + 40% synthetic
- Use mutation-based generation from real code
- Validate synthetic examples with static analysis tools
- Include complexity distribution in dataset metadata

### 8.2 Evaluation Risks

**Risk:** Models hack rewards without learning security
**Mitigation:**
- Executable test suite (can't fake passing tests)
- Security validation with static scanners
- OOD evaluation on unseen CWE categories
- Manual review of high-reward examples

**Risk:** Evaluation too slow, expensive
**Mitigation:**
- Test fixtures (N=20-30) for fast CI
- Early stopping after consecutive errors
- Batch evaluation with caching
- Start with small N (10-50) for iteration

### 8.3 Infrastructure Risks

**Risk:** Sandbox escapes in test execution
**Mitigation:**
- Restricted imports (only safe stdlib modules)
- No eval/exec/open/compile
- AST validation before execution
- Resource limits (timeout, memory cap)
- Regular security audits of sandbox code

**Risk:** HF dataset leakage to training data
**Mitigation:**
- Gated access with manual approval
- Clear "evaluation-only" license
- Monitor model benchmarks for suspiciously high scores
- Keep test split completely private (only on HF, not in repo)

## 9. Future Enhancements (Post-Production)

### 9.1 Multi-Language Support
- JavaScript (Node.js vulnerabilities)
- Java (Spring/Hibernate issues)
- Go (concurrency vulnerabilities)
- Rust (unsafe code patterns)

### 9.2 Advanced Vulnerability Types
- Multi-file vulnerabilities (cross-module issues)
- Race conditions and concurrency bugs
- Business logic vulnerabilities
- Supply chain vulnerabilities (dependency issues)

### 9.3 Enhanced Tooling
- Fuzzing integration (property-based testing)
- Symbolic execution (Angr, KLEE)
- Dynamic analysis (runtime behavior validation)
- Coverage-guided patch generation

### 9.4 Research Integration
- Active learning (select hardest examples for labeling)
- Curriculum learning (easy → hard vulnerability progression)
- Multi-task training (E2 config + E3 code = transfer learning)
- Attacker/defender co-training (generate new vulnerabilities)

## 10. References

### 10.1 Datasets
- [CVEFixes](https://huggingface.co/datasets/DetectVul/CVEFixes) - 211K Python statements, highest accuracy
- [DiverseVul](https://arxiv.org/abs/2304.00409) - 60% label accuracy, RAID 2023
- [BigVul](https://github.com/ZeoVan/MSR_20_Code_vulnerability_CSV_Dataset) - C/C++, 25% accuracy
- [Juliet Test Suite](https://samate.nist.gov/SARD/test-suites/112) - NIST SAST benchmark
- [CodeXGLUE](https://github.com/microsoft/CodeXGLUE) - Defect detection
- [The Stack v2](https://huggingface.co/datasets/bigcode/the-stack-v2) - 67.5TB code for commit analysis

### 10.2 Tools
- [Bandit](https://bandit.readthedocs.io/) - Python SAST
- [Semgrep](https://semgrep.dev/) - Lightweight static analysis
- [Verifiers Framework](https://github.com/willccbb/verifiers) - RL environments
- [Prime Intellect](https://www.primeintellect.ai/) - Distributed training

### 10.3 Research Plans
- [RESEARCH-CODEX.md](./RESEARCH-CODEX.md) - 24-week comprehensive plan
- [RESEARCH-CLAUDE.md](./RESEARCH-CLAUDE.md) - 20-week updated plan with 2025 models
- [RESEARCH-DROID.md](./RESEARCH-DROID.md) - 10-week focused plan
- [PRD.md](../PRD.md) - Original environment specification

## 11. Appendix: Code Templates

### 11.1 Dataset Loader Template

```python
# sv_shared/dataset_loader.py additions for E3

def load_vulnerability_dataset(
    name: str | None = None,
    source: Literal["auto", "local", "hub", "synthetic"] = "auto",
    max_examples: int | None = None,
) -> Dataset:
    """
    Load E3 vulnerability dataset with multi-tiered strategy.

    Loading priority (source="auto"):
    1. Local: data/vulnerabilities-{name}.jsonl
    2. Hub: E3_HF_REPO environment variable
    3. Synthetic: Builtin test fixtures
    """
    if source == "synthetic" or (source == "auto" and should_use_synthetic()):
        return load_synthetic_vulnerabilities(max_examples)

    if source == "local" or source == "auto":
        try:
            return load_local_vulnerabilities(name, max_examples)
        except FileNotFoundError:
            if source == "local":
                raise

    if source == "hub" or source == "auto":
        try:
            return load_hub_vulnerabilities(name, max_examples)
        except Exception:
            if source == "hub":
                raise

    # Final fallback
    logger.warning("All dataset sources failed, using synthetic")
    return load_synthetic_vulnerabilities(max_examples)
```

### 11.2 Evaluation Script Template

```python
# scripts/eval_code_vulnerability.py

def evaluate_code_vulnerability(
    models: List[str],
    num_examples: int,
    dataset: str = "vulnerabilities-test-v1.jsonl",
    max_consecutive_errors: int = 3,
    include_tools: bool = True,
) -> None:
    """Run E3 evaluation with early stopping."""

    for model in models:
        logger.info(f"Evaluating {model} on {dataset}")

        env = load_environment(
            dataset_name=dataset,
            max_examples=num_examples,
            include_tools=include_tools,
        )

        client = get_client(model)
        consecutive_errors = 0
        results = []

        for i, example in enumerate(env.dataset):
            try:
                result = env.run_episode(client, model, example)
                results.append(result)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error on example {i}: {e}")

                if max_consecutive_errors > 0 and consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Stopping early after {consecutive_errors} consecutive errors")
                    break

        # Save results
        save_evaluation_results(model, dataset, results)
```

### 11.3 Report Template

```python
# scripts/generate_e3_eval_report.py

def generate_e3_report(run_ids: List[str]) -> Dict[str, Any]:
    """Generate comprehensive E3 evaluation report."""

    report = {
        "summary": {
            "total_runs": len(run_ids),
            "total_examples": 0,
            "avg_test_pass_rate": 0.0,
            "avg_patch_success_rate": 0.0,
        },
        "per_model": {},
        "per_cwe": {},
        "failure_analysis": [],
    }

    for run_id in run_ids:
        results = load_results(run_id)

        # Aggregate metrics
        report["per_model"][results.model] = {
            "test_pass_rate": calculate_test_pass_rate(results),
            "patch_success_rate": calculate_patch_success_rate(results),
            "avg_diff_size": calculate_avg_diff_size(results),
            "cwe_coverage": calculate_cwe_coverage(results),
        }

        # Per-CWE breakdown
        for cwe_id, examples in group_by_cwe(results):
            report["per_cwe"][cwe_id] = {
                "examples": len(examples),
                "test_pass_rate": calculate_test_pass_rate(examples),
            }

    return report
```

---

**End of Plan Document**

This plan provides a complete roadmap for bringing E3 from WIP to production-ready status, unifying the research visions and leveraging the infrastructure patterns established by E1 and E2.
