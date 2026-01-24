# Prime Intellect Environments Hub Compatibility

This document assesses the compatibility of the Open Security Verifiers repository with Prime Intellect's Environments Hub and `vf-eval` style evaluations.

## Executive Summary

**Compatibility Status: ✅ HIGH COMPATIBILITY**

The Open Security Verifiers environments are **already highly compatible** with Prime Intellect's Environments Hub. The repository follows the correct package structure, entry point conventions, and `load_environment()` patterns. However, some adjustments are recommended for optimal integration with `vf-eval` and Hub-based evaluations.

## Current Implementation Analysis

### ✅ What's Already Compatible

1. **Package Structure** (`pyproject.toml`)
   - All six environments are properly packaged with `pyproject.toml` files
   - Dependencies are correctly declared
   - Build system uses hatchling (compatible with pip/uv)
   - Example from `sv-env-network-logs/pyproject.toml`:
     ```toml
     [project.entry-points."verifiers.environments"]
     sv-env-network-logs = "sv_env_network_logs:load_environment"
     ```

2. **Entry Points Convention**
   - All environments correctly expose `load_environment()` via `[project.entry-points."verifiers.environments"]`
   - Entry point naming follows Hub conventions: `owner/env-name` or `env-name`
   - This matches Prime Intellect's requirements for environment discovery

3. **Environment Interface**
   - All `load_environment()` functions return proper `verifiers` environment objects:
     - E1: `vf.SingleTurnEnv`
     - E2: `vf.ToolEnv`
     - E3-E6: Various environment types
   - Functions accept standard parameters (dataset_name, max_examples, logger, etc.)
   - Parsers, rubrics, and system prompts are correctly implemented

4. **Deployment Infrastructure**
   - `Makefile` already includes `deploy` target using `prime env push`
   - Example: `make deploy E=network-logs`
   - Uses Prime CLI: `prime login` and `prime env push -v PUBLIC`

5. **vf-eval Configuration**
   - Repository includes `configs/endpoints.py` with endpoint configurations
   - README files contain `vf-eval` usage examples
   - Example from `sv-env-network-logs/README-DEV.md`:
     ```bash
     vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3
     ```

### ⚠️ Compatibility Gaps & Recommendations

1. **Dataset Loading Strategy**
   - **Current:** Environments load datasets from local JSONL files
     - E1: `environments/sv-env-network-logs/data/iot23-train-dev-test-v1.jsonl`
     - E2: `environments/sv-env-config-verification/data/k8s-labeled-v1.jsonl`
   - **Issue:** When deployed to Hub, these local files won't be accessible
   - **Solution:** Implement multi-tiered dataset loading strategy (see Implementation Plan)

2. **vf-eval Testing**
   - **Current:** No automated tests for `vf-eval` compatibility
   - **Issue:** Can't verify Hub evaluations work correctly
   - **Solution:** Add integration tests for `vf-eval` command

3. **Evaluation Script Duplication**
   - **Current:** Custom evaluation scripts in `scripts/eval_*.py`
   - **Issue:** Parallel evaluation systems (custom scripts + vf-eval)
   - **Observation:** Custom scripts provide additional features:
     - Model routing (OpenAI + OpenRouter)
     - Early stopping on consecutive errors
     - Detailed artifact logging (metadata.json, results.jsonl)
   - **Solution:** Document both workflows; use custom scripts for research, vf-eval for Hub

4. **Hub Deployment Validation**
   - **Current:** Deployment target exists but not documented/tested
   - **Issue:** Unknown if current environments can be deployed/installed via Hub
   - **Solution:** Add deployment validation workflow

## Prime Intellect Requirements (Reference)

