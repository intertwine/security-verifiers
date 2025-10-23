# Data Build Scripts

This directory contains scripts for building and uploading datasets for the Security Verifiers environments.

## Public Datasets

Public metadata-only datasets are available for browsing:

- **E1 (Network Logs)**: <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata>
- **E2 (Config Verification)**: <https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata>

These repos include sampling metadata and instructions for requesting access to full datasets.

**Metadata Schema:** All HuggingFace metadata splits use a standardized six-column flat schema:

- `section`: Category (sampling/ood/tools/provenance/notes)
- `name`: Short identifier key
- `description`: 1-2 sentence summary
- `payload_json`: JSON-encoded structured details (minified)
- `version`: Dataset version (e.g., "v1")
- `created_at`: ISO-8601 UTC timestamp

This schema ensures consistent rendering in the HuggingFace Dataset Viewer across all metadata splits.

## Scripts

### `build_e1_iot23.py`

Builds the E1 (Network Log Anomaly Detection) primary dataset from IoT-23.

**Quality Features (v1.1):**
- **70/15/15 split distribution** (train/dev/test) with stratified sampling
- **Robust port extraction** handling multiple column name variants (`id.orig_p`, `sport`, etc.)
- **Arrow format ports** (`sport→dport`) in prompts for readability
- **100% deduplication** effectiveness (1800 unique samples)
- **50/50 label balance** (malicious/benign)

**Usage:**

```bash
# Build production dataset (1800 samples)
uv run python scripts/data/build_e1_iot23.py --mode full

# Build test fixtures (~20-30 samples)
uv run python scripts/data/build_e1_iot23.py --mode test

# Or use Make targets
make data-e1        # production
make data-e1-test   # test fixtures
```

**Output:**
- `environments/sv-env-network-logs/data/iot23-train-dev-test-v1.jsonl` (1800 samples)
  - train: 1253 samples (69.6%)
  - dev: 269 samples (14.9%)
  - test: 278 samples (15.4%)
- `environments/sv-env-network-logs/data/sampling-iot23-v1.json` (metadata)

### `build_e1_ood.py`

Builds E1 out-of-distribution (OOD) datasets from CIC-IDS-2017 and UNSW-NB15.

**Quality Features (v1.1):**
- **Content-based deduplication** using 5-tuple + bytes + duration + state + service (not just 5-tuple)
- **Stratified sampling for CIC-IDS-2017** to overcome temporal clustering (fetches 10-30x samples)
- **100% unique hashes** for both datasets (600/600 each)
- **50/50 label balance** for CIC-IDS-2017 (was 100% benign in v1.0)
- **Diverse attack types** represented in CIC-IDS-2017

**Usage:**

```bash
# Build production OOD datasets (600 samples each)
uv run python scripts/data/build_e1_ood.py --mode full

# Build test fixtures
uv run python scripts/data/build_e1_ood.py --mode test

# Or use Make targets
make data-e1-ood        # production
make data-e1-test       # includes OOD test fixtures
```

**Output:**
- `environments/sv-env-network-logs/data/cic-ids-2017-ood-v1.jsonl` (600 samples, 50/50 balance)
- `environments/sv-env-network-logs/data/unsw-nb15-ood-v1.jsonl` (600 samples, 55/45 balance)
- `environments/sv-env-network-logs/data/sampling-e1-ood-v1.json` (metadata)

### `build_e2_k8s_tf.py`

Builds E2 (Security Config Verification) datasets from Kubernetes and Terraform source files.

**Quality Features (v1.1):**
- **K8s manifest validation** requiring ≥2 API markers (`apiVersion`, `kind`, `metadata`, `spec`)
- **Terraform HCL validation** requiring blocks (`resource`, `module`, `data`, `variable`, `output`, `provider`)
- **Pre-filtering before scanning** removes empty files and non-HCL/YAML content
- **100% valid prompts** after filtering (K8s: 444/444, Terraform: 115/115)
- **Tool version pinning** for reproducibility (KubeLinter 0.7.6, Semgrep 1.137.0, OPA 1.8.0)

**Usage:**

```bash
# Build from cloned sources (after running make clone-e2-sources)
uv run python scripts/data/build_e2_k8s_tf.py \
  --k8s-root scripts/data/sources/kubernetes \
  --tf-root scripts/data/sources/terraform \
  --mode full

# Build test fixtures
uv run python scripts/data/build_e2_k8s_tf.py --mode test

# Or use Make targets
make clone-e2-sources   # one-time setup
make data-e2-local      # production
make data-e2-test       # test fixtures
```

