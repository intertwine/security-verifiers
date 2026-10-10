# Evaluation data recovery and freeze, October 2026

The 200-case E1 and 100-case E2 **candidate** sets are frozen privately. Neither is ready to support an independent held-out comparison of preserved adapters. E1 full historical training membership and source/group independence remain unresolved; E2 builtin membership was subsequently reconstructed from the exact deployed package, but independent-case review remains pending; the freeze manifests explicitly record that limitation. No model calls were made.

## Actual source inventory

| Available source | Findings | Research use |
|---|---|---|
| Committed E1 public mini | 100 distinct inputs; metadata labels 71 train, 16 dev, 13 test | Smoke only; public exposure and historical use prohibit treating the whole mini set as held out. |
| Committed E2 public mini | 100 rows, 97 distinct inputs; no split labels | Smoke only; repeated input rows are not independent cases. |
| Committed E1 test/demo files | 20 IoT-23, 10 CIC and 10 UNSW test rows | Fixtures do not supply the requested 200 independent E1 cases. |
| Local canonical files | Full canonical JSONL files are absent; retained sampling records describe E1 1,800 rows (1,253 train/269 dev/278 test) and E2 444 Kubernetes/217 Terraform source items | Metadata establishes intended counts, not actual training membership or dataset bytes. |
| Hosted archive snapshots | 170 team objects; six E1 snapshots have 1,800 nonempty prompts; five E2 Kubernetes snapshots have 444 rows/437 distinct prompts; seven Terraform snapshots have 115 rows/63 distinct prompts | Recoverable inputs and labels; historical split/model-output information absent. Other snapshots frequently have empty prompts. |
| Public Hugging Face metadata cards | E1/E2 cards explicitly describe metadata-only hosting; private full data was not accessible through public retrieval | Descriptions and sampling records cannot establish held-out membership. |

The private inventory retains per-source SHA256, version joins, row counts and nonempty input counts under `outputs/completion_20261010/dataset_inventory.json`. Aggregate counts do not imply all hosted snapshots represent independent datasets; many repeat published versions.

The public-mini source file SHA256 values are:

- E1: `7f7dc1ef1cb0283efb00c1cbbc5c9e3f25af20b7bf13504ed959ae1bf7b29b93`
- E2: `09c6a402613097fdf56ea32d8b9e6f7fef640f209d71c068b0ea25e6bf153163`

## Frozen candidate contract

The private recovered E1 pool contains 1,800 distinct exact prompts. A historical E2 Kubernetes/Terraform snapshot pair contains 559 rows and 500 distinct prompts. One identical-input group had contradictory annotation/locations; both rows were excluded, leaving 499 distinct eligible inputs. Labels were not selected to improve apparent balance or outcomes.

| Candidate | Cases | SHA256 of frozen JSONL | Held-out verification |
|---|---:|---|---|
| E1 | 200 | `c72b41af664f8f328c9a4ead96cc5963c401724da476e304e7787fa07f6dae2e` | False |
| E2 | 100 | `271af901b4a8358664ee9b62e51f7c08dc2d050112276e2bf1d8e6593460769b` | False |

The initial E2 freeze above is superseded for runner preparation by a separate immutable `e2_candidate_freeze_builtin_excluded/` packet: it adds the environment-format `answer=json.dumps(info)`, excludes unresolved templates and documents builtin training exclusion. Its 100-case JSONL SHA256 is `b6a888be6299bd3f860a2b66fdf144bcafcfe80588d6bea01133971ea98fbb2c`. All 22 template-bearing source rows (21 distinct prompts) were excluded before deterministic selection; 478 distinct eligible prompts remain. Template values were not invented.

Each row preserves `question`, `answer` (E1), `info` (E2) and private source metadata, adding `case_id = SHA256(question UTF-8)`. Exact-input identity excludes labels, so contradictory labels cannot disguise training overlap. Selection orders hashes ascending, then takes the requested count. The output directory refuses overwrite. The manifest contains file digest, source digest, duplicate/overlap counts, ID-list paths and explicit provenance status.

