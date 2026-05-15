# Environments Hub Publication

Use the existing Hub Make targets:

```bash
make hub-validate E=network-logs
make hub-deploy E=network-logs TEAM=<team>
```

For suite v1, each environment must have:

- importable package
- public mini set
- eval config
- metrics documentation
- Hub ID or planned Hub ID
- data publication status

E1/E2 are production. E3-E6 must be labeled beta until their safety and smoke checks pass.
