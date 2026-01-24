# E4 (Phishing Detection) Productionization Plan

**Version:** 1.0
**Date:** 2025-11-06
**Status:** Planning Phase
**Target Completion:** Q1 2026

## Executive Summary

This document outlines the productionization plan for E4 (sv-env-phishing-detection), bringing it to the same production-ready status as E1 (network-logs) and E2 (config-verification). The plan synthesizes three complementary research visions (RESEARCH-CODEX, RESEARCH-CLAUDE, RESEARCH-DROID) and aligns them with the established patterns from E1/E2.

**Current State:** Alpha-quality SingleTurnEnv with basic evidence support and synthetic fallback dataset.

**Production Target:** Production-ready SingleTurnEnv with comprehensive dataset infrastructure, evaluation pipeline, and baseline benchmarks.

**Key Deliverables:**
1. Multi-source dataset pipeline with gated HuggingFace distribution
2. Reproducible evaluation infrastructure with metrics reporting
3. Comprehensive documentation (README, DATA_CARD, README-DEV)
4. Makefile integration matching E1/E2 patterns
5. Baseline benchmarks for 2025 SOTA models

---

## 1. Vision Synthesis

### 1.1 Unified Environment Vision

**Environment Type:** `SingleTurnEnv` (current implementation)
**Future Extension Path:** ToolEnv with verification tools (Phase 2, not in this plan)

**Task:** Calibrated phishing email classification with evidence-based reasoning and appropriate abstention.

**Key Characteristics (from unified research plans):**
- **Evidence-seeking classification:** Models must cite specific indicators (URLs, sender patterns, keywords)
- **Calibrated abstention:** Models should abstain when evidence is ambiguous
- **Asymmetric cost structure:** False negatives (missing phishing) are heavily penalized vs false positives
- **Cross-corpus generalization:** Train on public datasets, evaluate on corporate/multilingual OOD data

### 1.2 Alignment with Production Patterns

Following E1 and E2 precedents:

| Component | E1 Pattern | E2 Pattern | E4 Implementation |
|-----------|-----------|-----------|-------------------|
| **Dataset Loading** | Local → Hub → Synthetic | Local → Hub → Builtin | Local → Hub → Synthetic (12 examples) |
| **Data Building** | `build_e1_iot23.py`, `build_e1_ood.py` | `build_e2_k8s_tf.py` | `build_e4_phishing.py` (NEW) |
| **Evaluation** | `eval_network_logs.py` | `eval_config_verification.py` | `eval_phishing_detection.py` (NEW) |
| **Reporting** | `generate_e1_eval_report.py` | `generate_e2_eval_report.py` | `generate_e4_eval_report.py` (NEW) |
| **Makefile Targets** | `data-e1`, `eval-e1`, `report-network-logs` | `data-e2`, `eval-e2`, `report-config-verification` | `data-e4`, `eval-e4`, `report-phishing-detection` (NEW) |
| **HF Repos** | `intertwine-ai/security-verifiers-e1{,-metadata}` | `intertwine-ai/security-verifiers-e2{,-metadata}` | `intertwine-ai/security-verifiers-e4{,-metadata}` (NEW) |
| **Documentation** | README, README-DEV, DATA_CARD | README, README-DEV, DATA_CARD | Update existing README, add README-DEV, DATA_CARD |

---

## 2. Dataset Strategy

### 2.1 Dataset Sources (from Research Plans)

#### Primary Training Data
1. **zefang-liu/phishing-email-dataset** (HuggingFace)
   - 18.7k labeled emails (current target in code)
   - BERT-trained, compiled from multiple sources
   - Status: Already integrated in current implementation

2. **ealvaradob/phishing-dataset** (HuggingFace)
   - Alternative primary source
   - Compiled from multiple phishing corpora
   - Recommended by CODEX and CLAUDE plans

3. **pirocheto/phishing-url** (HuggingFace)
   - URL-focused phishing detection
   - Recommended by CODEX plan

#### Legitimate Email Corpus (Ham)
1. **Enron Email Corpus** (DROID plan)
   - Classic legitimate email dataset
   - Business communication baseline

2. **Modern business emails** (synthesized)
   - GitHub notifications
   - Slack invitations
   - Calendar reminders
   - Service receipts (Uber, etc.)
   - Current synthetic dataset has 7 good examples

#### Out-of-Distribution (OOD) Evaluation
1. **Corporate internal emails** (CODEX plan)
   - Red-team captured samples (sanitized)
   - Internal phishing simulation results

2. **Multilingual phishing** (CLAUDE plan)
   - Non-English phishing campaigns
   - Cross-domain evaluation

3. **Cybersecurity context** (CLAUDE plan)
   - `zeroshot/cybersecurity-corpus`
   - `ahmed000000000/cybersec`

### 2.2 Dataset Construction Pipeline

#### Production Dataset (make data-e4)
```bash
# Build E4 production phishing dataset
make data-e4 LIMIT=15000
```

**Implementation:** `scripts/data/build_e4_phishing.py`

**Components:**
1. Load and merge multiple phishing datasets
2. Extract and normalize email features (sender, subject, body, URLs)
3. Generate phishing indicators using heuristics:
   - URL extraction (regex pattern already in code)
   - Suspicious keyword detection (existing _SUSPICIOUS_KEYWORDS)
   - Sender spoofing patterns (existing _is_suspicious_sender)
   - Subject line urgency markers
