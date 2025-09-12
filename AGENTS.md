# AGENTS.md

Guidelines for agents working on the Security Verifiers repository.

## Required Checks

- Run `make lint` and `make test` (or `make check`) before committing. Use the Makefile targets rather than calling tools directly, and run `make install-dev` first if dependencies are missing.
- Ensure documentation and READMEs are updated alongside code changes.

## Coding Practices

- Use the `sv_shared` package for shared parsers, rewards, and utilities.
- Include type hints and docstrings for public functions.
- Normalize reward components to the `[0.0, 1.0]` range.

## Workflow Notes

- Prefer Makefile targets over raw commands when available.
- Do not commit secrets or API keys.
- Keep commits focused and descriptive.
