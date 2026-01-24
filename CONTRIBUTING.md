# Contributing to Security Verifiers

Thank you for your interest in contributing! This guide covers the essentials for contributing to the project.

## Quick Start

```bash
git clone https://github.com/intertwine/security-verifiers.git
cd security-verifiers
make setup && source .venv/bin/activate
make pre-commit  # Install git hooks
```

See [docs/development.md](docs/development.md) for detailed setup instructions.

## Development Workflow

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make focused changes**: One feature/fix per PR
3. **Run quality checks**:
   ```bash
   make check  # lint + format + tests
   ```
4. **Update documentation** if needed
5. **Submit PR** with a clear description

## Code Style

- Follow PEP 8 with type hints
- Keep functions focused and testable
- Use descriptive variable names
- Add docstrings to public functions

## Environment Development

When modifying environments:

1. **Use shared components** from `sv_shared/` (parsers, rewards, utilities)
2. **Implement proper interfaces**: `load_environment()` entry point
3. **Add comprehensive tests**
4. **Update environment README**

### Reward Design Principles

- **Executable verification first**: Use tests, linters, policy engines over LLM judges
- **Format compliance**: Zero reward for malformed outputs
- **Calibration bonuses**: Reward well-calibrated confidence
- **Asymmetric costs**: Reflect operational priorities (FN >> FP)
- **Abstention support**: Allow safe "I don't know" responses

## Commit Messages

```
type: Brief description

- Detailed change 1
- Detailed change 2

Refs: #issue-number
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

## Security

- Never commit secrets (API keys, tokens)
- Sanitize datasets
- Use sandboxed execution for code evaluation

## Getting Help

- [GitHub Issues](https://github.com/intertwine/security-verifiers/issues)
- [Development Guide](docs/development.md)
- [CLAUDE.md](CLAUDE.md) for command reference

## License

MIT License - see [LICENSE](LICENSE).