4. Create train/dev/test splits (70/15/15)
5. Export to JSONL format:
   - `phishing-train-dev-test-v1.jsonl` (full dataset, ~15k examples)

**Schema (per example):**
```json
{
  "question": "From: security@amaz0n-account.com\nSubject: Urgent...\n\n[email body]",
  "answer": "Phishing|Legitimate|Abstain",
  "metadata": {
    "phishing_indicators": ["url1", "keyword", "sender-pattern"],
    "source_dataset": "zefang-liu/phishing-email-dataset",
    "language": "en",
    "phishing_type": "credential-harvest|invoice-fraud|...",
    "difficulty": "easy|medium|hard"
  }
}
```

#### OOD Datasets (make data-e4-ood)
```bash
# Build E4 OOD evaluation datasets
make data-e4-ood N=500
```

**Implementation:** `scripts/data/build_e4_ood.py`

**Outputs:**
- `corporate-emails-ood-v1.jsonl` (500 examples)
- `multilingual-phishing-ood-v1.jsonl` (500 examples)

#### Test Fixtures (make data-e4-test)
```bash
# Build E4 test fixtures for CI
make data-e4-test
```

**Output:** `phishing-train-dev-test-test.jsonl` (~20-30 examples, checked into repo)

### 2.3 Phishing Indicator Extraction Enhancement

**Current Implementation:** Basic extraction in `_extract_phishing_indicators()`

**Production Enhancements:**
1. **URL analysis:**
   - Extract all URLs (existing regex)
   - Detect URL shorteners (bit.ly, tinyurl, etc.)
   - Check for homoglyph domains (amaz0n vs amazon)
   - Identify suspicious TLDs (.tk, .ru, .xyz in suspicious context)

2. **Sender analysis:**
   - Current: Basic character hints and token matching
   - Enhanced: Email domain vs display name mismatch
   - Free email provider detection for business emails
   - Detect reply-to mismatches

3. **Content analysis:**
   - Urgency language (existing keywords)
   - Request for credentials/PII
   - Financial transaction urgency
   - Spelling/grammar errors (typosquatting)

4. **Metadata preservation:**
   - Difficulty scoring (easy/medium/hard based on indicator clarity)
   - Phishing taxonomy (credential-harvest, invoice-fraud, CEO-fraud, etc.)
   - Source attribution (which dataset)

### 2.4 HuggingFace Distribution Strategy

Following E1/E2 gated dataset pattern:

#### Public Metadata Repository
**Repo:** `intertwine-ai/security-verifiers-e4-metadata`
- Flat schema with sampling information
- Dataset composition statistics
- Model cards explaining privacy rationale
- No actual email content (prevent contamination)

**Push command:**
```bash
make hf-e4-push HF_ORG=intertwine-ai
```

#### Private Full Dataset Repository
**Repo:** `intertwine-ai/security-verifiers-e4`
- Gated access (manual approval required)
- Full dataset with splits (train/dev/test)
- Canonical schema with Features
- Access via HF_TOKEN + E4_HF_REPO env vars

**Push command:**
```bash
make hf-e4p-push-canonical HF_ORG=intertwine-ai
```

#### Dataset Card Template
```markdown
# Security Verifiers E4: Phishing Email Detection

## Dataset Description
- **Curated by:** Intertwine AI
- **Language:** English (primary), multilingual (OOD)
- **License:** Evaluation-only (see DATASET_EVAL_ONLY_LICENSE.md)
- **Size:** ~15k training examples, 500 OOD examples

## Source Datasets
- zefang-liu/phishing-email-dataset (18.7k emails)
- ealvaradob/phishing-dataset
- Enron Email Corpus (ham samples)
- Synthetic business emails

## Privacy & Contamination Prevention
This dataset is gated to prevent LLM training contamination...
```

---

## 3. Evaluation Infrastructure

### 3.1 Evaluation Script

**File:** `scripts/eval_phishing_detection.py`

**Pattern:** Mirror `eval_network_logs.py` (E1 pattern)

**Key Features:**
1. Model routing via `model_router.py` (OpenAI + OpenRouter)
2. Multi-model batch evaluation
3. Dataset selection (local JSONL files)
4. Early stopping via `MAX_CONSECUTIVE_ERRORS`
5. Weave auto-tracing integration
6. Metadata export (run_id, timestamp, git hash)
7. Per-example results.jsonl
8. Summary metrics computation

**Usage:**
```bash
# Via Makefile
make eval-e4 MODELS="gpt-5-mini,qwen3-32b" N=100 DATASET="phishing-train-dev-test-v1.jsonl"

# Direct script
uv run python scripts/eval_phishing_detection.py \
  --models "gpt-5-mini,claude-sonnet-4.5" \
  --num-examples 100 \
  --dataset "phishing-train-dev-test-v1.jsonl" \
  --max-consecutive-errors 3
```

**Output Structure:**
```
outputs/evals/sv-env-phishing-detection--gpt-5-mini/{run_id}/
├── metadata.json
├── results.jsonl
└── summary.json
```

### 3.2 Metrics Reporting

**File:** `scripts/generate_e4_eval_report.py`

**Pattern:** Mirror `generate_e1_eval_report.py`

