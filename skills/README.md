# Security Verifiers Agent Skills

This directory contains [Agent Skills](https://agentskills.io/) that help AI agents work efficiently with the Security Verifiers repository.

## Available Skills

| Skill | Description |
|-------|-------------|
| `sv-eval` | Run and analyze evaluations for E1/E2 environments |
| `sv-data` | Build and manage datasets (production and test fixtures) |
| `sv-deploy` | Deploy to Environments Hub and publish to PyPI |
| `sv-hf` | Manage HuggingFace dataset repositories |
| `sv-dev` | Development workflow (testing, linting, formatting) |
| `sv-report` | Generate SV-Bench metrics reports (summary.json + report.md) |

## Using Skills

### With Claude Code

Skills are automatically discovered. Ask Claude to help with tasks like:
- "Run an E1 evaluation with gpt-5-mini"
- "Build the E2 dataset from cloned sources"
- "Deploy network-logs to the Environments Hub"
- "Push E1 datasets to HuggingFace"

### Skill Structure

Each skill follows the [Agent Skills specification](https://agentskills.io/specification):

```
skill-name/
└── SKILL.md    # Instructions and metadata
```

## Quick Reference

### Evaluation
```bash
make eval-e1 MODELS="gpt-5-mini" N=10
make eval-e2 MODELS="gpt-5-mini" N=2 INCLUDE_TOOLS=true
make report-network-logs
```

### Data Building
```bash
make data-e1              # E1 production dataset
make clone-e2-sources     # Clone repos for E2
make data-e2-local        # E2 production dataset
make data-test-all        # CI test fixtures
```

### Deployment
```bash
make hub-deploy E=network-logs BUMP=patch
make pypi-publish-utils
```

### HuggingFace
```bash
make hf-e1p-push-canonical HF_ORG=your-org
make validate-data
```

### Development
```bash
make check    # lint + format + test
make e1       # test E1 environment
```

## Contributing

When adding new skills:
1. Create a directory matching the skill name
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`)
3. Keep instructions concise (< 500 lines)
4. Use Make commands as the primary interface
5. Update this README
