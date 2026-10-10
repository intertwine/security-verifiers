# Preserved adapter evaluation execution packet

`preserved-primary-20261010.json` is the primary 800-episode matrix: E1 200
cases × base/executable/judge and E2 100 × base/executable. It is intentionally
not launch ready. Preparation performs no model calls, deployments, or uploads.

```bash
.venv/bin/python scripts/run_preserved_evaluation.py \
  --packet configs/eval/preserved-primary-20261010.json
```

Execution additionally requires `--execute`. Set a numerical approved USD cap,
a current provider quote including **adapter** pricing, and conservative rates
covering every selected policy. Token-only billing must be verified; account
hosting/compute charges outside that model must be quoted and included or the
runner cannot enforce the full bill. `fixed_charges_usd` reserves the quoted
maximum non-request cost. The Intertwine AI team ID must match the explicit
`X-Prime-Team-ID` request header and verified credential billing scope. Keep keys
in the named environment variable, never in packet JSON or request headers.

Fill immutable model revisions and adapter SHA256 values. Each policy's
`identity_evidence` is `{path, sha256}` pointing to JSON whose `model`,
`base_revision`, and `adapter_sha256` exactly match the selected policy; adapter
policies also require their `training_run_id`. A structural compatibility check
alone cannot establish immutable base weights.

Each environment needs a frozen dataset, manifest and system prompt file. Cases
retain `question`, canonical environment `answer`, `info`, and `case_id` equal to
SHA256 of exact UTF-8 question. The manifest's dataset checksum must match and
its `heldout_verified` must be true. Candidate snapshots do not meet that claim.
The environment additionally needs `case_independence_verified=true` and a
hashed `scientific_review_evidence` JSON receipt containing:

- `status: approved`, a named `reviewer`, and exact `dataset_sha256`;
- `heldout_verified: true` and `case_independence_verified: true`;
- a hashed `training_membership_evidence` receipt pointing to JSON with all
  selected adapters' `training_run_ids` and complete unique `case_ids` (exact
  training prompt hashes). The runner checks held-out/train disjointness.

The reviewer must verify that this is full historical training membership and
that independent statistical units have been identified. A dataset's unique
prompt hashes cannot prove either fact on their own.

E2 requires exact version outputs for `kube-linter`, `semgrep`, and `opa`, and
`semgrep_rules: {path, sha256}` identifying frozen local rules. Scanner failures
stop execution; heuristic fallbacks are disabled. Recognizable raw Kubernetes
or Terraform inputs are supported, along with the existing explicit
`File path: ... / Configuration: fenced-content` wrapper. Ambiguous inputs
fail closed. Terraform offers Semgrep only; OPA's missing Terraform parser is
not presented as an available capability. The same role-neutral retained
fixture paths, system prompt and tool schema are used for paired policies.

The envelope caps E1 output at 2,048 tokens/episode, E2 aggregate output at
4,096 across at most five requests, three tool calls, 30 seconds/tool and 120
seconds/episode. UTF-8 bytes plus a conservative framing allowance bound input
size before each request; provider usage is checked afterward and any overrun
stops the run. SDK retries are disabled. The request budget reserves the full
input cap and remaining output cap **before** calling the provider. Failed or
uncertain requests retain their reservation. This intentionally overestimates
cost; no automatic refunds rely on uncertain provider billing.

Outputs are private, ignored files under `outputs/evals/`. The packet, data,
manifest, prompt, model receipts, review receipts, evaluator source, E2 adapters
and policies are fingerprinted for resume. A lock prevents simultaneous
writers. Every attempted episode is recorded before generation. An interrupted
attempt is never retried automatically; inspect it and report it as missing or
failed. Raw provider responses and tool observations are retained separately
from report scoring. A completed model call is not patch verification, learning
proof, or an empirical release-gate pass.