**Key Metrics (from research plans):**
1. **Accuracy:** Overall classification correctness
2. **False Negative Rate (FNR):** % of phishing emails missed (critical metric)
3. **False Positive Rate (FPR):** % of legitimate emails flagged as phishing
4. **Abstention Rate:** % of examples where model abstained
5. **Expected Calibration Error (ECE):** Calibration quality
6. **Evidence Precision:** % of cited evidence that matches known indicators
7. **Cost-Weighted Reward:** Asymmetric cost function performance

**Additional Metrics:**
- Confusion matrix (Phishing/Legitimate/Abstain)
- Per-phishing-type accuracy (credential-harvest, invoice-fraud, etc.)
- Difficulty stratification (easy/medium/hard)
- Evidence citation rate (% examples with evidence)

**Report Format (JSON + Pretty Print):**
```json
{
  "run_id": "20250106_143022_gpt-5-mini",
  "model": "gpt-5-mini",
  "dataset": "phishing-train-dev-test-v1.jsonl",
  "num_examples": 1500,
  "timestamp": "2025-01-06T14:30:22Z",
  "metrics": {
    "accuracy": 0.87,
    "false_negative_rate": 0.05,
    "false_positive_rate": 0.08,
    "abstention_rate": 0.12,
    "expected_calibration_error": 0.09,
    "evidence_precision": 0.76,
    "mean_reward": 0.84,
    "cost_weighted_reward": 0.81
  },
  "breakdown": {
    "by_type": {...},
    "by_difficulty": {...},
    "confusion_matrix": [...]
  }
}
```

**Usage:**
```bash
# Generate report for specific run IDs
make report-phishing-detection RUN_IDS="run1 run2"

# Generate report for all non-archived runs
make report-phishing-detection

# Custom output path
make report-phishing-detection OUTPUT="reports/e4-benchmark-2025.json"
```

### 3.3 Makefile Integration

**New Targets:**

```makefile
# Data building (production - private, not committed)
data-e4: venv
	@LIMIT=$${LIMIT:-15000}; \
	$(ECHO) "$(YELLOW)Building E4 phishing dataset (LIMIT=$$LIMIT)...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e4_phishing.py --limit $$LIMIT --mode full
	@$(ECHO) "$(GREEN)✓ E4 phishing dataset built$(NC)"

data-e4-ood: venv
	@N=$${N:-500}; \
	$(ECHO) "$(YELLOW)Building E4 OOD datasets (N=$$N)...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e4_ood.py --n $$N --mode full
	@$(ECHO) "$(GREEN)✓ E4 OOD datasets built$(NC)"

# Test fixtures (small, checked in for CI)
data-e4-test: venv
	@$(ECHO) "$(YELLOW)Building E4 test fixtures for CI...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e4_phishing.py --mode test
	@$(ECHO) "$(GREEN)✓ E4 test fixtures built$(NC)"

# Evaluation
eval-e4: venv
	@if [ -z "$(MODELS)" ]; then \
		$(ECHO) "$(RED)Error: Provide MODELS=\"gpt-5-mini,qwen3-32b\"$(NC)"; \
		exit 1; \
	fi
	@N=$${N:-100}; \
	DATASET=$${DATASET:-phishing-train-dev-test-v1.jsonl}; \
	MAX_ERRORS=$${MAX_CONSECUTIVE_ERRORS:-3}; \
	$(ECHO) "$(YELLOW)Evaluating E4 (phishing-detection) for models: $(MODELS) (N=$$N, dataset=$$DATASET, max_errors=$$MAX_ERRORS)$(NC)"; \
	$(ACTIVATE) && set -a && source .env && set +a && \
	python scripts/eval_phishing_detection.py --models "$(MODELS)" --num-examples $$N --dataset "$$DATASET" --max-consecutive-errors $$MAX_ERRORS

# Generate E4 evaluation report
report-phishing-detection: venv
	@EVAL_DIR=$${EVAL_DIR:-outputs/evals}; \
	OUTPUT=$${OUTPUT}; \
	RUN_IDS=$${RUN_IDS}; \
	$(ECHO) "$(YELLOW)Generating E4 (phishing-detection) evaluation report...$(NC)"; \
	if [ -n "$$RUN_IDS" ]; then \
		$(ECHO) "  Run IDs: $$RUN_IDS"; \
		if [ -n "$$OUTPUT" ]; then \
			$(ACTIVATE) && uv run python scripts/generate_e4_eval_report.py \
				--eval-dir "$$EVAL_DIR" --output "$$OUTPUT" --run-ids $$RUN_IDS --pretty; \
		else \
			$(ACTIVATE) && uv run python scripts/generate_e4_eval_report.py \
				--eval-dir "$$EVAL_DIR" --run-ids $$RUN_IDS --pretty; \
		fi; \
	else \
		$(ECHO) "  Analyzing all non-archived runs in $$EVAL_DIR"; \
		if [ -n "$$OUTPUT" ]; then \
			$(ACTIVATE) && uv run python scripts/generate_e4_eval_report.py \
				--eval-dir "$$EVAL_DIR" --output "$$OUTPUT" --pretty; \
		else \
			$(ACTIVATE) && uv run python scripts/generate_e4_eval_report.py \
				--eval-dir "$$EVAL_DIR" --pretty; \
		fi; \
	fi
	@$(ECHO) "$(GREEN)✓ Report generated$(NC)"

# HuggingFace metadata push (PUBLIC repo)
hf-e4-meta: venv
	@$(ECHO) "$(YELLOW)Building E4 metadata (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e4 --out build/hf/e4/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E4 metadata built: build/hf/e4/meta.jsonl$(NC)"

hf-e4-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E4 metadata to PUBLIC repo: $$HF_ORG/security-verifiers-e4-metadata$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e4 --out build/hf/e4/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e4-metadata" --split meta --push
	@$(ECHO) "$(GREEN)✓ E4 metadata pushed to PUBLIC repo$(NC)"

# HuggingFace canonical push (PRIVATE repo)
hf-e4p-push-canonical: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E4 canonical splits to PRIVATE repo: $$HF_ORG/security-verifiers-e4$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e4 \
		--repo "$$HF_ORG/security-verifiers-e4" \
		--data-dir environments/sv-env-phishing-detection/data \
		--push \
		--force || ($(ECHO) "$(RED)✗ E4 canonical push failed$(NC)" && exit 1)
	@$(ECHO) "$(GREEN)✓ E4 canonical splits pushed$(NC)"

# Validation
validate-e4-data: venv
	@$(ECHO) "$(YELLOW)Validating E4 canonical splits with Pydantic...$(NC)"
	@$(ACTIVATE) && uv run python scripts/data/validate_splits_e4.py \
		--dir environments/sv-env-phishing-detection/data
	@$(ECHO) "$(GREEN)✓ E4 validation passed$(NC)"
```

