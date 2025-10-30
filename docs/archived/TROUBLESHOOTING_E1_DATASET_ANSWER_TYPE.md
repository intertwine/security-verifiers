# [RESOLVED] sv-env-network-logs: HF dataset answer type mismatch

**Status**: FIXED in commit [current]

**Issue**: The HuggingFace dataset for E1 (network-logs) used `ClassLabel` for the `answer` field, which returns integer values (0=Benign, 1=Malicious). The Verifiers environment expected string values, causing Pydantic validation errors.

## Root Cause

- HF dataset schema: `answer: ClassLabel(names=['Benign', 'Malicious'])` → returns `int` (0 or 1)
- Environment expectation: `answer: str` ("Benign" or "Malicious")
- Repository name: Default was `intertwine-ai/security-verifiers-e1-private` but actual repo is `intertwine-ai/security-verifiers-e1`

## Solution Implemented

Fixed in [sv_shared/dataset_loader.py](sv_shared/dataset_loader.py):

1. **Updated default repository name**: Changed from `security-verifiers-e1-private` to `security-verifiers-e1`

2. **Added automatic answer type coercion**: When loading E1 datasets from HuggingFace Hub, the loader now:
   - Maps integer values to strings: `0 → "Benign"`, `1 → "Malicious"`
   - Updates the dataset Features schema to use `Value("string")` instead of `ClassLabel`
   - This happens transparently during dataset loading

3. **Updated tests**: Fixed [sv_shared/dataset_loader_test.py](sv_shared/dataset_loader_test.py) to account for the answer coercion step

## Testing

```bash
# Verify the fix works
uv run pytest environments/sv-env-network-logs/ -v
uv run pytest sv_shared/dataset_loader_test.py -v

# Test with real HF dataset
uv run python -c "
from sv_env_network_logs import load_environment
env = load_environment(dataset_source='hub', max_examples=5)
print(f'Loaded {len(env.dataset)} examples')
print(f'Answer types: {set(type(ex[\"answer\"]).__name__ for ex in env.dataset)}')
"
```

## For Users

No action required. The fix is transparent and automatic when loading from HuggingFace Hub. The environment now correctly handles both:
- Local JSONL files (already have string answers)
- HuggingFace datasets (now automatically convert int to string)

---

This document is archived for reference. The issue has been resolved.
