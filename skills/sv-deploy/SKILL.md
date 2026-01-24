---
name: sv-deploy
description: Deploy Security Verifiers environments and packages. Use when asked to deploy to Prime Intellect Environments Hub, publish to PyPI, bump versions, build wheels, or manage releases.
metadata:
  author: security-verifiers
  version: "1.0"
---

# Security Verifiers Deployment

Deploy environments to Prime Intellect Environments Hub and publish packages to PyPI.

## Environment Names

| Short Name | Full Package | Environment |
|------------|--------------|-------------|
| network-logs | sv-env-network-logs | E1 |
| config-verification | sv-env-config-verification | E2 |
| code-vulnerability | sv-env-code-vulnerability | E3 |
| phishing-detection | sv-env-phishing-detection | E4 |
| redteam-attack | sv-env-redteam-attack | E5 |
| redteam-defense | sv-env-redteam-defense | E6 |

## Environments Hub Deployment

### Prerequisites

1. Login to Prime Intellect:
```bash
prime login
```

2. Ensure tests pass:
```bash
make test-env E=network-logs
```

### Quick Deploy (Validate + Version Bump + Deploy)

```bash
# Default: patch version bump
make hub-deploy E=network-logs

# Minor version bump (0.x.0)
make hub-deploy E=network-logs BUMP=minor

# Major version bump (x.0.0)
make hub-deploy E=network-logs BUMP=major

# No version bump
make hub-deploy E=network-logs BUMP=none
```

### Step-by-Step Deploy

```bash
# 1. Validate (tests + lint + build)
make hub-validate E=network-logs

# 2. Bump version
make update-version E=network-logs BUMP=patch

# 3. Deploy to Hub
make deploy E=network-logs
```

### Custom Team

```bash
make deploy E=network-logs TEAM=your-team
```

## Building Wheels

```bash
# Build single environment
make build-env E=network-logs

# Build all environments
make build

# Build security-verifiers-utils
make build-utils
```

Wheels are output to `environments/sv-env-*/dist/`.

## Version Management

### Environment Versions

```bash
# Bump patch (0.0.x)
make update-version E=network-logs BUMP=patch

# Bump minor (0.x.0)
make update-version E=network-logs BUMP=minor

# Bump major (x.0.0)
make update-version E=network-logs BUMP=major
```

### Utils Version

```bash
make update-utils-version BUMP=patch
```

This updates both `pyproject.toml` and `__init__.py`.

## PyPI Publishing (security-verifiers-utils)

### Test PyPI (for testing)

```bash
make pypi-publish-utils-test
```

Install from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ security-verifiers-utils
```

### Production PyPI

```bash
make pypi-publish-utils
```

**Warning**: This publishes to production PyPI. Requires confirmation.

## Deployment Checklist

Before deploying an environment:

- [ ] Tests pass: `make test-env E=name`
- [ ] Linting passes: `make lint`
- [ ] Wheel builds: `make build-env E=name`
- [ ] Version bumped appropriately
- [ ] README updated if behavior changed
- [ ] Logged in to Prime: `prime login`

## Using Deployed Environments

After deployment, users can run:

```bash
# Install from Hub
vf-install intertwine/sv-env-network-logs

# Run evaluation
vf-eval intertwine/sv-env-network-logs --model gpt-5-mini --num-examples 10
```

## Coordinated Releases (Shared Utils + Environments)

When updating `security-verifiers-utils` (sv_shared), environments that depend on it need coordinated releases:

```bash
# 1. Make changes to sv_shared/
# 2. Sync version in BOTH files (required for PyPI)
make update-utils-version BUMP=patch  # Updates pyproject.toml AND __init__.py

# 3. Test environments still work
make test

# 4. Publish to PyPI first
make pypi-publish-utils

# 5. Then deploy environments that use the new utils
make hub-deploy E=network-logs
make hub-deploy E=config-verification
```

**Important**: The Hub pulls `security-verifiers-utils` from PyPI, so always publish utils before deploying dependent environments.

## Multi-Environment Deployment

Deploy multiple environments efficiently:

```bash
# Sequential deployment (recommended for first-time)
make hub-deploy E=network-logs
make hub-deploy E=config-verification
make hub-deploy E=code-vulnerability

# Or use direct deploy if already validated
make deploy E=network-logs && make deploy E=config-verification
```

## Troubleshooting

**prime login fails**: Check internet connection, try `prime logout` then `prime login`.
**Wheel build fails**: Ensure `uv sync` was run in the environment directory.
**Version conflict**: Check the version in `pyproject.toml` isn't already published.
**PyPI auth**: Ensure `~/.pypirc` or `TWINE_USERNAME`/`TWINE_PASSWORD` are set.
**Interactive login prompt**: The first `make deploy` will open browser for authentication and prompt for team selection. This is normal.
**sv_shared version mismatch**: If PyPI publish fails with "version exists", ensure both `sv_shared/pyproject.toml` and `sv_shared/__init__.py` have matching, new versions.
**Pre-commit hook fails**: Install pre-commit with `uv pip install pre-commit`.

## Hub Integration Tests

Environments are tested on the Hub via CI. If tests fail:

1. Check `is_completed()` signature matches verifiers API
2. Check `env_response()` return type
3. Ensure `max_turns` parameter is accepted
4. Review Hub logs for timeout issues (common for multi-turn envs)