**Update data-all, data-test-all, validate-data, hf-push-all targets to include E4.**

---

## 4. Code Enhancements

### 4.1 Current Implementation Analysis

**Strengths:**
- ✅ Clean SingleTurnEnv architecture
- ✅ Evidence list schema with parser support
- ✅ Asymmetric cost reward (penalizes FN > FP)
- ✅ Evidence alignment reward (matches indicators)
- ✅ Calibration and format rewards
- ✅ Robust fallback to synthetic dataset
- ✅ Basic phishing indicator extraction

**Gaps vs Production Standards:**
- ❌ No multi-source dataset loading (local/hub/synthetic tiers)
- ❌ No dataset_source parameter
- ❌ No HF_TOKEN + E4_HF_REPO integration
- ❌ No data/ directory with test fixtures
- ❌ No DATA_CARD.md or README-DEV.md
- ❌ Limited phishing indicator extraction
- ❌ No difficulty scoring in metadata
- ❌ No phishing type taxonomy

### 4.2 Required Code Changes

#### File: `environments/sv-env-phishing-detection/sv_env_phishing_detection.py`

**Changes:**

1. **Add multi-tiered dataset loading:**
```python
def load_environment(
    dataset_name: str = "phishing-train-dev-test-v1.jsonl",
    dataset_source: str = "auto",  # NEW: auto|local|hub|synthetic
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
) -> vf.SingleTurnEnv:
    """Load the Phishing Email Detection environment.

    Args:
        dataset_name: Local JSONL filename or HF dataset identifier
        dataset_source: Loading strategy - "auto" (local→hub→synthetic),
                       "local" (require local file), "hub" (HF only),
                       "synthetic" (builtin fixtures)
        max_examples: Maximum examples to load
        logger: Optional rollout logger
    """
    # Implementation similar to E1's load_environment
    # Try local → hub → synthetic based on dataset_source
```

2. **Enhance phishing indicator extraction:**
```python
def _extract_phishing_indicators(
    *,
    email_text: str,
    subject: str,
    sender: str,
) -> dict[str, Any]:
    """Extract comprehensive phishing indicators with taxonomy.

    Returns:
        {
            "indicators": [...],  # List of indicator strings
            "types": [...],       # Phishing types detected
            "difficulty": "easy|medium|hard"
        }
    """
    # Enhanced extraction logic:
    # - URL shorteners, homoglyphs, suspicious TLDs
    # - Sender/display name mismatches
    # - Urgency/credential requests
    # - Difficulty scoring based on indicator clarity
```

3. **Add dataset helper functions:**
```python
def _try_load_local_dataset(dataset_name: str, data_dir: Path) -> Dataset | None:
    """Try loading dataset from local data directory."""
    # Check environments/sv-env-phishing-detection/data/{dataset_name}

def _try_load_hub_dataset(repo_id: str, split: str, hf_token: str | None) -> Dataset | None:
    """Try loading dataset from HuggingFace Hub with gated access handling."""
    # Use HF_TOKEN and E4_HF_REPO env vars
    # Handle gated access errors with actionable messages
```

4. **Update transform_dataset for enhanced metadata:**
```python
def transform_dataset(raw_dataset: Dataset, max_examples: int | None) -> Dataset:
    """Transform raw phishing datasets into SingleTurnEnv format."""
    # Enhanced to preserve:
    # - Phishing type taxonomy
    # - Difficulty scoring
    # - Source attribution
    # - Language metadata
```

#### File: `environments/sv-env-phishing-detection/data/`

**New Files:**
- `phishing-train-dev-test-test.jsonl` (20-30 examples for CI)
- `sampling-e4-v1.json` (sampling metadata)
- `sampling-demo.json` (demo configuration)

#### File: `environments/sv-env-phishing-detection/README.md`

**Update to match E1/E2 production pattern:**
- Remove aspirational ToolEnv claims
- Add dataset access section (public metadata + gated private)
- Add dataset loading strategies (local/hub/synthetic)
- Add evaluation examples with expected metrics
- Remove non-existent tools (keep focused on evidence-based classification)
- Add performance benchmarks table (to be populated)

#### File: `environments/sv-env-phishing-detection/README-DEV.md` (NEW)

