# Data Build Scripts

This directory contains scripts for building and uploading datasets for the Security Verifiers environments.

## Public Datasets

Public metadata-only datasets are available for browsing:
- **E1 (Network Logs)**: https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata
- **E2 (Config Verification)**: https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata

These repos include sampling metadata and instructions for requesting access to full datasets.

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

### `create_public_datasets.py`

Creates PUBLIC metadata-only datasets on HuggingFace with model cards and access instructions (maintainers only).

**Requirements:**
- HF_TOKEN in `.env` file or environment variable
- Packages: `huggingface_hub`, `python-dotenv`

**Usage:**
```bash
# Set HF_TOKEN in .env (recommended)
echo "HF_TOKEN=your_token_here" >> .env

# Create public metadata-only datasets
uv run python scripts/data/create_public_datasets.py --hf-org intertwine-ai

# Or use Make target
make create-public-datasets HF_ORG=intertwine-ai
```

**What's Uploaded:**
- Sampling metadata files (`sampling-*.json`)
- Tools versions (`tools-versions.json` for E2)
- Model cards explaining privacy rationale
- Links to GitHub Issues for access requests

**Script Options:**
- `--hf-org`: HuggingFace organization name (required)
- `--dataset-name-prefix`: Base dataset name prefix (default: `security-verifiers`)
- `--e1-only`: Only create E1 public dataset
- `--e2-only`: Only create E2 public dataset

### `upload_to_hf.py`

Builds and uploads PRIVATE production datasets to HuggingFace Hub (maintainers only).

**Requirements:**

- HF_TOKEN in `.env` file or environment variable
- Packages: `huggingface_hub`, `python-dotenv`

**Usage:**

```bash
# Set HF_TOKEN in .env (recommended)
echo "HF_TOKEN=your_token_here" >> .env

# Upload all PRIVATE datasets
uv run python scripts/data/upload_to_hf.py --hf-org intertwine-ai

# Upload only E1 datasets
uv run python scripts/data/upload_to_hf.py --hf-org intertwine-ai --e1-only

# Upload only E2 datasets
uv run python scripts/data/upload_to_hf.py --hf-org intertwine-ai --e2-only

# Or use Make target
make upload-datasets HF_ORG=intertwine-ai
```

**Script Options:**

- `--hf-org`: HuggingFace organization name (default: `intertwine-ai`)
- `--dataset-name`: Base dataset name on HF Hub (default: `security-verifiers`)
- `--k8s-root`: Path to K8s source files for E2 (default: `scripts/data/sources/kubernetes`)
- `--tf-root`: Path to Terraform source files for E2 (default: `scripts/data/sources/terraform`)
- `--e1-only`: Only build and upload E1 datasets
- `--e2-only`: Only build and upload E2 datasets

**Testing:**
The upload script includes comprehensive unit tests:

```bash
# Run tests
uv run pytest scripts/data/upload_to_hf_test.py -v

# Check code quality
uv run ruff check scripts/data/upload_to_hf.py
```

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

- `HF_TOKEN`: HuggingFace API token (required for `upload_to_hf.py`)
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

# Upload to HuggingFace (maintainers only)
make upload-datasets HF_ORG=intertwine-ai

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