**Output:**
- `environments/sv-env-config-verification/data/k8s-labeled-v1.jsonl` (444 samples)
  - KubeLinter: 1014 violations, Semgrep: 422 violations
  - 244 files with violations (55.0%)
- `environments/sv-env-config-verification/data/terraform-labeled-v1.jsonl` (115 samples)
  - Semgrep: 4 violations (3.5% of files)
  - Low violation rate indicates high-quality source repos
- `environments/sv-env-config-verification/data/tools-versions.json` (tool versions)
- `environments/sv-env-config-verification/data/sampling-e2-v1.json` (metadata)

### `validate_e1_datasets.py`

Validates E1 datasets against HuggingFace sources.

**Checks:**
- Schema compliance (prompt, answer, meta fields)
- Label distribution and balance (±5% threshold)
- Deduplication effectiveness (hash uniqueness)
- Split distribution (train/dev/test ratios)
- Field mapping accuracy (source columns → prompt rendering)
- Sample verification (5 random items vs HuggingFace source)

**Usage:**

```bash
# Validate all E1 datasets (requires HF_TOKEN)
uv run python scripts/data/validate_e1_datasets.py --datasets all

# Validate specific dataset
uv run python scripts/data/validate_e1_datasets.py --datasets iot23
uv run python scripts/data/validate_e1_datasets.py --datasets ood

# Save report
uv run python scripts/data/validate_e1_datasets.py --datasets all --output outputs/validation-e1-report.json
```

### `validate_e2_datasets.py`

Validates E2 datasets against source repositories.

**Checks:**
- Schema compliance (prompt, info.violations, meta fields)
- Violation analysis (tool coverage, severity levels)
- Prompt content validation (K8s YAML / Terraform HCL markers)
- Tool version consistency
- Source file verification (requires local source repos)

**Usage:**

```bash
# Validate all E2 datasets
uv run python scripts/data/validate_e2_datasets.py --datasets all

# Validate specific dataset
uv run python scripts/data/validate_e2_datasets.py --datasets k8s
uv run python scripts/data/validate_e2_datasets.py --datasets terraform

# With source verification (requires local source repos)
uv run python scripts/data/validate_e2_datasets.py \
  --k8s-source-root scripts/data/sources/kubernetes \
  --tf-source-root scripts/data/sources/terraform

# Save report
uv run python scripts/data/validate_e2_datasets.py --datasets all --output outputs/validation-e2-report.json
```

### `clone_e2_sources.sh`

Clones recommended Kubernetes and Terraform repositories for E2 dataset building.

**Usage:**

```bash
bash scripts/data/clone_e2_sources.sh

# Or use Make target
make clone-e2-sources
```

### `export_metadata_flat.py` (in `scripts/hf/`)

Exports metadata in a standardized flat schema for HuggingFace Dataset Viewer compatibility.

**Location:** `scripts/hf/export_metadata_flat.py`

**Purpose:** Normalizes all metadata into a uniform six-column schema to ensure stable rendering in the HF Dataset Viewer.

**Requirements:**

- HF_TOKEN in `.env` file or environment variable (for `--push`)
- Packages: `huggingface_hub`, `datasets`, `python-dotenv`

**Usage:**

```bash
# Build metadata locally (flat schema)
make hf-e1-meta      # E1 metadata
make hf-e2-meta      # E2 metadata

# Push to PUBLIC metadata-only repos
make hf-e1-push      # Push to intertwine-ai/security-verifiers-e1-metadata
make hf-e2-push      # Push to intertwine-ai/security-verifiers-e2-metadata

# Push to PRIVATE full dataset repos (meta split only)
make hf-e1p-push     # Push to intertwine-ai/security-verifiers-e1
make hf-e2p-push     # Push to intertwine-ai/security-verifiers-e2

# Push all metadata to all repos
make hf-push-all

# Or run directly
uv run python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl
uv run python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl \
  --repo intertwine-ai/security-verifiers-e1-metadata --split meta --push
```

**Script Options:**

- `--env`: Environment (e1 or e2) (required)
- `--out`: Output JSONL file path (required)
- `--repo`: HuggingFace repo ID (required for `--push`)
- `--split`: Split name (default: `meta`)
- `--push`: Push to HuggingFace Hub after exporting
- `--private`: Flag for logging (private repos managed manually)
- `--created-at`: Override timestamp (ISO-8601 UTC)

**What's Exported:**

