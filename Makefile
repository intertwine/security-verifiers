# Makefile for Open Security Verifiers
# A composable suite of security and alignment RL environments

SHELL := /bin/bash

# Phony targets
.PHONY: \
help setup venv install install-dev install-all install-linux check-tools \
\
test test-env test-cov lint lint-fix format check quick-test quick-fix quick-check \
\
build build-env deploy ci cd \
\
eval eval-e1 eval-e2 e1 e2 e3 e4 e5 e6 \
\
data-e1 data-e1-ood data-e1-test data-e2 data-e2-local data-e2-test data-all data-test-all clone-e2-sources \
hf-e1-meta hf-e2-meta hf-e1-push hf-e2-push hf-e1p-meta hf-e2p-meta hf-e1p-push hf-e2p-push hf-push-all \
validate-e1-data validate-e2-data validate-data hf-e1p-push-canonical hf-e2p-push-canonical hf-e1p-push-canonical-dry hf-e2p-push-canonical-dry \
\
pre-commit clean clean-outputs clean-logs clean-outputs-all clean-all docs info dev watch

# Default Python version
PYTHON := python3.12
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate

# Ensure uv uses Python 3.12 for all operations
export UV_PYTHON := python3.12

# ---------- Colors (portable) ----------
# Use NO_COLOR=1 to disable
ifdef NO_COLOR
RED :=
GREEN :=
YELLOW :=
NC :=
else
ESC := $(shell printf '\033')
RED := $(ESC)[0;31m
GREEN := $(ESC)[0;32m
YELLOW := $(ESC)[1;33m
NC := $(ESC)[0m
endif
ECHO = printf "%b\n"

# Default target
help:
	@$(ECHO) "$(GREEN)Open Security Verifiers - Development Commands$(NC)"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Setup:$(NC)"
	@$(ECHO) "  make setup          - Complete setup (venv + all deps)"
	@$(ECHO) "  make venv           - Create Python virtual environment"
	@$(ECHO) "  make install        - Install all environments in editable mode"
	@$(ECHO) "  make install-dev    - Install development tools"
	@$(ECHO) "  make install-all    - Install everything (alias)"
	@$(ECHO) "  make install-linux  - Install pinned security tools (Ubuntu 24)"
	@$(ECHO) "  make check-tools    - Check if app tools match pinned versions"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Quality:$(NC)"
	@$(ECHO) "  make test           - Run all tests"
	@$(ECHO) "  make test-env E=x   - Test specific environment (e.g., E=network-logs)"
	@$(ECHO) "  make lint           - Run linter checks"
	@$(ECHO) "  make format         - Auto-format code"
	@$(ECHO) "  make check          - Run all quality checks (lint + test)"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Building:$(NC)"
	@$(ECHO) "  make build          - Build all environment wheels"
	@$(ECHO) "  make build-env E=x  - Build specific environment wheel"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Deployment:$(NC)"
	@$(ECHO) "  make deploy E=x     - Deploy environment to Hub (requires prime login)"
	@$(ECHO) "  make eval E=x       - Evaluate environment locally"
	@$(ECHO) "  make eval-e1 MODELS=... N=10                     - Reproducible E1 evals (network-logs)"
	@$(ECHO) "  make eval-e2 MODELS=... N=2 INCLUDE_TOOLS=true  - Reproducible E2 evals (config-verification)"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Data Building (Production - Private):$(NC)"
	@$(ECHO) "  make data-e1        - Build E1 IoT-23 dataset (LIMIT=1800, full mode)"
	@$(ECHO) "  make data-e1-ood    - Build E1 OOD datasets (CIC, UNSW; N=600, full mode)"
	@$(ECHO) "  make clone-e2-sources - Clone K8s/TF repositories for E2"
	@$(ECHO) "  make data-e2        - Build E2 K8s/TF datasets (requires K8S_ROOT, TF_ROOT, full mode)"
	@$(ECHO) "  make data-e2-local  - Build E2 using cloned sources (run clone-e2-sources first)"
	@$(ECHO) "  make data-all       - Build all production datasets"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Data Building (Test Fixtures - Committed):$(NC)"
	@$(ECHO) "  make data-e1-test   - Build E1 test fixtures for CI (small, checked in)"
	@$(ECHO) "  make data-e2-test   - Build E2 test fixtures for CI (small, checked in)"
	@$(ECHO) "  make data-test-all  - Build all test fixtures for CI"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)HuggingFace Flat Metadata Schema (Dataset Viewer):$(NC)"
	@$(ECHO) "  make hf-e1-meta     - Build E1 metadata (flat schema) locally"
	@$(ECHO) "  make hf-e2-meta     - Build E2 metadata (flat schema) locally"
	@$(ECHO) "  make hf-e1-push     - Push E1 metadata to PUBLIC repo (HF_ORG=intertwine-ai)"
	@$(ECHO) "  make hf-e2-push     - Push E2 metadata to PUBLIC repo (HF_ORG=intertwine-ai)"
	@$(ECHO) "  make hf-e1p-push    - Push E1 metadata to PRIVATE repo (meta split only)"
	@$(ECHO) "  make hf-e2p-push    - Push E2 metadata to PRIVATE repo (meta split only)"
	@$(ECHO) "  make hf-push-all    - Push all metadata to all repos (public + private)"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Data Validation & Canonical Push (HF Features):$(NC)"
	@$(ECHO) "  make validate-data            - Validate E1 & E2 canonical splits (Pydantic)"
	@$(ECHO) "  make hf-e1p-push-canonical    - Push E1 canonical with Features (PRIVATE)"
	@$(ECHO) "  make hf-e2p-push-canonical    - Push E2 canonical with Features (PRIVATE)"
	@$(ECHO) "  make hf-e1p-push-canonical-dry - Dry run E1 canonical push"
	@$(ECHO) "  make hf-e2p-push-canonical-dry - Dry run E2 canonical push"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Utilities:$(NC)"
	@$(ECHO) "  make clean          - Remove build artifacts and caches"
	@$(ECHO) "  make clean-outputs  - Remove outputs/evals artifacts (preserve outputs/logs)"
	@$(ECHO) "  make clean-logs     - Remove outputs/logs artifacts only"
	@$(ECHO) "  make clean-outputs-all - Remove all outputs (evals + logs), keep outputs/.gitkeep"
	@$(ECHO) "  make docs           - Serve documentation locally"
	@$(ECHO) "  make pre-commit     - Install and run pre-commit hooks"
	@$(ECHO) ""
	@$(ECHO) "$(YELLOW)Environment Variables:$(NC)"
	@$(ECHO) "  E=network-logs             - Target specific environment"
	@$(ECHO) "  MODEL=gpt-5-mini          - Model for evaluation"
	@$(ECHO) "  N=10                       - Number of examples for eval"
	@$(ECHO) "  MAX_CONSECUTIVE_ERRORS=3   - Error threshold (default: 3, 0 to disable)"
	@$(ECHO) "  LIMIT=1800                 - Total rows for E1 dataset"
	@$(ECHO) "  K8S_ROOT=path              - Kubernetes YAML directory for E2"
	@$(ECHO) "  TF_ROOT=path               - Terraform HCL directory for E2"

# Complete setup
setup: venv install install-dev
	@$(ECHO) "$(GREEN)✓ Setup complete! Activate with: source $(VENV)/bin/activate$(NC)"

# Create virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		$(ECHO) "$(YELLOW)Creating virtual environment...$(NC)"; \
		uv venv --python=$(PYTHON); \
	else \
		$(ECHO) "$(GREEN)✓ Virtual environment already exists$(NC)"; \
	fi

# Install all environments in editable mode (Ubuntu/macOS safe)
install: venv
	@$(ECHO) "$(YELLOW)Installing all environments...$(NC)"
	@$(ACTIVATE) && \
	for env in environments/sv-env-*/; do \
		$(ECHO) "Installing $$env..."; \
		( cd "$$env" && uv sync ); \
		uv pip install -e "$$env"; \
	done
	@$(ECHO) "$(GREEN)✓ All environments installed$(NC)"

# Install development tools
install-dev: venv
	@$(ECHO) "$(YELLOW)Installing development tools...$(NC)"
	@$(ACTIVATE) && uv pip install pytest pytest-cov ruff build pre-commit verifiers prime
	@$(ECHO) "$(GREEN)✓ Development tools installed$(NC)"

# Install everything (alias)
install-all: setup

# Install for linux systems (pipx kubelinter opa semgrep)
install-linux:
	@$(ECHO) "$(YELLOW)Installing pinned security tools (Ubuntu 24)...$(NC)"
	@set -e; \
	VFILE="environments/sv-env-config-verification/ci/versions.txt"; \
	OPA_VER=$$(grep '^OPA_VERSION=' $$VFILE | cut -d= -f2); \
	KL_VER=$$(grep '^KUBELINTER_VERSION=' $$VFILE | cut -d= -f2); \
	SG_VER=$$(grep '^SEMGREP_VERSION=' $$VFILE | cut -d= -f2); \
	\
	echo "Checking pipx..."; \
	if ! command -v pipx >/dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y pipx; \
		pipx ensurepath; \
	fi; \
	\
	echo "Installing kube-linter v$$KL_VER..."; \
	curl -sSL https://github.com/stackrox/kube-linter/releases/download/v$$KL_VER/kube-linter-linux.tar.gz \
		| sudo tar -xz -C /usr/local/bin kube-linter; \
	\
	echo "Installing opa v$$OPA_VER..."; \
	curl -sSL -o /tmp/opa https://openpolicyagent.org/downloads/v$$OPA_VER/opa_linux_amd64_static; \
	sudo mv /tmp/opa /usr/local/bin/opa; \
	sudo chmod +x /usr/local/bin/opa; \
	\
	echo "Installing semgrep v$$SG_VER..."; \
	pipx install "semgrep==$$SG_VER" --force; \
	\
	$(MAKE) check-tools

# Check if app tools match the pinned version in versions.txt
check-tools:
	@set -e; \
	VFILE="environments/sv-env-config-verification/ci/versions.txt"; \
	OPA_VER=$$(grep '^OPA_VERSION=' $$VFILE | cut -d= -f2); \
	KL_VER=$$(grep '^KUBELINTER_VERSION=' $$VFILE | cut -d= -f2); \
	SG_VER=$$(grep '^SEMGREP_VERSION=' $$VFILE | cut -d= -f2); \
	\
	OPA_ACTUAL=$$(opa version | grep -oE 'Version: *[0-9]+\.[0-9]+\.[0-9]+' | awk '{print $$2}'); \
	KL_ACTUAL=$$(kube-linter version); \
	SG_ACTUAL=$$(semgrep --version); \
	echo "OPA: expected $$OPA_VER, got $$OPA_ACTUAL"; \
	echo "kube-linter: expected $$KL_VER, got $$KL_ACTUAL"; \
	echo "semgrep: expected $$SG_VER, got $$SG_ACTUAL"; \
	if [ "$$OPA_VER" != "$$OPA_ACTUAL" ] || [ "$$KL_VER" != "$$KL_ACTUAL" ] || [ "$$SG_VER" != "$$SG_ACTUAL" ]; then \
		echo "$(RED)✗ Version mismatch detected$(NC)"; exit 1; \
	else \
		$(ECHO) "$(GREEN)✓ All security tools match pinned versions$(NC)"; \
	fi


# Run all tests
test: venv
	@$(ECHO) "$(YELLOW)Running all tests...$(NC)"
	@$(ACTIVATE) && uv run pytest -q
	@$(ECHO) "$(GREEN)✓ All tests passed$(NC)"

# Test specific environment
test-env: venv
	@if [ -z "$(E)" ]; then \
		$(ECHO) "$(RED)Error: Specify environment with E=name$(NC)"; \
		$(ECHO) "Example: make test-env E=network-logs"; \
		exit 1; \
	fi
	@$(ECHO) "$(YELLOW)Testing sv-env-$(E)...$(NC)"
	@$(ACTIVATE) && uv run pytest environments/sv-env-$(E)/ -q
	@$(ECHO) "$(GREEN)✓ Tests passed for sv-env-$(E)$(NC)"

# Test with coverage
test-cov: venv
	@$(ECHO) "$(YELLOW)Running tests with coverage...$(NC)"
	@$(ACTIVATE) && uv run pytest --cov=environments --cov-report=term-missing

# Run linter
lint: venv
	@$(ECHO) "$(YELLOW)Running linter...$(NC)"
	@$(ACTIVATE) && uv run ruff check .

# Fix linting issues
lint-fix: venv
	@$(ECHO) "$(YELLOW)Fixing linting issues...$(NC)"
	@$(ACTIVATE) && uv run ruff check . --fix
	@$(ECHO) "$(GREEN)✓ Linting issues fixed$(NC)"

# Format code
format: venv
	@$(ECHO) "$(YELLOW)Formatting code...$(NC)"
	@$(ACTIVATE) && uv run ruff format .
	@$(ECHO) "$(GREEN)✓ Code formatted$(NC)"

# Run all quality checks
check: lint format test
	@$(ECHO) "$(GREEN)✓ All quality checks passed$(NC)"

# Build all environment wheels
build: venv install-dev
	@$(ECHO) "$(YELLOW)Building all environment wheels...$(NC)"
	@$(ACTIVATE) && \
	for env in environments/sv-env-*/; do \
		$(ECHO) "Building $$env..."; \
		( cd "$$env" && python -m build --wheel ); \
	done
	@$(ECHO) "$(GREEN)✓ All wheels built$(NC)"

# Build specific environment wheel
build-env: venv install-dev
	@if [ -z "$(E)" ]; then \
		$(ECHO) "$(RED)Error: Specify environment with E=name$(NC)"; \
		$(ECHO) "Example: make build-env E=network-logs"; \
		exit 1; \
	fi
	@$(ECHO) "$(YELLOW)Building sv-env-$(E) wheel...$(NC)"
	@$(ACTIVATE) && ( cd environments/sv-env-$(E) && python -m build --wheel )
	@$(ECHO) "$(GREEN)✓ Wheel built for sv-env-$(E)$(NC)"

# Deploy environment to Hub
deploy: venv install-dev
	@if [ -z "$(E)" ]; then \
		$(ECHO) "$(RED)Error: Specify environment with E=name$(NC)"; \
		$(ECHO) "Example: make deploy E=network-logs"; \
		exit 1; \
	fi
	@$(ECHO) "$(YELLOW)Deploying sv-env-$(E) to Environments Hub...$(NC)"
	@$(ACTIVATE) && ( cd environments/sv-env-$(E) && \
		python -m build --wheel && \
		prime login && \
		prime env push -v PUBLIC )
	@$(ECHO) "$(GREEN)✓ sv-env-$(E) deployed to Hub$(NC)"

# Evaluate environment locally
eval: venv
	@if [ -z "$(E)" ]; then \
		$(ECHO) "$(RED)Error: Specify environment with E=name$(NC)"; \
		$(ECHO) "Example: make eval E=network-logs MODEL=gpt-5-mini N=10"; \
		exit 1; \
	fi
	@MODEL=$${MODEL:-gpt-5-mini}; \
	N=$${N:-10}; \
	$(ECHO) "$(YELLOW)Evaluating sv-env-$(E) with $$MODEL ($$N examples)...$(NC)"; \
	$(ACTIVATE) && vf-eval intertwine/sv-env-$(E) --model $$MODEL --num-examples $$N

# Install and run pre-commit hooks
pre-commit: venv
	@$(ECHO) "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	@$(ACTIVATE) && uv run pre-commit install
	@$(ACTIVATE) && uv run pre-commit run --all-files
	@$(ECHO) "$(GREEN)✓ Pre-commit hooks installed and run$(NC)"

# Clean build artifacts and caches
clean:
	@$(ECHO) "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf environments/*/dist/ environments/*/build/ environments/*/*.egg-info/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@$(ECHO) "$(GREEN)✓ Build artifacts cleaned$(NC)"

# Clean evaluation artifacts while keeping logs
clean-outputs:
	@$(ECHO) "$(YELLOW)Cleaning outputs/evals (preserving outputs/logs)...$(NC)"
	@mkdir -p outputs
	@touch outputs/.gitkeep
	@rm -rf outputs/evals/* 2>/dev/null || true
	@$(ECHO) "$(GREEN)✓ outputs/evals cleaned$(NC)"

# Clean only logs
clean-logs:
	@$(ECHO) "$(YELLOW)Cleaning outputs/logs...$(NC)"
	@mkdir -p outputs/logs
	@rm -rf outputs/logs/* 2>/dev/null || true
	@touch outputs/.gitkeep
	@$(ECHO) "$(GREEN)✓ outputs/logs cleaned$(NC)"

# Clean everything under outputs/ while preserving the placeholder
clean-outputs-all:
	@$(ECHO) "$(YELLOW)Cleaning all outputs (evals + logs)...$(NC)"
	@mkdir -p outputs
	@rm -rf outputs/* 2>/dev/null || true
	@touch outputs/.gitkeep
	@$(ECHO) "$(GREEN)✓ outputs cleared (kept .gitkeep)$(NC)"

# Deep clean (including venv)
clean-all: clean
	@$(ECHO) "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf $(VENV)
	@$(ECHO) "$(GREEN)✓ Deep clean complete$(NC)"

# Serve documentation
docs: venv
	@$(ECHO) "$(YELLOW)Starting documentation server...$(NC)"
	@$(ECHO) "$(RED)Note: Documentation server not yet configured$(NC)"
	@$(ECHO) "View project docs at:"
	@$(ECHO) "  - EXECUTIVE_SUMMARY.md"
	@$(ECHO) "  - PRD.md"
	@$(ECHO) "  - CONTRIBUTING.md"

# Environment-specific shortcuts
e1:
	@$(MAKE) test-env E=network-logs
e2:
	@$(MAKE) test-env E=config-verification
e3:
	@$(MAKE) test-env E=code-vulnerability
e4:
	@$(MAKE) test-env E=phishing-detection
e5:
	@$(MAKE) test-env E=redteam-attack
e6:
	@$(MAKE) test-env E=redteam-defense

# Default error threshold for evaluations
MAX_CONSECUTIVE_ERRORS ?= 3

# E1/E2 eval helpers
eval-e1: venv
	@if [ -z "$(MODELS)" ]; then \
		$(ECHO) "$(RED)Error: Provide MODELS=\"gpt-5-mini,gpt-5-mini\"$(NC)"; \
		exit 1; \
	fi
	@N=$${N:-10}; \
	DATASET=$${DATASET:-iot23-train-dev-test-v1.jsonl}; \
	MAX_ERRORS=$${MAX_CONSECUTIVE_ERRORS:-3}; \
	$(ECHO) "$(YELLOW)Evaluating E1 (network-logs) for models: $(MODELS) (N=$$N, dataset=$$DATASET, max_errors=$$MAX_ERRORS)$(NC)"; \
	$(ACTIVATE) && set -a && source .env && set +a && \
	python scripts/eval_network_logs.py --models "$(MODELS)" --num-examples $$N --dataset "$$DATASET" --max-consecutive-errors $$MAX_ERRORS

eval-e2: venv
	@if [ -z "$(MODELS)" ]; then \
		$(ECHO) "$(RED)Error: Provide MODELS=\"gpt-5-mini,gpt-5-mini\"$(NC)"; \
		exit 1; \
	fi
	@N=$${N:-2}; \
	DATASET=$${DATASET:-combined}; \
	INCLUDE_TOOLS=$${INCLUDE_TOOLS:-true}; \
	MAX_ERRORS=$${MAX_CONSECUTIVE_ERRORS:-3}; \
	$(ECHO) "$(YELLOW)Evaluating E2 (config-verification) for models: $(MODELS) (N=$$N, dataset=$$DATASET, INCLUDE_TOOLS=$$INCLUDE_TOOLS, max_errors=$$MAX_ERRORS)$(NC)"; \
	$(ACTIVATE) && set -a && source .env && set +a && \
	python scripts/eval_config_verification.py --models "$(MODELS)" --num-examples $$N --dataset "$$DATASET" --include-tools $$INCLUDE_TOOLS --max-consecutive-errors $$MAX_ERRORS

# Data building targets (production - private, not committed)
data-e1: venv
	@LIMIT=$${LIMIT:-1800}; \
	HF_ID=$${HF_ID:-19kmunz/iot-23-preprocessed}; \
	$(ECHO) "$(YELLOW)Building E1 IoT-23 dataset (LIMIT=$$LIMIT)...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e1_iot23.py --limit $$LIMIT --hf-id "$$HF_ID" --mode full
	@$(ECHO) "$(GREEN)✓ E1 IoT-23 dataset built$(NC)"

data-e1-ood: venv
	@N=$${N:-600}; \
	CIC_ID=$${CIC_ID:-bvk/CICIDS-2017}; \
	UNSW_ID=$${UNSW_ID:-Mireu-Lab/UNSW-NB15}; \
	$(ECHO) "$(YELLOW)Building E1 OOD datasets (N=$$N)...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e1_ood.py --n $$N --cic-id "$$CIC_ID" --unsw-id "$$UNSW_ID" --mode full
	@$(ECHO) "$(GREEN)✓ E1 OOD datasets built$(NC)"

# Test fixtures (small datasets for CI - committed to repo)
data-e1-test: venv
	@$(ECHO) "$(YELLOW)Building E1 test fixtures for CI...$(NC)"; \
	$(ACTIVATE) && set -a && source .env 2>/dev/null && set +a && \
	uv run python scripts/data/build_e1_iot23.py --mode test && \
	uv run python scripts/data/build_e1_ood.py --mode test
	@$(ECHO) "$(GREEN)✓ E1 test fixtures built$(NC)"

# Clone E2 source repositories
clone-e2-sources:
	@$(ECHO) "$(YELLOW)Cloning E2 source repositories...$(NC)"
	@./scripts/data/clone_e2_sources.sh
	@$(ECHO) "$(GREEN)✓ E2 sources cloned to scripts/data/sources/$(NC)"

# Build E2 with custom paths (production)
data-e2: venv
	@if [ -z "$(K8S_ROOT)" ] || [ -z "$(TF_ROOT)" ]; then \
		$(ECHO) "$(RED)Error: Specify K8S_ROOT and TF_ROOT$(NC)"; \
		$(ECHO) "Example: make data-e2 K8S_ROOT=path/to/k8s TF_ROOT=path/to/terraform"; \
		$(ECHO) "Or use: make clone-e2-sources && make data-e2-local"; \
		exit 1; \
	fi
	@REGO_DIR=$${REGO_DIR:-environments/sv-env-config-verification/policies}; \
	PATCHES_DIR=$${PATCHES_DIR}; \
	MODE=$${MODE:-full}; \
	$(ECHO) "$(YELLOW)Building E2 K8s/TF datasets (MODE=$$MODE)...$(NC)"; \
	if [ -n "$$PATCHES_DIR" ]; then \
		$(ACTIVATE) && uv run python scripts/data/build_e2_k8s_tf.py \
			--k8s-root "$(K8S_ROOT)" --tf-root "$(TF_ROOT)" \
			--rego-dir "$$REGO_DIR" --patches-dir "$$PATCHES_DIR" --mode "$$MODE"; \
	else \
		$(ACTIVATE) && uv run python scripts/data/build_e2_k8s_tf.py \
			--k8s-root "$(K8S_ROOT)" --tf-root "$(TF_ROOT)" \
			--rego-dir "$$REGO_DIR" --mode "$$MODE"; \
	fi
	@$(ECHO) "$(GREEN)✓ E2 K8s/TF datasets built$(NC)"

# Build E2 using cloned local sources (production)
data-e2-local: venv
	@if [ ! -d "scripts/data/sources/kubernetes" ] || [ ! -d "scripts/data/sources/terraform" ]; then \
		$(ECHO) "$(RED)Error: Source directories not found$(NC)"; \
		$(ECHO) "Run: make clone-e2-sources first"; \
		exit 1; \
	fi
	@$(MAKE) data-e2 \
		K8S_ROOT=scripts/data/sources/kubernetes \
		TF_ROOT=scripts/data/sources/terraform \
		MODE=full

# Build E2 test fixtures (small datasets for CI)
data-e2-test: venv
	@if [ ! -d "scripts/data/sources/kubernetes" ] || [ ! -d "scripts/data/sources/terraform" ]; then \
		$(ECHO) "$(RED)Error: Source directories not found$(NC)"; \
		$(ECHO) "Run: make clone-e2-sources first"; \
		exit 1; \
	fi
	@$(ECHO) "$(YELLOW)Building E2 test fixtures for CI...$(NC)"; \
	$(MAKE) data-e2 \
		K8S_ROOT=scripts/data/sources/kubernetes \
		TF_ROOT=scripts/data/sources/terraform \
		MODE=test
	@$(ECHO) "$(GREEN)✓ E2 test fixtures built$(NC)"

# Build all production datasets
data-all: data-e1 data-e1-ood
	@$(ECHO) "$(GREEN)✓ All E1 datasets built (E2 requires: make clone-e2-sources && make data-e2-local)$(NC)"

# Build all test fixtures for CI
data-test-all: data-e1-test data-e2-test
	@$(ECHO) "$(GREEN)✓ All test fixtures built for CI$(NC)"

# ========== Flat Metadata Schema Targets (HF Dataset Viewer) ==========
# Build metadata locally (flat schema)
hf-e1-meta: venv
	@$(ECHO) "$(YELLOW)Building E1 metadata (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e1 --out build/hf/e1/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E1 metadata built: build/hf/e1/meta.jsonl$(NC)"

hf-e2-meta: venv
	@$(ECHO) "$(YELLOW)Building E2 metadata (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e2 --out build/hf/e2/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E2 metadata built: build/hf/e2/meta.jsonl$(NC)"

# Push to PUBLIC metadata-only repos
hf-e1-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E1 metadata to PUBLIC repo: $$HF_ORG/security-verifiers-e1-metadata$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e1 --out build/hf/e1/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e1-metadata" --split meta --push
	@$(ECHO) "$(GREEN)✓ E1 metadata pushed to PUBLIC repo$(NC)"

hf-e2-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E2 metadata to PUBLIC repo: $$HF_ORG/security-verifiers-e2-metadata$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e2 --out build/hf/e2/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e2-metadata" --split meta --push
	@$(ECHO) "$(GREEN)✓ E2 metadata pushed to PUBLIC repo$(NC)"

# Push to PRIVATE full dataset repos (only updates meta split)
hf-e1p-meta: venv
	@$(ECHO) "$(YELLOW)Building E1 metadata for PRIVATE repo (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e1 --out build/hf/e1/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E1 metadata built: build/hf/e1/meta.jsonl$(NC)"

hf-e2p-meta: venv
	@$(ECHO) "$(YELLOW)Building E2 metadata for PRIVATE repo (flat schema)...$(NC)"
	@$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e2 --out build/hf/e2/meta.jsonl
	@$(ECHO) "$(GREEN)✓ E2 metadata built: build/hf/e2/meta.jsonl$(NC)"

hf-e1p-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E1 metadata to PRIVATE repo: $$HF_ORG/security-verifiers-e1 (meta split only)$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e1 --out build/hf/e1/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e1" --split meta --push --private
	@$(ECHO) "$(GREEN)✓ E1 metadata pushed to PRIVATE repo (meta split only)$(NC)"

hf-e2p-push: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E2 metadata to PRIVATE repo: $$HF_ORG/security-verifiers-e2 (meta split only)$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/export_metadata_flat.py \
		--env e2 --out build/hf/e2/meta.jsonl \
		--repo "$$HF_ORG/security-verifiers-e2" --split meta --push --private
	@$(ECHO) "$(GREEN)✓ E2 metadata pushed to PRIVATE repo (meta split only)$(NC)"

# Convenience: push all metadata to all repos
hf-push-all: hf-e1-push hf-e2-push hf-e1p-push hf-e2p-push
	@$(ECHO) "$(GREEN)✓ All metadata pushed (public + private repos)$(NC)"

# ========== Pydantic Validators & Canonical Push (with Features) ==========
# Validate canonical splits with Pydantic before pushes
validate-e1-data: venv
	@$(ECHO) "$(YELLOW)Validating E1 canonical splits with Pydantic...$(NC)"
	@$(ACTIVATE) && uv run python scripts/data/validate_splits_e1.py \
		--dir environments/sv-env-network-logs/data
	@$(ECHO) "$(GREEN)✓ E1 validation passed$(NC)"

validate-e2-data: venv
	@$(ECHO) "$(YELLOW)Validating E2 canonical splits with Pydantic...$(NC)"
	@$(ACTIVATE) && uv run python scripts/data/validate_splits_e2.py \
		--dir environments/sv-env-config-verification/data
	@$(ECHO) "$(GREEN)✓ E2 validation passed$(NC)"

validate-data: validate-e1-data validate-e2-data
	@$(ECHO) "$(GREEN)✓ All data validation passed$(NC)"

# Push canonical splits with explicit HF Features (PRIVATE repos only)
hf-e1p-push-canonical: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E1 canonical splits to PRIVATE repo: $$HF_ORG/security-verifiers-e1$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e1 \
		--repo "$$HF_ORG/security-verifiers-e1" \
		--data-dir environments/sv-env-network-logs/data \
		--push
	@$(ECHO) "$(GREEN)✓ E1 canonical splits pushed$(NC)"

hf-e2p-push-canonical: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)Pushing E2 canonical splits to PRIVATE repo: $$HF_ORG/security-verifiers-e2$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e2 \
		--repo "$$HF_ORG/security-verifiers-e2" \
		--data-dir environments/sv-env-config-verification/data \
		--push
	@$(ECHO) "$(GREEN)✓ E2 canonical splits pushed$(NC)"

# Dry run canonical pushes (no --push)
hf-e1p-push-canonical-dry: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)[DRY RUN] E1 canonical splits to $$HF_ORG/security-verifiers-e1$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e1 \
		--repo "$$HF_ORG/security-verifiers-e1" \
		--data-dir environments/sv-env-network-logs/data

hf-e2p-push-canonical-dry: venv
	@HF_ORG=$${HF_ORG:-intertwine-ai}; \
	$(ECHO) "$(YELLOW)[DRY RUN] E2 canonical splits to $$HF_ORG/security-verifiers-e2$(NC)"; \
	$(ACTIVATE) && uv run python scripts/hf/push_canonical_with_features.py \
		--env e2 \
		--repo "$$HF_ORG/security-verifiers-e2" \
		--data-dir environments/sv-env-config-verification/data

# Quick commands
quick-test:
	@$(MAKE) test
quick-fix:
	@$(MAKE) lint-fix format
quick-check:
	@$(MAKE) check

# CI/CD targets
ci: venv
	@$(ECHO) "$(YELLOW)Running CI checks...$(NC)"
	@$(ACTIVATE) && uv run ruff check . --exit-non-zero-on-fix
	@$(ACTIVATE) && uv run pytest -q --tb=short
	@$(ECHO) "$(GREEN)✓ CI checks passed$(NC)"

cd: ci build
	@$(ECHO) "$(GREEN)✓ Ready for deployment$(NC)"

# Development workflow helpers
dev: venv
	@$(ECHO) "$(YELLOW)Starting development mode...$(NC)"
	@$(ECHO) "Virtual environment: $(VENV)"
	@$(ECHO) "Run 'source $(VENV)/bin/activate' to activate"
	@$(ECHO) ""
	@$(ECHO) "Quick commands:"
	@$(ECHO) "  make test       - Run tests"
	@$(ECHO) "  make lint-fix   - Fix linting issues"
	@$(ECHO) "  make format     - Format code"
	@$(ECHO) "  make check      - Run all checks"

# Watch for changes (requires entr)
watch:
	@command -v entr >/dev/null 2>&1 || { \
		$(ECHO) "$(RED)entr not installed.$(NC)"; \
		$(ECHO) "Install with:  $(YELLOW)brew install entr$(NC)  (macOS)  or  $(YELLOW)sudo apt-get install entr$(NC)  (Ubuntu)"; \
		exit 1; \
	}
	@$(ECHO) "$(YELLOW)Watching for changes...$(NC)"
	@find . -name "*.py" | entr -c make test

# Print environment info
info:
	@$(ECHO) "$(GREEN)Open Security Verifiers - Environment Info$(NC)"
	@$(ECHO) ""
	@$(ECHO) "Python: $(PYTHON)"
	@$(ECHO) "Virtual Environment: $(VENV)"
	@$(ECHO) ""
	@$(ECHO) "Environments:"
	@for env in environments/sv-env-*/; do \
		basename=$$(basename $$env); \
		if compgen -G "$$env/dist/*.whl" >/dev/null; then \
			$(ECHO) "  ✓ $$basename (built)"; \
		else \
			$(ECHO) "  ○ $$basename"; \
		fi; \
	done
	@$(ECHO) ""
	@if [ -d "$(VENV)" ]; then \
		$(ECHO) "Status: $(GREEN)Ready$(NC)"; \
	else \
		$(ECHO) "Status: $(YELLOW)Run 'make setup' to get started$(NC)"; \
	fi
