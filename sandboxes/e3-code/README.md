# E3 Code Sandbox

Build:

```bash
docker build -t svbench/e3-code:local sandboxes/e3-code
```

Expected tools:

- python
- pytest
- bandit
- semgrep
- ruff

This image is for defensive toy repair tasks and should run without network access during tests.
