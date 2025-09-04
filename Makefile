# Makefile for Open Security Verifiers
# A composable suite of security and alignment RL environments

.PHONY: help setup venv install install-dev install-all test lint format check build deploy clean docs

# Default Python version
PYTHON := python3.12
VENV := .venv
ACTIVATE := source $(VENV)/bin/activate

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(GREEN)Open Security Verifiers - Development Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup:$(NC)"
	@echo "  make setup          - Complete setup (venv + all deps)"
	@echo "  make venv           - Create Python virtual environment"
	@echo "  make install        - Install all environments in editable mode"
	@echo "  make install-dev    - Install development tools"
	@echo ""
	@echo "$(YELLOW)Quality:$(NC)"
	@echo "  make test           - Run all tests"
	@echo "  make test-env E=x   - Test specific environment (e.g., E=network-logs)"
	@echo "  make lint           - Run linter checks"
	@echo "  make format         - Auto-format code"
	@echo "  make check          - Run all quality checks (lint + test)"
	@echo ""
	@echo "$(YELLOW)Building:$(NC)"
	@echo "  make build          - Build all environment wheels"
	@echo "  make build-env E=x  - Build specific environment wheel"
	@echo ""
	@echo "$(YELLOW)Deployment:$(NC)"
	@echo "  make deploy E=x     - Deploy environment to Hub (requires prime login)"
	@echo "  make eval E=x       - Evaluate environment locally"
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@echo "  make clean          - Remove build artifacts and caches"
	@echo "  make docs           - Serve documentation locally"
	@echo "  make pre-commit     - Install and run pre-commit hooks"
	@echo ""
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@echo "  E=network-logs      - Target specific environment"
	@echo "  MODEL=gpt-4o-mini   - Model for evaluation"
	@echo "  N=10                - Number of examples for eval"

# Complete setup
setup: venv install install-dev
	@echo "$(GREEN)✓ Setup complete! Activate with: source $(VENV)/bin/activate$(NC)"

# Create virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Creating virtual environment...$(NC)"; \
		uv venv --python=$(PYTHON); \
	else \
		echo "$(GREEN)✓ Virtual environment already exists$(NC)"; \
	fi

# Install all environments in editable mode
install: venv
	@echo "$(YELLOW)Installing all environments...$(NC)"
	@$(ACTIVATE) && \
	for env in environments/*/; do \
		echo "Installing $${env}..."; \
		cd "$${env}" && uv sync && cd ../..; \
		uv pip install -e "$${env}"; \
	done
	@echo "$(GREEN)✓ All environments installed$(NC)"

# Install development tools
install-dev: venv
	@echo "$(YELLOW)Installing development tools...$(NC)"
	@$(ACTIVATE) && uv pip install pytest pytest-cov ruff build pre-commit verifiers prime
	@echo "$(GREEN)✓ Development tools installed$(NC)"

# Install everything (alias)
install-all: setup

# Run all tests
test: venv
	@echo "$(YELLOW)Running all tests...$(NC)"
	@$(ACTIVATE) && uv run pytest -q
	@echo "$(GREEN)✓ All tests passed$(NC)"

# Test specific environment
test-env: venv
	@if [ -z "$(E)" ]; then \
		echo "$(RED)Error: Specify environment with E=name$(NC)"; \
		echo "Example: make test-env E=network-logs"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Testing sv-env-$(E)...$(NC)"
	@$(ACTIVATE) && uv run pytest environments/sv-env-$(E)/ -q
	@echo "$(GREEN)✓ Tests passed for sv-env-$(E)$(NC)"

# Test with coverage
test-cov: venv
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	@$(ACTIVATE) && uv run pytest --cov=environments --cov-report=term-missing

# Run linter
lint: venv
	@echo "$(YELLOW)Running linter...$(NC)"
	@$(ACTIVATE) && uv run ruff check .

# Fix linting issues
lint-fix: venv
	@echo "$(YELLOW)Fixing linting issues...$(NC)"
	@$(ACTIVATE) && uv run ruff check . --fix
	@echo "$(GREEN)✓ Linting issues fixed$(NC)"

# Format code
format: venv
	@echo "$(YELLOW)Formatting code...$(NC)"
	@$(ACTIVATE) && uv run ruff format .
	@echo "$(GREEN)✓ Code formatted$(NC)"

# Run all quality checks
check: lint format test
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

# Build all environment wheels
build: venv
	@echo "$(YELLOW)Building all environment wheels...$(NC)"
	@$(ACTIVATE) && \
	for env in environments/*/; do \
		echo "Building $${env}..."; \
		cd "$${env}" && uv run python -m build --wheel && cd ../..; \
	done
	@echo "$(GREEN)✓ All wheels built$(NC)"

