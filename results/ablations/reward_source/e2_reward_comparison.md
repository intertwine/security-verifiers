# Reward Source Comparison: E2

## Budget Parity

All required budget fields match across executable, judge, and hybrid manifests.

## Hosted Identity

Hosted environment IDs and versions match across variants, or were not reported.

## Metric Deltas

| Metric | Executable | Judge | Hybrid | Judge delta | Hybrid delta |
|---|---:|---:|---:|---:|---:|
| eval/intertwine/sv-env-config-verification/avg@1 | 0.1571 | 0.5000 | 1.1571 | 0.3429 | 1.0000 |
| eval/intertwine/sv-env-config-verification/completion_len/max | 1241.0000 | 636.0000 | 831.0000 | -605.0000 | -410.0000 |
| eval/intertwine/sv-env-config-verification/completion_len/mean | 765.5000 | 516.5000 | 723.5000 | -249.0000 | -42.0000 |
| eval/intertwine/sv-env-config-verification/completion_len/min | 290.0000 | 397.0000 | 616.0000 | 107.0000 | 326.0000 |
| eval/intertwine/sv-env-config-verification/failed_rollouts | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| eval/intertwine/sv-env-config-verification/is_truncated/mean | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| eval/intertwine/sv-env-config-verification/no_response/count | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| eval/intertwine/sv-env-config-verification/no_response/mean | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| eval/intertwine/sv-env-config-verification/pass@1 | n/a | 0.5000 | n/a | n/a | n/a |
| eval/intertwine/sv-env-config-verification/time | 46.4097 | 43.7741 | 15.2604 | -2.6357 | -31.1494 |
| progress/ckpt_step | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| step | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

## Failure-Mode Notes

- All three runs completed on Prime hosted training against the same hosted environment identity, `intertwine/sv-env-config-verification@0.2.19`.
- This is a claim-grade matched hosted pilot: required budget fields match, hosted identity matches, and the runs report zero failed rollouts, zero truncated rollouts, and zero no-response rollouts. The run is intentionally small (`max_steps=1`) and should not be read as a large-scale convergence result.
