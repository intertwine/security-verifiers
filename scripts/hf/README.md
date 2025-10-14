# HuggingFace Metadata Export

This directory contains scripts for exporting metadata in a standardized flat schema for HuggingFace Dataset Viewer compatibility.

## Problem Statement

The HuggingFace Dataset Viewer requires consistent schemas across all rows in a split. When metadata contains rows with different keys or nested structures, the viewer fails to render the dataset properly.

## Solution: Flat Schema

All metadata splits use a uniform six-column schema:

| Column | Type | Description |
|--------|------|-------------|
| `section` | string | Category (sampling/ood/tools/provenance/notes) |
| `name` | string | Short identifier key |
| `description` | string | 1-2 sentence summary |
| `payload_json` | string | JSON-encoded structured details (minified) |
| `version` | string | Dataset version (e.g., "v1") |
| `created_at` | string | ISO-8601 UTC timestamp |

All structured content is JSON-encoded inside `payload_json` for stable tabular display.

## Scripts

### `export_metadata_flat.py`

Exports metadata in the flat schema for both public and private HuggingFace repositories.

**Usage:**

```bash
# Build metadata locally
make hf-e1-meta      # E1 metadata → build/hf/e1/meta.jsonl
make hf-e2-meta      # E2 metadata → build/hf/e2/meta.jsonl

# Push to PUBLIC metadata-only repos
make hf-e1-push      # → intertwine-ai/security-verifiers-e1-metadata
make hf-e2-push      # → intertwine-ai/security-verifiers-e2-metadata

# Push to PRIVATE full dataset repos (meta split only)
make hf-e1p-push     # → intertwine-ai/security-verifiers-e1 (meta split)
make hf-e2p-push     # → intertwine-ai/security-verifiers-e2 (meta split)

# Push all metadata to all repos
make hf-push-all

# Or run directly
uv run python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl
uv run python scripts/hf/export_metadata_flat.py --env e1 --out build/hf/e1/meta.jsonl \
  --repo intertwine-ai/security-verifiers-e1-metadata --split meta --push
```

**Options:**

- `--env e1|e2`: Environment to export metadata for (required)
- `--out PATH`: Output JSONL file path (required)
- `--repo REPO_ID`: HuggingFace repo ID (required for `--push`)
- `--split NAME`: Split name (default: `meta`)
- `--push`: Push to HuggingFace Hub after exporting
- `--private`: Flag for logging (private repos managed manually)
- `--created-at TIMESTAMP`: Override created_at (ISO-8601 UTC)

**Important:**

- When pushing to private repos, **only the `meta` split is updated**
- Canonical `train/dev/test/ood` splits remain unchanged
- Requires `HF_TOKEN` in `.env` for `--push`

## E1 Metadata Sections

| Section | Name | Description |
|---------|------|-------------|
| sampling | iot23-train-dev-test | IoT-23 primary dataset sampling |
| sampling | e1-ood-datasets | OOD datasets (CIC-IDS-2017, UNSW-NB15) |
| ood | cic-ids-2017-ood | CIC-IDS-2017 OOD details |
| ood | unsw-nb15-ood | UNSW-NB15 OOD details |
| provenance | dataset-sources | Original dataset sources and references |
| notes | privacy-rationale | Training contamination prevention |

## E2 Metadata Sections

| Section | Name | Description |
|---------|------|-------------|
| sampling | e2-k8s-terraform | K8s and Terraform sampling |
| tools | tool-versions | Pinned security tool versions |
| tools | tool-descriptions | Tool descriptions and URLs |
| provenance | dataset-sources | Source repositories |
| notes | privacy-rationale | Training contamination prevention |
| notes | multi-turn-performance | Performance with/without tools |

## Example Row

```json
{
  "section": "sampling",
  "name": "iot23-train-dev-test",
  "description": "IoT-23 primary dataset sampling metadata (train/dev/test splits)",
  "payload_json": "{\"mode\":\"full\",\"seed\":42,\"total\":1800,\"by_split\":{\"train\":523,\"dev\":1274,\"test\":3}}",
  "version": "v1",
  "created_at": "2025-10-13T00:00:00Z"
}
```

## Schema Validation

Tests ensure:

1. All rows have exactly 6 required keys
2. `payload_json` contains valid minified JSON
3. Schema is consistent across all rows
4. Dataset loads correctly with HuggingFace `datasets` library

Run tests:

```bash
uv run pytest tests/hf/ -v
```

## Deployment Workflow

1. **Build metadata locally:**
   ```bash
   make hf-e1-meta hf-e2-meta
   ```

2. **Validate output:**
   ```bash
   # Check schema consistency
   cat build/hf/e1/meta.jsonl | jq -r 'keys | sort | join(",")' | sort | uniq

   # Validate payload_json
   cat build/hf/e1/meta.jsonl | jq -r '.payload_json' | head -n 3 | jq -c .
   ```

3. **Run tests:**
   ```bash
   uv run pytest tests/hf/ -v
   ```

4. **Push to HuggingFace:**
   ```bash
   # Set HF_TOKEN in .env
   echo "HF_TOKEN=your_token_here" >> .env

   # Push to all repos
   make hf-push-all
   ```

## Guardrails

- **Schema consistency:** All rows must have identical keys with identical types
- **No optional columns:** Every row must include all 6 fields
- **Valid JSON:** `payload_json` must always contain valid minified JSON
- **Private repo safety:** Only `meta` split is touched; `train/dev/test/ood` remain unchanged
- **Visibility preservation:** Public/private status maintained when pushing

## Related Documentation

- [scripts/data/README.md](../data/README.md): Data building scripts
- [README.md](../../README.md): Project overview
- [CLAUDE.md](../../CLAUDE.md): Development guide