# Build specific environment wheel
build-env: venv
	@if [ -z "$(E)" ]; then \
		echo "$(RED)Error: Specify environment with E=name$(NC)"; \
		echo "Example: make build-env E=network-logs"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Building sv-env-$(E) wheel...$(NC)"
	@$(ACTIVATE) && cd environments/sv-env-$(E) && uv run python -m build --wheel
	@echo "$(GREEN)✓ Wheel built for sv-env-$(E)$(NC)"

# Deploy environment to Hub
deploy: venv
	@if [ -z "$(E)" ]; then \
		echo "$(RED)Error: Specify environment with E=name$(NC)"; \
		echo "Example: make deploy E=network-logs"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Deploying sv-env-$(E) to Environments Hub...$(NC)"
	@$(ACTIVATE) && cd environments/sv-env-$(E) && \
		uv run python -m build --wheel && \
		prime login && \
		prime env push -v PUBLIC
	@echo "$(GREEN)✓ sv-env-$(E) deployed to Hub$(NC)"

# Evaluate environment locally
eval: venv
	@if [ -z "$(E)" ]; then \
		echo "$(RED)Error: Specify environment with E=name$(NC)"; \
		echo "Example: make eval E=network-logs MODEL=gpt-4o-mini N=10"; \
		exit 1; \
	fi
	@MODEL=$${MODEL:-gpt-4o-mini}; \
	N=$${N:-10}; \
	echo "$(YELLOW)Evaluating sv-env-$(E) with $$MODEL ($$N examples)...$(NC)"; \
	$(ACTIVATE) && vf-eval intertwine/sv-env-$(E) \
		--model $$MODEL \
		--num-examples $$N

# Install and run pre-commit hooks
pre-commit: venv
	@echo "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	@$(ACTIVATE) && uv run pre-commit install
	@$(ACTIVATE) && uv run pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit hooks installed and run$(NC)"

# Clean build artifacts and caches
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf environments/*/dist/
	@rm -rf environments/*/build/
	@rm -rf environments/*/*.egg-info/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Build artifacts cleaned$(NC)"

# Deep clean (including venv)
clean-all: clean
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf $(VENV)
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# Serve documentation
docs: venv
	@echo "$(YELLOW)Starting documentation server...$(NC)"
	@echo "$(RED)Note: Documentation server not yet configured$(NC)"
	@echo "View project docs at:"
	@echo "  - EXECUTIVE_SUMMARY.md"
	@echo "  - PRD.md"
	@echo "  - CONTRIBUTING.md"

# Environment-specific shortcuts
.PHONY: e1 e2 e3 e4 e5 e6

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

# Quick commands for common workflows
.PHONY: quick-test quick-fix quick-check

quick-test:
	@$(MAKE) test

quick-fix:
	@$(MAKE) lint-fix format

quick-check:
	@$(MAKE) check

# CI/CD targets
.PHONY: ci cd

ci: venv
	@echo "$(YELLOW)Running CI checks...$(NC)"
	@$(ACTIVATE) && uv run ruff check . --exit-non-zero-on-fix
	@$(ACTIVATE) && uv run pytest -q --tb=short
	@echo "$(GREEN)✓ CI checks passed$(NC)"

cd: ci build
	@echo "$(GREEN)✓ Ready for deployment$(NC)"

# Development workflow helpers
.PHONY: dev watch

dev: venv
	@echo "$(YELLOW)Starting development mode...$(NC)"
	@echo "Virtual environment: $(VENV)"
	@echo "Run 'source $(VENV)/bin/activate' to activate"
	@echo ""
	@echo "Quick commands:"
	@echo "  make test       - Run tests"
	@echo "  make lint-fix   - Fix linting issues"
	@echo "  make format     - Format code"
	@echo "  make check      - Run all checks"

# Watch for changes (requires entr)
watch:
	@command -v entr >/dev/null 2>&1 || { echo "$(RED)entr not installed. Install with: brew install entr$(NC)"; exit 1; }
	@echo "$(YELLOW)Watching for changes...$(NC)"
	@find . -name "*.py" | entr -c make test

# Print environment info
.PHONY: info

info:
	@echo "$(GREEN)Open Security Verifiers - Environment Info$(NC)"
	@echo ""
	@echo "Python: $(PYTHON)"
	@echo "Virtual Environment: $(VENV)"
	@echo ""
	@echo "Environments:"
	@for env in environments/*/; do \
		basename=$$(basename $$env); \
		if [ -f "$$env/dist/*.whl" ] 2>/dev/null; then \
			echo "  ✓ $$basename (built)"; \
		else \
			echo "  ○ $$basename"; \
		fi; \
	done
	@echo ""
	@if [ -d "$(VENV)" ]; then \
		echo "Status: $(GREEN)Ready$(NC)"; \
	else \
		echo "Status: $(YELLOW)Run 'make setup' to get started$(NC)"; \
	fi