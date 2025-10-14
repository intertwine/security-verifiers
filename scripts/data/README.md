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

### `build_e1_ood.py`

Builds E1 out-of-distribution (OOD) datasets from CIC-IDS-2017 and UNSW-NB15.

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

### `build_e2_k8s_tf.py`

Builds E2 (Security Config Verification) datasets from Kubernetes and Terraform source files.

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