**Content:**
```markdown
# E4 Developer Documentation

## Dataset Building
- How to run build_e4_phishing.py
- Source dataset requirements
- Schema validation

## Evaluation
- Running eval_phishing_detection.py
- Metrics interpretation
- Debugging low rewards

## Contributing
- Adding new phishing types
- Enhancing indicator extraction
- Test fixture maintenance
```

#### File: `environments/sv-env-phishing-detection/DATA_CARD.md` (NEW)

**Content:**
```markdown
# E4 Dataset Card

## Sources
- zefang-liu/phishing-email-dataset (18.7k)
- ealvaradob/phishing-dataset
- Enron corpus (ham)
- Synthetic business emails

## Statistics
- Train: X examples
- Dev: Y examples
- Test: Z examples
- Phishing/Legitimate ratio: ...

## Phishing Type Distribution
- Credential harvest: %
- Invoice fraud: %
- ...

## Privacy & Ethics
- All datasets are public or synthesized
- Corporate emails are sanitized/anonymized
- Gated access prevents contamination
```

---

## 5. Documentation Updates

### 5.1 Repository-Level Documentation

#### File: `README.md` (root)

**Updates:**
- Update E4 status from "Alpha" to "Production-Ready"
- Add E4 to evaluation examples
- Update environment status table

#### File: `PRD.md`

**Updates:**
- Expand E4 specification with production dataset details
- Add phishing type taxonomy
- Document difficulty scoring methodology
- Update reward weights to match implementation

#### File: `CLAUDE.md`

**Updates:**
- Add E4 to Makefile command examples
- Document `make eval-e4`, `make data-e4`, `make report-phishing-detection`
- Add E4 to dataset management section

### 5.2 New Documentation Files

#### File: `docs/phishing-taxonomy.md` (NEW)

**Content:**
```markdown
# Phishing Email Taxonomy

## Attack Vectors
1. **Credential Harvest:** Fake login pages
2. **Invoice Fraud:** Fake invoices/payment requests
3. **CEO Fraud:** Impersonation of executives
4. **Tech Support Scams:** Fake IT/support requests
5. **Prize/Lottery Scams:** Fake winnings
6. **Urgency/Threat:** Account suspension threats

## Indicator Types
- URL-based: Shorteners, homoglyphs, suspicious TLDs
- Sender-based: Domain spoofing, free email providers
- Content-based: Urgency language, credential requests
- Metadata: Missing SPF/DKIM, reply-to mismatches

## Difficulty Levels
- Easy: Multiple obvious indicators
- Medium: Subtle spoofing, fewer indicators
- Hard: Sophisticated attacks, minimal indicators
```

---

## 6. Baseline Benchmarking

### 6.1 Model Selection (from Research Plans)

#### Closed-Source Models (2025 SOTA)
1. **GPT-5** (OpenAI flagship, 2M context)
2. **GPT-5-mini** (cost-effective baseline)
3. **Claude-Sonnet-4.5** (Anthropic, extended thinking)
4. **Claude-Opus-4.1** (1M context, 72.5% SWE-bench)
5. **Gemini-2.5-Pro** (Google, 86.4 GPQA)

#### Open-Source Models (Fine-Tuning Targets)
1. **Qwen3-32B** (131K context, efficient dense)
2. **Qwen3-235B** (beats GPT-4o on code)
3. **DeepSeek-R1-Distill-Qwen-32B** (beats o1-mini)
4. **Llama-4-Scout** (10M context MoE)
5. **Mistral-Small-3** (24B dense)

### 6.2 Evaluation Plan

**Phase 1: Initial Baselines (Week 1)**
```bash
# Quick smoke test on all models
make eval-e4 MODELS="gpt-5-mini,gpt-4.5,claude-sonnet-4.5,qwen3-32b" N=10

# Full baseline on primary dataset
make eval-e4 MODELS="gpt-5-mini,gpt-4.5,claude-sonnet-4.5" N=1500 \
  DATASET="phishing-train-dev-test-v1.jsonl"
```

**Phase 2: OOD Evaluation (Week 2)**
```bash
# Corporate emails OOD
make eval-e4 MODELS="gpt-5-mini,claude-sonnet-4.5" N=500 \
  DATASET="corporate-emails-ood-v1.jsonl"

# Multilingual OOD
make eval-e4 MODELS="gpt-5-mini,claude-sonnet-4.5" N=500 \
  DATASET="multilingual-phishing-ood-v1.jsonl"
```

**Phase 3: Comprehensive Report (Week 3)**
```bash
# Generate benchmark report across all runs
make report-phishing-detection OUTPUT="reports/e4-baseline-2025.json"
```

### 6.3 Success Criteria (from Research Plans)

**Minimum Acceptable Performance (based on CLAUDE plan estimates):**

| Model | Accuracy | FN Rate | FP Rate | Evidence Precision | Overall Reward |
|-------|----------|---------|---------|-------------------|----------------|
| GPT-5-mini | 85% | <8% | <10% | >70% | >0.80 |
| GPT-4.5 | 90% | <5% | <7% | >75% | >0.85 |
| Claude-Sonnet-4.5 | 92% | <4% | <6% | >80% | >0.88 |
| Qwen3-32B (baseline) | 80% | <12% | <12% | >65% | >0.75 |

**Target Improvements (Post-SFT, from CLAUDE plan):**
- Accuracy: +20% relative
- FN Rate: -50% relative (critical)
- Evidence Precision: +15% relative