Based on [Prime Intellect documentation](https://docs.primeintellect.ai/) and the [Verifiers library](https://github.com/PrimeIntellect-ai/verifiers):

### Environment Structure Requirements

1. **Installable Python Package**
   - Must have `pyproject.toml` with dependencies ✅
   - Must be buildable as a wheel ✅
   - Must be pip/uv installable ✅

2. **Entry Point Registration**
   - Must expose `load_environment()` via entry points ✅
   - Format: `[project.entry-points."verifiers.environments"]` ✅
   - Entry point name becomes the environment identifier ✅

3. **load_environment() Function**
   - Must return a `verifiers.Environment` subclass ✅
   - Should accept standard parameters (dataset_name, max_examples, etc.) ✅
   - Should support synthetic/test datasets for quick testing ✅

4. **Hub Deployment**
   - Build wheel: `python -m build --wheel` ✅
   - Authenticate: `prime login` ✅
   - Deploy: `prime env push -v PUBLIC` ✅
   - Install: `prime env install owner/env-name` (untested)

5. **vf-eval Compatibility**
   - Must be loadable via `vf.load_environment("env-name")` ✅
   - Must work with `vf-eval env-name --model MODEL --num-examples N` (partially tested)
   - Should handle API keys via environment variables ✅

### Current Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Package structure | ✅ Complete | All environments properly packaged |
| Entry points | ✅ Complete | Correct convention followed |
| load_environment() | ✅ Complete | Returns proper vf.Environment objects |
| Build system | ✅ Complete | Wheels build successfully |
| Deployment target | ⚠️ Partial | Makefile target exists but untested |
| vf-eval examples | ⚠️ Partial | Documented but not CI-tested |
| Hub dataset access | ⚠️ Needs work | Local file dependencies |
| vf-eval integration tests | ❌ Missing | No automated validation |

## Implementation Plan: Full Hub Compatibility

### Phase 1: Dataset Strategy (Priority: High)

**Goal:** Enable environments to work both locally and when deployed to Hub

**Approach:** Implement multi-tiered dataset loading

```python
def load_environment(
    dataset_name: str = "iot23-train-dev-test-v1.jsonl",
    dataset_source: str = "auto",  # auto | local | hub | synthetic
    max_examples: int = 1000,
    logger: RolloutLogger | None = None,
) -> vf.SingleTurnEnv:
    """Load environment with flexible dataset sources.

    Dataset loading priority (when source="auto"):
    1. Local JSONL files (environments/sv-env-*/data/*.jsonl)
    2. HuggingFace Hub (with HF_TOKEN)
    3. Synthetic fixtures (for testing)
    """
    if dataset_source == "auto":
        # Try local first
        if _local_dataset_exists(dataset_name):
            dataset = _load_local_dataset(dataset_name, max_examples)
        # Try Hub second
        elif _hub_credentials_available():
            dataset = _load_hub_dataset(dataset_name, max_examples)
        # Fall back to synthetic
        else:
            dataset = _create_synthetic_dataset(max_examples)
    elif dataset_source == "local":
        dataset = _load_local_dataset(dataset_name, max_examples)
    elif dataset_source == "hub":
        dataset = _load_hub_dataset(dataset_name, max_examples)
    elif dataset_source == "synthetic":
        dataset = _create_synthetic_dataset(max_examples)

    # Rest of environment setup...
```

**Implementation Steps:**

1. Add `dataset_source` parameter to all `load_environment()` functions
2. Implement HuggingFace Hub dataset loading helper:
   ```python
   def _load_hub_dataset(dataset_name: str, max_examples: int):
       """Load dataset from HuggingFace Hub."""
       from datasets import load_dataset

       # Map local names to Hub repos
       HUB_DATASETS = {
           "iot23-train-dev-test-v1.jsonl": "intertwine-ai/security-verifiers-e1",
           "k8s-labeled-v1.jsonl": "intertwine-ai/security-verifiers-e2",
           # ... etc
       }

       hub_repo = HUB_DATASETS.get(dataset_name)
       if not hub_repo:
           raise ValueError(f"Unknown dataset: {dataset_name}")

       dataset = load_dataset(hub_repo, split="train", use_auth_token=True)
       return dataset.select(range(min(len(dataset), max_examples)))
   ```
3. Update environment READMEs to document dataset source options
4. Add integration tests for each dataset source

**Benefits:**
- Environments work locally (current workflow)
- Environments work when deployed to Hub (requires HF_TOKEN)
- Synthetic datasets enable quick testing without data dependencies

### Phase 2: vf-eval Integration Tests (Priority: Medium)

**Goal:** Validate that environments work correctly with `vf-eval` command

**Implementation Steps:**

1. Create `tests/integration/test_vfeval.py`:
   ```python
   import subprocess
   import os
   import pytest

   @pytest.mark.integration
   def test_vfeval_e1_synthetic():
       """Test vf-eval with E1 using synthetic dataset."""
       result = subprocess.run([
           "vf-eval", "sv-env-network-logs",
           "--model", "gpt-5-mini",
           "--num-examples", "3",
           "--dataset", "synthetic"
       ], env={**os.environ, "DATASET_SOURCE": "synthetic"})
       assert result.returncode == 0

   @pytest.mark.integration
   def test_vfeval_e2_fixtures():
       """Test vf-eval with E2 using builtin fixtures."""
       result = subprocess.run([
           "vf-eval", "sv-env-config-verification",
           "--model", "gpt-5-mini",
           "--num-examples", "2",
           "--dataset", "builtin"
       ])
       assert result.returncode == 0
   ```

2. Add integration test CI workflow:
   ```yaml
   # .github/workflows/integration.yml
   name: Integration Tests
   on: [push, pull_request]
   jobs:
     vfeval:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
         - run: make setup
         - run: source .venv/bin/activate
         - run: pytest tests/integration/ -v -m integration
   ```

3. Add Makefile target:
   ```makefile
   test-integration: venv
       @$(ECHO) "$(YELLOW)Running integration tests...$(NC)"
       @$(ACTIVATE) && pytest tests/integration/ -v -m integration
   ```

**Benefits:**
- Automated validation of vf-eval compatibility
- Catch regressions before Hub deployment
- Documentation that vf-eval works correctly

### Phase 3: Hub Deployment Validation (Priority: Medium)

**Goal:** Verify environments can be deployed and installed via Hub

**Implementation Steps:**

1. Create deployment validation script (`scripts/validate_hub_deployment.sh`):
   ```bash
   #!/bin/bash
   set -e

   ENV_NAME=$1

   echo "Building wheel for $ENV_NAME..."
   cd environments/sv-env-$ENV_NAME
   python -m build --wheel

   echo "Checking wheel contents..."
   unzip -l dist/*.whl

   echo "Testing local installation..."
   uv pip install dist/*.whl --force-reinstall

   echo "Testing load_environment..."
   python -c "import verifiers as vf; env = vf.load_environment('sv-env-$ENV_NAME', dataset_source='synthetic'); print(f'✓ Loaded {env.name}')"

   echo "✓ $ENV_NAME validation passed"
   ```

2. Add to Makefile:
   ```makefile
   validate-env: venv
       @if [ -z "$(E)" ]; then \
           echo "Error: Specify E=env-name"; exit 1; \
       fi
       @./scripts/validate_hub_deployment.sh $(E)
   ```

3. Document manual Hub deployment testing:
   ```markdown
   ## Testing Hub Deployment

   1. Build and push to Hub (requires prime CLI):
      ```bash
      make deploy E=network-logs
      ```

   2. Install from Hub (in clean environment):
      ```bash
      prime env install intertwine/sv-env-network-logs
      ```

   3. Test with vf-eval:
      ```bash
      vf-eval intertwine/sv-env-network-logs --model gpt-5-mini --num-examples 3
      ```
   ```

**Benefits:**
- Confidence that environments deploy successfully
- Catch packaging issues before Hub upload
- Documented deployment workflow

### Phase 4: Documentation & Examples (Priority: High)

**Goal:** Comprehensive documentation for Hub usage

**Implementation Steps:**

1. Create `docs/hub-deployment.md`:
   - Prerequisites (prime CLI, API keys)
   - Building wheels
   - Deploying to Hub
   - Installing from Hub
   - Using vf-eval
   - Troubleshooting common issues

2. Update environment READMEs with Hub examples:
   ```markdown
   ## Using from Prime Intellect Hub

   ### Install
   ```bash
   prime env install intertwine/sv-env-network-logs
   ```

   ### Evaluate
   ```bash
   # Set API keys
   export OPENAI_API_KEY=your-key-here

   # Run evaluation
   vf-eval intertwine/sv-env-network-logs \
     --model gpt-5-mini \
     --num-examples 10
   ```

   ### Load in Python
   ```python
   import verifiers as vf

   env = vf.load_environment(
       "intertwine/sv-env-network-logs",
       dataset_source="hub",  # Use Hub datasets
       max_examples=100
   )
   ```
   ```

3. Add Hub deployment checklist to `CONTRIBUTING.md`:
   ```markdown
   ## Hub Deployment Checklist

   - [ ] All tests passing
   - [ ] Wheel builds successfully
   - [ ] Local installation works
   - [ ] vf-eval works with synthetic dataset
   - [ ] Environment loads correctly
   - [ ] API keys documented
   - [ ] README updated with Hub examples
   - [ ] Version bumped in pyproject.toml
   ```

4. Create Hub-specific Makefile targets:
   ```makefile
   # Validate environment is Hub-ready
   hub-validate: venv
       @$(MAKE) validate-env E=$(E)
       @$(MAKE) test-env E=$(E)

   # Deploy with validation
   hub-deploy: venv
       @$(MAKE) hub-validate E=$(E)
       @$(MAKE) deploy E=$(E)
   ```

**Benefits:**
- Clear path for contributors
- Reduced deployment errors
- Better user experience

## Comparison: Custom Scripts vs. vf-eval

### Current Custom Scripts (`scripts/eval_*.py`)

**Advantages:**
- Multi-model routing (OpenAI + OpenRouter APIs)
- Automatic model name resolution via `model_router.py`
- Early stopping on consecutive errors (prevents wasted API costs)
- Structured artifact logging:
  - `outputs/evals/sv-env-{name}--{model}/{run_id}/metadata.json`
  - `outputs/evals/sv-env-{name}--{model}/{run_id}/results.jsonl`
- Dataset selection with validation
- Git commit tracking in metadata
- Reproducible evaluations with complete provenance

**Use Cases:**
- Research evaluations
- Benchmarking multiple models
- Cost-sensitive experiments
- Local development

### vf-eval Command

**Advantages:**
- Standard Prime Intellect interface
- Works with Hub-deployed environments
- Simpler command line interface
- Integration with Prime Intellect infrastructure
- Compatible with RL training workflows

**Use Cases:**
- Hub-based evaluations
- Quick environment testing
- Standard benchmarks
- Integration with Prime RL training

### Recommendation: Support Both

**Strategy:**
- **Custom scripts:** Primary research evaluation workflow
- **vf-eval:** Hub compatibility and quick testing

**Implementation:**
- Keep custom scripts for advanced features
- Ensure environments work with both approaches
- Document when to use each
- Add integration tests for vf-eval

## Testing Roadmap

### Phase 1: Basic Compatibility
- [ ] Verify entry points are discoverable
- [ ] Test `vf.load_environment("env-name")` for all environments
- [ ] Validate synthetic datasets work with vf-eval

### Phase 2: Local vf-eval
- [ ] Test `vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3`
- [ ] Test `vf-eval sv-env-config-verification --model gpt-5-mini --num-examples 2`
- [ ] Validate API key handling
- [ ] Test with multiple models

### Phase 3: Hub Deployment
- [ ] Build and validate all environment wheels
- [ ] Deploy test environment to Hub
- [ ] Install from Hub in clean environment
- [ ] Run vf-eval with Hub-installed environment

### Phase 4: Dataset Integration
- [ ] Implement Hub dataset loading
- [ ] Test fallback strategy (local → hub → synthetic)
- [ ] Validate with production datasets
- [ ] Test without local data files

### Phase 5: Documentation
- [ ] Update all environment READMEs
- [ ] Create Hub deployment guide
- [ ] Add troubleshooting documentation
- [ ] Create video walkthrough (optional)

## Quick Start: Testing Hub Compatibility

### Option 1: Test vf-eval Locally (No Hub Required)

```bash
# Setup
make setup
source .venv/bin/activate

# Test E1 with synthetic dataset
vf-eval sv-env-network-logs --model gpt-5-mini --num-examples 3

# Test E2 with builtin fixtures
vf-eval sv-env-config-verification --model gpt-5-mini --num-examples 2
```

### Option 2: Test Full Hub Workflow (Requires Prime CLI)

```bash
# Setup
uv tool install prime
prime login

# Build and deploy
make deploy E=network-logs

# Install in new environment
cd /tmp
python -m venv test_env
source test_env/bin/activate
prime env install intertwine/sv-env-network-logs

# Test
export OPENAI_API_KEY=your-key
vf-eval intertwine/sv-env-network-logs --model gpt-5-mini --num-examples 3
```

## Recommended Next Steps

### Immediate (Week 1)
1. ✅ **Document current compatibility status** (this document)
2. Test basic vf-eval locally with synthetic datasets
3. Validate entry points work correctly
4. Run integration tests manually

### Short-term (Weeks 2-4)
1. Implement multi-tiered dataset loading (Phase 1)
2. Add vf-eval integration tests (Phase 2)
3. Update environment READMEs with Hub examples
4. Test deployment to Hub with one environment

### Medium-term (Weeks 5-8)
1. Deploy all production-ready environments (E1, E2) to Hub
2. Create comprehensive Hub deployment guide
3. Add automated Hub deployment validation
4. Document troubleshooting procedures

### Long-term (Ongoing)
1. Monitor Hub deployments for issues
2. Gather user feedback on vf-eval experience
3. Optimize dataset loading performance
4. Integrate with Prime RL training workflows

## Conclusion

The Open Security Verifiers repository is **already highly compatible** with Prime Intellect's Environments Hub. The package structure, entry points, and environment interfaces follow all required conventions.

**Key Strengths:**
- ✅ Correct package structure and entry points
- ✅ Standard `load_environment()` interface
- ✅ Build and deployment infrastructure in place
- ✅ vf-eval examples documented

**Minimal Work Required:**
- ⚠️ Implement multi-tiered dataset loading
- ⚠️ Add vf-eval integration tests
- ⚠️ Validate Hub deployment workflow

With the implementation plan outlined above, full Hub compatibility can be achieved in **2-4 weeks** of focused development.

## References

- [Prime Intellect Verifiers Library](https://github.com/PrimeIntellect-ai/verifiers)
- [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments)
- [Prime Intellect Documentation](https://docs.primeintellect.ai/)
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli)
- [Verifiers Documentation](https://verifiers.readthedocs.io/)
- [Environments Hub Blog Post](https://www.primeintellect.ai/blog/environments)