- Sampling metadata (how datasets were built)
- OOD dataset details (for E1)
- Tool versions and descriptions (for E2)
- Dataset provenance and sources
- Privacy rationale and access instructions

**Important:** When pushing to private repos, only the `meta` split is updated. Canonical `train/dev/test/ood` splits remain unchanged.

### `push_canonical_with_features.py` (in `scripts/hf/`)

Pushes canonical training/eval splits to PRIVATE HuggingFace repos with explicit Features for consistent nested rendering.

**Location:** `scripts/hf/push_canonical_with_features.py`

**Purpose:** Upload train/dev/test/ood splits with explicit HuggingFace Features so the Dataset Viewer renders nested structures consistently.

**Requirements:**

- HF_TOKEN in `.env` file or environment variable
- Packages: `huggingface_hub`, `datasets`, `python-dotenv`

**Usage:**

```bash
# Validate canonical splits first
make validate-data

# Dry run to preview (no actual push)
make hf-e1p-push-canonical-dry
make hf-e2p-push-canonical-dry

# Actually push to PRIVATE repos
make hf-e1p-push-canonical HF_ORG=intertwine-ai
make hf-e2p-push-canonical HF_ORG=intertwine-ai
```

**What's Pushed:**

- **E1**: `train`, `dev`, `test`, `ood` splits with explicit Features (ClassLabel for answer, nested meta)
- **E2**: `train` split (K8s + Terraform combined) with explicit Features (nested violations list, patch field)

**Schema Enforcement:**

- Pydantic validators (`validate_splits_e1.py`, `validate_splits_e2.py`) run before push
- Explicit HuggingFace Features ensure consistent nested rendering
- Coerces `info.patch: null` → `""` for E2 to match Features schema

## Output Locations

All build scripts write datasets to their respective environment data directories:

- **E1**: `environments/sv-env-network-logs/data/`
- **E2**: `environments/sv-env-config-verification/data/`

Each dataset includes sampling metadata in `sampling-*.json` files for reproducibility.

## Dataset Privacy

⚠️ **Important**: Production datasets are **NOT committed** to the repository to prevent training contamination.

- **Production datasets**: Built locally and uploaded to private HuggingFace repos
- **Test fixtures**: Small datasets (~20-30 samples) committed for CI/testing
- **Sampling metadata**: JSON files documenting how datasets were built (committed)

## Environment Variables

These scripts respect the following environment variables:

- `HF_TOKEN`: HuggingFace API token (required for pushing to HuggingFace)
- `LIMIT`: Override sample count for E1 builds (e.g., `LIMIT=100`)
- `N`: Override sample count for E1 OOD builds (e.g., `N=50`)

## Make Targets (Recommended)

For convenience, use the Make targets defined in the root `Makefile`:

```bash
# Production data builds
make data-e1            # E1 IoT-23
make data-e1-ood        # E1 OOD datasets
make data-e2-local      # E2 from cloned sources
make data-all           # All E1 datasets

# Test fixtures (committed for CI)
make data-e1-test       # E1 test fixtures
make data-e2-test       # E2 test fixtures
make data-test-all      # All test fixtures

# Validate canonical splits (Pydantic)
make validate-data      # Validate E1 & E2 canonical data

# HuggingFace operations (maintainers only)
make hf-e1-push                 # Push E1 PUBLIC metadata
make hf-e2-push                 # Push E2 PUBLIC metadata
make hf-e1p-push-canonical      # Push E1 PRIVATE canonical splits
make hf-e2p-push-canonical      # Push E2 PRIVATE canonical splits
make hf-push-all                # Push all metadata (public + private)

# Utilities
make clone-e2-sources   # Clone E2 source repositories
```

## CI Integration

Test fixtures are automatically validated in CI:

- `.github/workflows/ci.yml` runs tests using the committed test fixtures
- Tool versions (e.g., KubeLinter) are pinned in `environments/sv-env-config-verification/ci/versions.txt`
- Production datasets are NOT required for CI

## Troubleshooting

**"HF_TOKEN not found"**: Add your token to `.env`:

```bash
echo "HF_TOKEN=your_token_here" >> .env
```

**"Source directories not found"**: Run `make clone-e2-sources` first for E2 builds.

**"Dataset loading failed"**: Check that HuggingFace datasets are accessible and your token has appropriate permissions.

**Import errors**: Ensure dependencies are installed:

```bash
uv sync
```

## References

- [PRD.md](../../PRD.md): Dataset specifications and requirements
- [CLAUDE.md](../../CLAUDE.md): Development guide and quick commands
- [README.md](../../README.md): Project overview and getting started