**Target Improvements (Post-RLFT, from CLAUDE plan):**
- Additional +10% on calibration
- Additional -30% on FN rate
- Better abstention on ambiguous cases

---

## 7. Implementation Phases

### Phase 1: Dataset Infrastructure (Weeks 1-2)

**Deliverables:**
- [ ] `scripts/data/build_e4_phishing.py` implementation
- [ ] `scripts/data/build_e4_ood.py` implementation
- [ ] Enhanced phishing indicator extraction in environment
- [ ] Test fixtures in `data/phishing-train-dev-test-test.jsonl`
- [ ] Makefile targets: `data-e4`, `data-e4-ood`, `data-e4-test`
- [ ] DATA_CARD.md documentation

**Acceptance Criteria:**
- [ ] `make data-e4` produces ~15k examples in correct schema
- [ ] `make data-e4-ood` produces 500 examples each (corporate, multilingual)
- [ ] `make data-e4-test` produces 20-30 CI fixtures
- [ ] All datasets pass Pydantic validation
- [ ] Phishing indicators extracted with >90% recall

### Phase 2: Evaluation Infrastructure (Weeks 3-4)

**Deliverables:**
- [ ] `scripts/eval_phishing_detection.py` implementation
- [ ] `scripts/generate_e4_eval_report.py` implementation
- [ ] Makefile targets: `eval-e4`, `report-phishing-detection`
- [ ] README-DEV.md documentation
- [ ] Updated environment with multi-source dataset loading

**Acceptance Criteria:**
- [ ] `make eval-e4` runs successfully with model routing
- [ ] Results export to correct directory structure
- [ ] `make report-phishing-detection` generates metrics report
- [ ] All metrics (Acc, FN%, FP%, ECE, Evidence%) computed correctly
- [ ] Weave auto-tracing captures all evaluations

### Phase 3: HuggingFace Distribution (Week 5)

**Deliverables:**
- [ ] Public metadata repo: `intertwine-ai/security-verifiers-e4-metadata`
- [ ] Private gated repo: `intertwine-ai/security-verifiers-e4`
- [ ] Makefile targets: `hf-e4-push`, `hf-e4p-push-canonical`
- [ ] `scripts/hf/export_metadata_flat.py` E4 support
- [ ] `scripts/hf/push_canonical_with_features.py` E4 support
- [ ] `scripts/data/validate_splits_e4.py` implementation

**Acceptance Criteria:**
- [ ] `make hf-e4-push` publishes metadata successfully
- [ ] `make hf-e4p-push-canonical` uploads full dataset with gating
- [ ] Dataset viewer works on metadata repo
- [ ] Gated access prompts users correctly
- [ ] `make validate-e4-data` passes on all splits

### Phase 4: Baseline Benchmarking (Weeks 6-7)

**Deliverables:**
- [ ] Baseline evaluations for 5 closed-source models
- [ ] Baseline evaluations for 3 open-source models
- [ ] OOD evaluations (corporate, multilingual)
- [ ] Comprehensive benchmark report
- [ ] Updated README.md with performance table

**Acceptance Criteria:**
- [ ] All models evaluated on ≥1500 examples
- [ ] Metrics meet minimum acceptable thresholds
- [ ] OOD performance documented
- [ ] Baseline report published to `reports/e4-baseline-2025.json`
- [ ] README performance table populated

### Phase 5: Documentation & Integration (Week 8)

**Deliverables:**
- [ ] Updated README.md (production-ready, remove aspirational content)
- [ ] README-DEV.md (developer guide)
- [ ] DATA_CARD.md (dataset documentation)
- [ ] docs/phishing-taxonomy.md (taxonomy reference)
- [ ] CLAUDE.md updates (E4 commands)
- [ ] PRD.md updates (E4 specification)

**Acceptance Criteria:**
- [ ] All documentation accurate and complete
- [ ] README matches E1/E2 production pattern
- [ ] No aspirational/future features listed as current
- [ ] Developer guide enables new contributors
- [ ] Taxonomy covers all phishing types in dataset

### Phase 6: CI/CD & Release (Week 9)

**Deliverables:**
- [ ] CI integration: `make e4` in GitHub Actions
- [ ] Version bump to 1.0.0
- [ ] Hub deployment: `make hub-deploy E=phishing-detection`
- [ ] Release notes
- [ ] Announcement (blog post/paper)

**Acceptance Criteria:**
- [ ] `make e4` passes in CI
- [ ] Environment deploys successfully to Prime Hub
- [ ] Version tagged in git
- [ ] Release announcement published
- [ ] External users can install and run environment

---

## 8. Future Enhancements (Post-Production, Phase 2)

**Not included in this productionization plan, but identified in research plans:**

### 8.1 Tool Integration (ToolEnv Upgrade)

**Potential Tools (from README vision):**
1. **check_url_reputation:** VirusTotal/Google Safe Browsing API
2. **lookup_domain_whois:** Domain registration/age lookup
3. **search_similar_campaigns:** Threat intelligence search
4. **verify_sender_authenticity:** SPF/DKIM/DMARC validation

**Rationale for deferring:**
- Current SingleTurnEnv is production-ready and aligns with E1
- Tool integration requires significant infrastructure (API keys, rate limits, caching)
- E2 ToolEnv pattern is complex and still being refined
- Focus on dataset quality and baseline benchmarks first

