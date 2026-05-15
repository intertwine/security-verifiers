# Reward Source Comparison: E1

## Budget Parity

All required budget fields match across executable, judge, and hybrid manifests.

## Hosted Identity

Hosted environment identity/version differs across variants and is reported separately.

- `environment_version`: {'executable': '0.2.15', 'judge': '0.2.18'}
- `prime_environment_id`: {'executable': 'intertwine/sv-env-network-logs', 'judge': 'intertwine/sv-netlogs-judge'}

## Metric Deltas

| Metric | Executable | Judge | Hybrid | Judge delta | Hybrid delta |
|---|---:|---:|---:|---:|---:|
| eval/intertwine/sv-env-network-logs/avg@1 | 1.7850 | n/a | 1.7900 | n/a | 0.0050 |
| eval/intertwine/sv-env-network-logs/completion_len/max | 22.0000 | n/a | 21.0000 | n/a | -1.0000 |
| eval/intertwine/sv-env-network-logs/completion_len/mean | 21.1000 | n/a | 21.0000 | n/a | -0.1000 |
| eval/intertwine/sv-env-network-logs/completion_len/min | 21.0000 | n/a | 21.0000 | n/a | 0.0000 |
| eval/intertwine/sv-env-network-logs/failed_rollouts | 0.0000 | n/a | 0.0000 | n/a | 0.0000 |
| eval/intertwine/sv-env-network-logs/is_truncated/mean | 0.0000 | n/a | 0.0000 | n/a | 0.0000 |
| eval/intertwine/sv-env-network-logs/no_response/count | 0.0000 | n/a | 0.0000 | n/a | 0.0000 |
| eval/intertwine/sv-env-network-logs/no_response/mean | 0.0000 | n/a | 0.0000 | n/a | 0.0000 |
| eval/intertwine/sv-env-network-logs/time | 0.2066 | n/a | 0.1446 | n/a | -0.0619 |
| eval/intertwine/sv-netlogs-judge/avg@1 | n/a | 0.4400 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/completion_len/max | n/a | 553.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/completion_len/mean | n/a | 178.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/completion_len/min | n/a | 119.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/failed_rollouts | n/a | 0.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/is_truncated/mean | n/a | 0.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/no_response/count | n/a | 0.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/no_response/mean | n/a | 0.0000 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/pass@1 | n/a | 0.4400 | n/a | n/a | n/a |
| eval/intertwine/sv-netlogs-judge/time | n/a | 8.3368 | n/a | n/a | n/a |
| progress/ckpt_step | 48.0000 | 48.0000 | 49.0000 | 0.0000 | 1.0000 |
| step | 50.0000 | 50.0000 | 50.0000 | 0.0000 | 0.0000 |

## Failure-Mode Notes

- All three runs completed on Prime hosted training and reported zero failed rollouts, zero truncated rollouts, and zero no-response rollouts.
- Treat the E1 judge comparison as exploratory because the judge run uses `intertwine/sv-netlogs-judge@0.2.18` while executable and hybrid use `intertwine/sv-env-network-logs@0.2.15`; the comparator required `--allow-unmatched` and reports the identity mismatch above.
