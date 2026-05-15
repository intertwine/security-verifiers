# Security Verifiers Suite v1 Checklist

| Environment | Status | Public Mini | Eval Config | Metrics Doc | Hub State |
|---|---|---|---|---|---|
| E1 network logs | Production | Yes | Yes | Yes | Ready |
| E2 config verification | Production | Yes | Yes | Yes | Ready |
| E3 code vulnerability | Beta slice | Yes | Yes | Yes | Planned |
| E4 phishing detection | Beta slice | Yes | Yes | Yes | Planned |
| E5 red-team attack | Sanitized beta slice | Yes | Yes | Yes | Planned |
| E6 red-team defense | Sanitized beta slice | Yes | Yes | Yes | Planned |

Completion gate:

```bash
make suite-v1-check
```

The suite gate distinguishes production, beta, gated, and restricted components. Passing smoke tests does not promote E3-E6 to production.