**Future work:**
- Design tool adapter interfaces (similar to E2)
- Evaluate impact of tools on reward
- Compare single-turn (evidence-only) vs multi-turn (tool-grounded)

### 8.2 Advanced Synthetic Data Generation

**Techniques from research plans:**
1. **LLM-generated phishing variants** (CLAUDE plan)
   - Use GPT-5 to generate realistic phishing with specific tactics
   - Style transfer from benign → phishing
   - Controllable generation (vector, sophistication level)

2. **Feature-based synthesis** (CLAUDE plan)
   - Programmatic mutation of legitimate emails
   - URL obfuscation techniques
   - Urgency cue injection/removal

3. **Adversarial examples** (CLAUDE plan)
   - Benign emails with superficial indicators
   - Sophisticated phishing with few obvious signs
   - Boundary cases for calibration training

**Future work:**
- SFT training data generation pipeline
- RLFT training with environment rewards
- Cross-corpus transfer experiments

### 8.3 Multi-Language Support

**Datasets:**
- Multilingual phishing corpora (Spanish, French, Chinese)
- Cross-lingual transfer evaluation

**Challenges:**
- Language-specific phishing tactics
- Indicator extraction for non-English
- Translation quality for evidence

### 8.4 Attachment Analysis

**Scope:**
- Document scanning (PDF, DOCX) for malicious macros
- Executable analysis (static indicators)
- Link extraction from attachments

**Challenges:**
- Requires file upload/parsing infrastructure
- Security sandboxing for malicious samples
- Large model context for document content

---

## 9. Risk Assessment & Mitigations

### 9.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| **Dataset quality issues** | High - Poor training/eval | Medium | Multi-source validation, manual spot checks, Pydantic schemas |
| **HuggingFace access failures** | Medium - Eval disruption | Low | Multi-tiered loading (local fallback), cached datasets |
| **Model API rate limits** | Medium - Slow evals | Medium | Early stopping, batch scheduling, cost budgeting |
| **Indicator extraction errors** | High - Evidence rewards fail | Low | Unit tests, golden test cases, regression suite |
| **OOD dataset bias** | Medium - Unrealistic evals | Medium | Diverse sources, domain expert review, taxonomy coverage |

### 9.2 Schedule Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| **Dataset building delays** | High - Blocks all phases | Low | Start early, use existing zefang-liu dataset as baseline |
| **Evaluation infra complexity** | Medium - Delays baselines | Medium | Copy E1 pattern closely, reuse model_router |
| **HF distribution issues** | Low - Can defer | Low | Test with E1/E2 patterns first |
| **Documentation scope creep** | Low - Delays release | Medium | Time-box documentation, defer non-critical docs |

### 9.3 Data Privacy & Ethics

**Considerations:**
- All source datasets are public or synthesized
- Corporate emails must be sanitized/anonymized before inclusion
- Gated access prevents LLM training contamination
- Evaluation-only license enforced

**Mitigation:**
- Legal review of dataset sources
- PII scrubbing for corporate emails
- Clear licensing in dataset cards
- Gating enforcement on HF repos

---

## 10. Success Metrics

### 10.1 Quantitative Targets

**Dataset Quality:**
- [ ] ≥15,000 training examples
- [ ] ≥500 OOD examples per category
- [ ] Phishing indicator recall >90%
- [ ] Schema validation pass rate 100%

**Evaluation Infrastructure:**
- [ ] Eval script success rate >95%
- [ ] Metrics computation accuracy 100%
- [ ] Report generation <5 min for 1500 examples

**Baseline Performance (GPT-5-mini):**
- [ ] Accuracy ≥85%
- [ ] FN Rate ≤8%
- [ ] Evidence Precision ≥70%
- [ ] Overall Reward ≥0.80

### 10.2 Qualitative Targets

- [ ] Documentation clarity: New contributor can run eval in <30 min
- [ ] Dataset diversity: Covers all major phishing tactics
- [ ] Metrics interpretability: Clear actionable insights from reports
- [ ] Community adoption: External researchers use E4 in papers/projects

### 10.3 Parity with E1/E2

**Achieved when E4 matches E1/E2 on:**
- [ ] Multi-tiered dataset loading (local/hub/synthetic)
- [ ] Gated HuggingFace distribution
- [ ] Makefile integration (data/eval/report targets)
- [ ] Comprehensive documentation (README, README-DEV, DATA_CARD)
- [ ] Baseline benchmarks published
- [ ] CI integration and Hub deployment

---

## 11. Resource Requirements

### 11.1 Personnel

**Roles:**
- **ML Engineer (1 FTE, 9 weeks):** Dataset building, evaluation scripts, benchmarking
- **Data Engineer (0.5 FTE, 5 weeks):** Dataset curation, HF distribution, validation
- **Technical Writer (0.25 FTE, 2 weeks):** Documentation updates, README polish

**Total Effort:** ~13 person-weeks

### 11.2 Compute Resources

**Dataset Building:**
- Negligible (data processing, no model inference)
- Local machine sufficient

**Baseline Evaluation:**
- 5 closed-source models × 1500 examples × 3 datasets = 22,500 API calls
- Estimated cost: ~$500 (GPT-5-mini), ~$2000 (mix of GPT-5/Claude)
- Duration: ~2-3 days (with rate limiting)

**Storage:**
- Datasets: ~500 MB (JSONL)
- Evaluation results: ~2 GB (artifacts)
- HuggingFace: ~1 GB (gated repo)

