# Heldout and Public Data Policy

SV-Bench uses public mini sets for smoke tests and examples. Larger benchmark splits may be gated or held out to reduce contamination and preserve evaluation value.

## Public

- Small, reproducible examples under `datasets/public_mini/`.
- Safe E1/E2 examples suitable for local smoke tests.
- Sanitized E3-E6 beta examples with no operational misuse content.

## Gated

- Full E1/E2 benchmark splits where contamination would affect comparisons.
- Maintainer-controlled metadata needed for reproducible reports.

## Restricted

- Raw harmful prompts, exploit corpora, secret material, private customer data, and weaponized red-team traces.
- Offensive/red-team corpora for E5/E6 must not be published for SV-Bench v0.1.

Release checks should fail if public artifacts contain obvious secret markers or raw harmful-corpus placeholders.
