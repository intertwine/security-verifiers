# E2 Policy Sandbox

Build:

```bash
docker build -t svbench/e2-policy:local sandboxes/e2-policy
```

Expected tools:

- opa
- conftest
- kube-linter
- semgrep
- yq
- jq
- Python validation utilities

Pinned tool versions live in `environments/sv-env-config-verification/ci/versions.txt`. Use `make check-tools` on hosts where direct local execution is expected.

Dry-run through the shared runner:

```bash
uv run python -c "from sv_shared.sandbox_runner import dry_run_sandbox; print(dry_run_sandbox(['semgrep', '--version'], image='svbench/e2-policy:local').to_dict())"
```