### 11.3 External Dependencies

**Required:**
- HuggingFace account + token (dataset distribution)
- OpenAI API key (baseline evals)
- OpenRouter API key (open-source model evals)
- Weights & Biases account (Weave tracing, optional)

**Optional:**
- Anthropic API key (Claude models)
- Google Cloud account (Gemini models)

---

## 12. Next Actions (Week 0)

### Immediate Tasks (This Week)
1. [ ] **Create issue tracker:** GitHub project board for E4 productionization
2. [ ] **Spike: Dataset building:** Prototype `build_e4_phishing.py` with zefang-liu dataset
3. [ ] **Spike: Indicator extraction:** Test enhanced phishing indicator extraction
4. [ ] **Review & approval:** Present this plan to team, get go/no-go decision

### Week 1 Kickoff
1. [ ] **Dataset infrastructure:** Start Phase 1 implementation
2. [ ] **Setup:** Provision API keys, HF repos, storage
3. [ ] **Documentation:** Create README-DEV skeleton
4. [ ] **CI:** Add E4 placeholder to GitHub Actions

---

## 13. Appendices

### Appendix A: Research Plan Comparison

| Aspect | CODEX | CLAUDE | DROID | Unified (This Plan) |
|--------|-------|--------|-------|---------------------|
| **Scope** | 24-week research program | 20-week model improvement | Integration-focused | 9-week productionization |
| **Primary Dataset** | ealvaradob, pirocheto | zefang-liu, ealvaradob | Enron, zefang-liu | zefang-liu (current) + multi-source |
| **Env Type** | SingleTurnEnv, optional tools | SingleTurnEnv, evidence focus | SingleTurnEnv, optional tools | SingleTurnEnv (ToolEnv deferred) |
| **Training Focus** | SFT → RLFT, cross-corpus | SFT → RLFT, 15K examples | SFT → RLFT, abstention calibration | Baseline benchmarks only |
| **Evaluation** | Comprehensive baselines | Detailed metrics (Acc, FN, Evidence) | Cost-balanced rewards | Mirrors E1 pattern |
| **Unique Insights** | Corporate phishing, red-team captures | 2025 SOTA models, detailed training recipes | Weave integration, dual-mode logging | Production infrastructure, gated datasets |

**Synthesis Decisions:**
- **Dataset:** Adopt zefang-liu (current) + ealvaradob (CODEX/CLAUDE) + Enron (DROID) multi-source strategy
- **Env Type:** Keep SingleTurnEnv (current), defer ToolEnv to Phase 2
- **Training:** Defer to future work, focus on baseline infrastructure (this plan)
- **Evaluation:** Follow E1 pattern (DROID-aligned), add E4-specific metrics (CLAUDE-aligned)
- **Models:** Use 2025 SOTA from CLAUDE plan

### Appendix B: E1/E2 Pattern Analysis

**Common Production Patterns:**
1. Multi-tiered dataset loading (local → hub → synthetic/builtin)
2. Gated HuggingFace repos (private full + public metadata)
3. Makefile targets (data-e*, eval-e*, report-*)
4. Evaluation scripts with model routing
5. Report generation with metrics breakdown
6. Documentation trio (README, README-DEV, DATA_CARD)
7. Pydantic validation for datasets
8. CI integration (make e*)

**E4 Adaptations:**
- Follow E1 pattern (SingleTurnEnv) rather than E2 (ToolEnv)
- Dataset sources: Multiple phishing datasets vs single IoT-23 (E1)
- Metrics: Add evidence precision vs E1's pure classification
- OOD: Corporate/multilingual vs CIC/UNSW (E1)

### Appendix C: Phishing Dataset Landscape (2025)

**HuggingFace Datasets:**
1. **zefang-liu/phishing-email-dataset** (18.7k) - Current target
2. **ealvaradob/phishing-dataset** - CODEX/CLAUDE recommended
3. **pirocheto/phishing-url** - URL-focused, CODEX recommended
4. **zeroshot/cybersecurity-corpus** - Context, CLAUDE recommended
5. **ahmed000000000/cybersec** - Broader security corpus

**Classic Corpora:**
1. **Enron Email Corpus** - Legitimate business emails
2. **APWG Phishing Corpus** - Real-world phishing samples
3. **Nazario Corpus** - Historical phishing collection

**OOD Sources:**
1. **Corporate red-team captures** - Internal phishing simulations (sanitized)
2. **Multilingual corpora** - Non-English phishing campaigns
3. **Synthetic business emails** - Modern SaaS notifications (GitHub, Slack, etc.)

---

## Document Metadata

**Authors:** Claude (AI Assistant), Intertwine AI Team
**Version:** 1.0
**Last Updated:** 2025-11-06
**Status:** Draft for Review
**Next Review:** 2025-11-13 (go/no-go decision)

**Related Documents:**
- [RESEARCH-CODEX.md](RESEARCH-CODEX.md) - 24-week research program
- [RESEARCH-CLAUDE.md](RESEARCH-CLAUDE.md) - Model improvement methodology
- [RESEARCH-DROID.md](RESEARCH-DROID.md) - Integration-focused vision
- [PRD.md](../PRD.md) - Environment specifications
- [CLAUDE.md](../CLAUDE.md) - Repository guide

**Change Log:**
- 2025-11-06: Initial draft, synthesized from three research plans
