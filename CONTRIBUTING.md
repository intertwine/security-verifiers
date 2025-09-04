# Contributing to Open Security Verifiers

Welcome to the Open Security Verifiers project! We're building a composable suite of security and alignment RL environments for Prime Intellect's Environments Hub. Your contributions help advance verifiable, executable rewards for AI safety and security research.

## Project Vision

This project implements six composable RL environments with shared tooling and evaluation methods, emphasizing:

- **Executable verification** (tests, policy engines, linters) over LLM judges
- **Calibration and abstention** for operational deployment
- **Asymmetric cost functions** reflecting real security priorities
- **Cross-task skill transfer** through shared schemas and rewards

See [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) and [PRD.md](PRD.md) for the complete vision.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [Prime CLI](https://github.com/PrimeIntellect-ai/prime-cli) (for Hub deployment)
- Git for version control

## Development Setup

### 1. Clone and Initialize

```bash
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers
```

### 2. Create Virtual Environment

```bash
uv venv --python=python3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all environments in editable mode
for env in environments/*/; do
    cd "$env" && uv sync && cd ../..
    uv pip install -e "$env"
done

# Install development tools
uv pip install pytest ruff build pre-commit verifiers prime
```

### 4. Set Up Pre-commit Hooks (Recommended)

```bash
uv run pre-commit install
```

## Development Workflow

### Code Quality

```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Run pre-commit on all files
uv run pre-commit run --all-files
```

### Testing

```bash
# Run all tests
uv run pytest

# Test specific environment
uv run pytest environments/sv-env-network-logs/

# Run tests with coverage
uv run pytest --cov=environments --cov-report=term-missing
```

### Building Environments

```bash
# Build wheel for deployment
cd environments/sv-env-network-logs
uv run python -m build --wheel

# Push to Environments Hub
prime login
prime env push -v PUBLIC
```

## Contributing Guidelines

### Environment Development

When creating or modifying environments:

1. **Follow the PRD specifications**: Each environment has detailed specs in [PRD.md](PRD.md)
2. **Use shared components**: Leverage the common toolbox (schemas, rewards, verifiers)
3. **Implement proper interfaces**:
   - `load_environment()` entry point
   - Strict JSON output schemas
   - Calibration/abstention support where specified
4. **Add comprehensive tests**: Include unit tests and integration tests
5. **Document thoroughly**: Update READMEs with examples and usage

### Code Style

- Follow PEP 8 and use type hints
- Keep functions focused and testable
- Use descriptive variable names
- Add docstrings to all public functions
- Ensure rewards are normalized to [0.0, 1.0]

### Reward Design Principles

1. **Executable verification first**: Use tests, linters, policy engines
2. **Format compliance**: Zero reward for malformed outputs
3. **Calibration bonuses**: Reward well-calibrated confidence
4. **Asymmetric costs**: Reflect operational priorities (FN >> FP for security)
5. **Abstention support**: Allow safe "I don't know" responses

### Pull Request Process

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make focused changes**: One feature/fix per PR
3. **Write/update tests**: Ensure all tests pass
4. **Update documentation**: Including environment READMEs if needed
5. **Run quality checks**: `ruff`, `pytest`, `pre-commit`
6. **Submit PR with clear description**: Reference relevant PRD sections

### Commit Message Format

```markdown
type: Brief description

- Detailed change 1
- Detailed change 2

Refs: #issue-number
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

## Environment-Specific Guidelines

### Network Logs (E1)

- Focus on calibration and abstention mechanics
- Test with IoT-23, CIC-IDS-2017, UNSW-NB15 datasets
- Implement bin reliability for calibration scoring

### Config Auditing (E2)

- Integrate OPA/Rego, KubeLinter, Semgrep tools
- Provide tool wrappers with clear interfaces
- Test against real K8s/Terraform configs

### Code Vulnerability (E3)

- Implement sandboxed test execution
- Track coverage to ensure patch quality
- Use Devign/Big-Vul/CVEfixes datasets

### Phishing Detection (E4)

- Support evidence extraction
- Implement URL/domain reputation tools
- Cross-corpus OOD evaluation

### Attack/Defense (E5/E6)

- Integrate Llama Guard 3 for safety scoring
- Support co-training infrastructure
- Use JailbreakBench/HarmBench benchmarks

## Security Considerations

- **Never commit secrets**: API keys, tokens, passwords
- **Sanitize datasets**: Hash/remove sensitive content
- **Sandbox execution**: For code evaluation environments
- **Rate limit API calls**: Respect service limits

## Community

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)
- **Discussions**: Join conversations about design and research
- **Hub**: Share environments on [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments)

## License

This project is released under MIT License to maximize reuse and contribution. See [LICENSE](LICENSE) for details.

## Acknowledgments

Built on [Prime Intellect's Verifiers](https://github.com/willccbb/verifiers) framework and designed for the [Environments Hub](https://app.primeintellect.ai/dashboard/environments). Special thanks to the Prime Intellect team for creating the infrastructure that makes this work possible.

---

By contributing, you agree to abide by our code of conduct and license terms. Thank you for helping build verifiable security AI!