These are candidate cases, **not 300 independently validated benchmark cases**. Unique prompt text cannot prove independent network scenarios, source configurations or equivalent variants. No source-group metadata was reconstructed from absent archive fields. E1 input abstraction can discard source-network context; E2 copied configuration variants can remain correlated.

## Freeze utility and complete membership requirement

```bash
python scripts/freeze_evaluation_data.py \
  --candidates PRIVATE_CANDIDATES.jsonl \
  --count 200 --output outputs/completion_20261010/new_candidate_freeze
```

For exclusion verification, additionally supply `--training FULL_TRAINING_MEMBERSHIP.jsonl --training-provenance MEMBERSHIP_PROVENANCE.json`. The descriptor must include:

```json
{
  "coverage": "full-training-membership",
  "dataset_sha256": "SHA256_OF_EXACT_TRAINING_JSONL",
  "training_run_ids": ["COVERED_RUN_ID"],
  "source_revision": "40_OR_64_HEX_IMMUTABLE_SOURCE_REVISION",
  "membership_evidence": {
    "path": "RELATIVE_EVIDENCE_FILE",
    "sha256": "SHA256_OF_EVIDENCE_FILE"
  }
}
```

Those strings are placeholders, not acceptable evidence. The utility verifies file digests, nonempty run attribution and immutable-revision format, computes exact input exclusion and emits sorted training/held-out IDs. It does not independently attest the scientific truth of the descriptor: review the referenced immutable environment/dataset and every covered run's selection rule. An exporter’s retained sample subset must use a different coverage value and can never establish full exclusion.

The utility **always** emits `heldout_verified=false`. A matching descriptor records `claimed_full_membership=true` and `exclusion_status=documented-full-membership`, but an opaque hashed document and a user assertion cannot independently prove training selection. `independence_status` remains `case-independence-unverified` until scientific review validates structured run-linked selection evidence and establishes the appropriate source grouping. Related variants, source overlap and base-model pretraining are separate questions. The evaluation runner should block research launches while either required provenance claim is unresolved.

## Remaining provenance work

1. For E1, recover resolved historical dataset bytes and exact full selection membership in addition to the now-recovered deployed packages, including local data bytes and loader selection order, or equivalent immutable complete training membership evidence. May runs passed `max_examples` and reward settings without an explicit dataset source/split; a default cannot be inferred from a current checkout.
2. Resolve the repository mismatch: dataset documentation names `security-verifiers-e1-private`/`e2-private`, while `sv_shared/dataset_loader.py` runtime defaults are `security-verifiers-e1`/`e2`. Direct HF repo arguments default to `train`; `auto` can fall back to synthetic cases. Freeze explicit local inputs for new research and record their digests; do not rely on `auto`.
3. Confirm whether source-group metadata (network scenario or upstream configuration identity) can be joined to the private full dataset. Deduplicate/group correlated inputs before treating case counts as independent.
4. Pin private HF datasets to immutable revisions using secure authenticated access if those are the authoritative files. Access denial through a public tool does not establish deletion or account permission status.
5. Compare the full run-linked membership against the candidate pools. If complete membership is unavailable, the defensible alternative is a newly controlled training split and independently frozen evaluation split; label recovered-adapter evaluations exploratory.

Public primary metadata: [E1 dataset card](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata), [E2 dataset card](https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata). Raw recovered cases stay private under the [held-out policy](../datasets/HELDOUT_POLICY.md).

Focused validation:

```bash
make review-check \
  REVIEW_PATHS="scripts/freeze_evaluation_data.py scripts/freeze_evaluation_data_test.py" \
  REVIEW_TESTS="scripts/freeze_evaluation_data_test.py"
```

Nine tests verify duplicate handling, contradictory-label rejection, label-independent overlap, refusal to infer full membership from retained samples, source/evidence checksum enforcement, deterministic ordering, overwrite refusal and empty/nontext prompt rejection.

## Exact deployed environment recovery

Official PyPI package JSON endpoints returned 404 for all three environment package names. The authoritative distribution is Prime Hub. Reading the official Prime CLI implementation established the public route `/api/v1/environmentshub/intertwine/{name}/@{version}`. All three requested historical versions were retrieved without authentication, and their returned `version_id` values exactly match archived May training configurations. Source archives were downloaded, hashed and compared against the platform-provided SHA256; every comparison passed. Official linked wheels were downloaded and CRC inspected. No recovered package code was executed.

| Deployed environment | Version | Verified source archive SHA256 | Embedded data and selection |
|---|---|---|---|
| E1 executable | 0.2.15 | `32fdd1a271d321c810b735bb1adaf50d83ba0e604c6c9d6f06572dbb6ae78d0b` | Source includes small test files, not canonical 1,800-row data; wheel includes no JSONL. Default loader is `auto`, with a ten-case synthetic fallback. |
| E1 judge | 0.2.18 | `e0b571a649485a203ace2c831542dad466741859df39faf0bdf7b636866394a2` | Neither source nor wheel embeds canonical data. Default loader is `auto`, with the same ten synthetic cases. |
| E2 | 0.2.19 | `e7a4d9044f769300b9fa810d41049dcb5da6797e39c7a609a1619d76e6f64dae` | Canonical files are embedded, but default `dataset_name="builtin"` explicitly selects two packaged fixtures instead. |

This recovers real deployed source identity; it is stronger than assuming a similarly named PyPI build or the current checkout was used. The private packet retains source/wheel fingerprints, member inventories, stable Hub metadata, original archive files and bounded inspection copies. Ephemeral signed-download query parameters were removed from saved metadata.

### E1 consequence: the May reward arms used different observed data

All 160 retained May executable observations match the ten synthetic literals recovered from its deployed source, by exact user-input text. The judge's 160 observations contain 19 distinct IoT-style prompts; none matches those synthetic literals, and all 19 occur in the recovered 1,800-input IoT snapshot pool. This supports a clear **observed training-input mismatch** in addition to the previously known environment-version mismatch. It does not prove the judge's complete membership or establish which mutable HF revision/order was resolved at runtime. The executable adapter's successful synthetic diagnostics cannot be interpreted as an operational improvement on independent IoT cases.

E1 therefore still needs exact full membership or a newly controlled training experiment. Do not infer the entire training dataset from retained observations, even when every observed executable case matches the fallback.

### E2 consequence: complete builtin input selection is recoverable

The exact deployed E2 function defaults to `builtin`, and its builtin branch loads only `bad_pod.yaml` and `bad.tf`. The three archived May configurations specify `max_examples=60` and reward-source settings but do not override dataset name/source. A cap of 60 does not expand a two-item builtin dataset. The private `e2_builtin_full_membership.jsonl` therefore records both source-defined configuration bodies, linked to the deployed archive hash, version ID and all three run metadata hashes. All 48 retained observations across these arms match `bad.tf` after removing the runtime path/fenced-text wrapper.

The frozen 100-case candidate set has **zero overlap** with these two builtin bodies after removing wrappers, normalizing line endings/trailing whitespace, and canonicalizing Kubernetes using safe YAML parsing and sorted JSON. It still has 100 distinct inputs under that normalization. Terraform normalization is limited and does not establish semantic equivalence; related source variants and case independence need review. Runtime local paths are not independent case identities.

The selection evidence is saved as structured JSON with exact source selection, hashed run links and source-member identities. Its descriptor records `claimed_full_membership=true`; `heldout_verified` remains false pending independent scientific review. This resolves the E2 input-selection question without turning its one-step compatibility pilot into learning proof or asserting the 100 candidates are independent.
