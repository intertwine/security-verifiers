# **Agent Prompt: Gate & Re‑Upload Private HF Datasets + Wire Up Seamless Hub Loading for E1/E2 (Repo v0.2.0)**

## Context (ground truth)

- Repo: `intertwine/security-verifiers` @ v0.2.0. Production envs are:

  - `sv-env-network-logs` (E1)
  - `sv-env-config-verification` (E2)
    Environments share `sv_shared` helpers and already advertise **multi‑tier dataset loading** (local → **Hub** → synthetic). The README shows env vars `E1_HF_REPO` / `E2_HF_REPO` and Make targets to push datasets. ([GitHub][1])

- Public metadata datasets (browseable; **no raw data**):

  - `intertwine-ai/security-verifiers-e1-metadata`
  - `intertwine-ai/security-verifiers-e2-metadata` ([Hugging Face][2])

- The full E1/E2 datasets already exist privately on HF, but must be **reconfigured as gated** and **reuploaded** under the repo’s current conventions.

- HF gating is configured in the **Hub Settings UI**; usage can be guided/augmented with dataset card YAML fields (`extra_gated_*`). **Use the `token` argument or `DownloadConfig(token=...)` with `datasets.load_dataset`** (not `use_auth_token`, which is deprecated). ([Hugging Face][4])

- CLI users run evals either via **`vf-eval`** (Verifiers CLI) or **`prime env eval`** (Prime CLI). Our environments should seamlessly pull from gated HF if `HF_TOKEN` is set and the user has access. ([GitHub][5])

## Goal

1. **Reconfigure and re‑upload** the private E1/E2 datasets on Hugging Face as **gated** repos (manual approval; evaluation‑only terms).
2. **Harden environment data loaders** to:

   - prefer local when present, otherwise **Hub** (token‑aware), then synthetic,
   - **catch gated‑access errors** with helpful remediation messages,
   - support `HF_TOKEN` (and `HUGGINGFACE_TOKEN`) automatically.

3. **Makefile & scripts:** add make targets to (a) validate splits, (b) push to private gated repos, (c) smoke‑test loading via Hub with `HF_TOKEN`.
4. **Dataset cards & license:** add an **evaluation‑only license** and a **gating form** that forbids training/fine‑tuning/redistribution.
5. **Docs:** update `docs/hub-deployment.md` and `docs/user-dataset-guide.md` to reflect the **gated HF flow** and the **tokened Hub path** already signposted in the README. ([GitHub][1])

## Concrete repo changes

### A) Shared HF loader (new)

**File:** `sv_shared/hf_datasets.py` (new)

```python
# sv_shared/hf_datasets.py
from __future__ import annotations
import os
from typing import Optional
from datasets import load_dataset, DownloadConfig
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

class DatasetAccessError(RuntimeError): ...

def _get_hf_token() -> Optional[str]:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

def load_hf_split(repo_id: str, split: str, streaming: bool=False):
    """
    Robust HF loader for gated/private datasets.
    - Uses `token` (datasets>=2.14) with DownloadConfig fallback.
    - Raises DatasetAccessError with actionable advice on gating failures.
    """
    token = _get_hf_token()
    try:
        try:
            # Preferred path (datasets>=2.14)
            return load_dataset(repo_id, split=split, token=token, streaming=streaming)
        except TypeError:
            # Older `datasets`: fall back to DownloadConfig
            dlc = DownloadConfig(token=token)
            return load_dataset(repo_id, split=split, download_config=dlc, streaming=streaming)
    except GatedRepoError as e:
        msg = (
            f"Hugging Face gated dataset '{repo_id}' requires approved access.\n"
            f"1) Ensure you are logged in on the Hub and requested access on the dataset page.\n"
            f"2) Once approved, set HF_TOKEN and retry.\n"
        )
        raise DatasetAccessError(msg) from e
    except RepositoryNotFoundError as e:
        raise DatasetAccessError(f"Dataset repo '{repo_id}' not found or you lack access.") from e
```

**Why:** consolidates token handling; uses modern `token` (not deprecated `use_auth_token`) and surfaces gating remediation. ([Hugging Face][6])

### B) Wire into both environments

**Files:**
`environments/sv-env-network-logs/src/sv_env_network_logs/loader.py` (or wherever `load_environment` resolves data)
`environments/sv-env-config-verification/src/sv_env_config_verification/loader.py`

**Changes (pattern):**

```python
# inside environment dataset resolver
from sv_shared.hf_datasets import load_hf_split, DatasetAccessError

def _resolve_dataset(dataset_source: str | None=None, split: str="default"):
    """
    Auto: local -> hub -> synthetic  (already documented in README)
    """
    if dataset_source in (None, "auto", "local"):
        ds = _try_load_local(split)
        if ds is not None:
            return ds
        if dataset_source == "local":
            raise FileNotFoundError("Local dataset not found; try dataset_source='hub'.")

    # Hub path (gated)
    try:
        repo_id = os.getenv("E1_HF_REPO") if ENV_NAME=="sv-env-network-logs" else os.getenv("E2_HF_REPO")
        if not repo_id:
            raise DatasetAccessError(f"Set {'E1_HF_REPO' if ENV_NAME=='sv-env-network-logs' else 'E2_HF_REPO'} to your private HF dataset repo id.")
        return load_hf_split(repo_id, split=split)
    except DatasetAccessError as e:
        if dataset_source == "hub":
            raise
        # fall back to synthetic fixtures (as documented in README)
        return _load_synthetic_fixtures(split)
```

This matches the repo’s **Auto mode** and fills in the **Hub** branch with robust gating/error messages. ([GitHub][1])

### C) Makefile targets (add/adjust)

Add the following PHONY targets to keep parity with README conventions:

```make
.PHONY: validate-data hf-reconfigure-e1 hf-reconfigure-e2 hf-push-private hub-test-datasets

validate-data:
\tuv run python scripts/validate_splits.py

# Reconfigure (re-build) + push private gated datasets
# Expects: HF_TOKEN, E1_HF_REPO, E2_HF_REPO
hf-reconfigure-e1:
\tuv run python scripts/hf/build_e1_private.py
\tuv run python scripts/hf/push_dataset.py --repo $${E1_HF_REPO} --dir environments/sv-env-network-logs/data/private

hf-reconfigure-e2:
\tuv run python scripts/hf/build_e2_private.py
\tuv run python scripts/hf/push_dataset.py --repo $${E2_HF_REPO} --dir environments/sv-env-config-verification/data/private

hf-push-private: validate-data hf-reconfigure-e1 hf-reconfigure-e2

hub-test-datasets:
\tuv run python scripts/hf/smoke_hub_loading.py
```

This complements the existing `hf-*push*` targets mentioned in the README and gives a single shot to **rebuild + reupload** to the private gated repos. ([GitHub][1])

### D) Upload helper script (new)

**File:** `scripts/hf/push_dataset.py` (new; minimal Hub API wrapper)

```python
# scripts/hf/push_dataset.py
import argparse, os, pathlib, sys
from huggingface_hub import HfApi, HfFolder, upload_folder, create_repo

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="e.g. your-org/security-verifiers-e1-private")
    ap.add_argument("--dir", required=True, help="local folder with dataset files")
    ap.add_argument("--private", action="store_true", default=True)
    args = ap.parse_args()

    token = os.getenv("HF_TOKEN") or HfFolder.get_token()
    if not token:
        print("HF_TOKEN is required.", file=sys.stderr); sys.exit(2)

    api = HfApi(token=token)
    create_repo(args.repo, repo_type="dataset", private=True, exist_ok=True, token=token)
    upload_folder(
        repo_id=args.repo, repo_type="dataset",
        folder_path=args.dir, commit_message="push canonical split(s)", token=token
    )
    print(f"Pushed to https://huggingface.co/datasets/{args.repo}")

if __name__ == "__main__":
    main()
```

> **Important:** **Enabling gating** is a **Settings (UI)** step. After first push, owners must enable “Access requests” (manual approval) and configure the form. You can subsequently manage approvals via the Hub’s gating API or `huggingface_hub` helpers, but the **on/off switch** is set in the UI. ([Hugging Face][4])

### E) Gated dataset cards (new/replace on private repos)

**Files (in each private repo root):** `README.md` (dataset card), `LICENSE_EVAL_ONLY.txt`

**EVAL‑ONLY license file content (use verbatim):**

```txt
SECURITY VERIFIERS DATASET EVALUATION LICENSE (EVAL-ONLY)

You may use this dataset solely for evaluation of language or decision-making models
in the context of the Security Verifiers initiative. You may not modify, reproduce,
or redistribute any portion of the dataset. You may not use the dataset (or any
derived version) for training or fine-tuning a model or for inclusion in any model
pre-training corpus. You must not publish raw dataset items or enable third parties
to reconstruct the dataset. See repository README for contact and access management.
```

**Dataset card front‑matter (prepend to `README.md` in each private repo):**

```md
---
license: other
license_name: security-verifiers-eval-only
license_link: https://github.com/intertwine/security-verifiers/blob/main/docs/DATASET_EVAL_ONLY_LICENSE.md
gated: true
extra_gated_heading: "Request access (evaluation only)"
extra_gated_description: "Manual approval. You agree to evaluation-only terms."
extra_gated_button_content: "Request evaluation access"
extra_gated_prompt: "You agree the dataset is evaluation-only; no training/fine-tuning/redistribution."
extra_gated_fields:
  Affiliation: text
  Intended use:
    type: select
    options: ["Evaluation-only", "Other (explain in Notes)"]
  Contact email: text
  HF username: text
  I agree to EVAL-ONLY license: checkbox
tags:
  - security
  - verifiers
  - gated
  - evaluation
---

# Security Verifiers — Private Canonical Splits

This repository hosts the private canonical split(s) for {{E1|E2}} used by the `sv-env-{{network-logs|config-verification}}` environment.
Granting access preserves benchmark integrity and prevents training contamination.
```

> **Note:** Card YAML customizes the **gate form** and records the gating posture. Users still must be manually approved. ([Hugging Face][4])

### F) Smoke tests (new)

**File:** `scripts/hf/smoke_hub_loading.py`

```python
import os
from sv_shared.hf_datasets import load_hf_split

def check(repo_id: str, split: str):
    ds = load_hf_split(repo_id, split=split)
    print(repo_id, split, len(ds))
    print(ds[0])

if __name__ == "__main__":
    # Expect E1_HF_REPO / E2_HF_REPO and HF_TOKEN set
    e1 = os.environ["E1_HF_REPO"]
    e2 = os.environ["E2_HF_REPO"]
    check(e1, "default")
    check(e2, "default")
```

Run via: `HF_TOKEN=... E1_HF_REPO=... E2_HF_REPO=... make hub-test-datasets`

### G) Docs updates

- **`docs/hub-deployment.md`:** add the gated flow section:

  1. build locally (`make data-e1`, `make data-e2-local`),
  2. push private canonical splits (`make hf-reconfigure-e1 hf-reconfigure-e2`),
  3. enable gating in HF Settings (manual approval),
  4. verify with `make hub-test-datasets`,
  5. deploy envs to Hub (`make hub-deploy E=network-logs` / `E=config-verification`) and evaluate via **`vf-eval`** or **`prime env eval`**. ([GitHub][1])

- **`docs/user-dataset-guide.md`:** add “Request access & run”:

  - Request access on the private dataset pages (manual approval).
  - Set `HF_TOKEN` (or run `hf auth login`) and **do not** commit tokens.
  - Example runs:

    - Verifiers CLI:

      ```bash
      export HF_TOKEN=... E1_HF_REPO=your-org/security-verifiers-e1-private
      vf-eval your-org/sv-env-network-logs --num-examples 50
      ```

    - Prime CLI:

      ```bash
      export HF_TOKEN=...
      prime env install your-org/sv-env-network-logs
      prime env eval sv-env-network-logs -m meta-llama/llama-3.1-8b-instruct -n 50
      ```

    (Environments already default to **Auto** dataset source and will use **Hub** when locals are absent and a token is present.) ([GitHub][1])

### Acceptance criteria

- **Private HF repos live & gated** (manual approval on): E1/E2 canonical splits uploaded; dataset cards show evaluation‑only terms & custom gating form. Users without approval get a clear denial until they request access. ([Hugging Face][4])
- **Env loaders** successfully load **local → Hub (gated, token) → synthetic** and emit actionable errors on `GatedRepoError` (pointing users to request access and set `HF_TOKEN`). ([Hugging Face][4])
- **End‑to‑end eval runs**:

  - `vf-eval your-org/sv-env-network-logs --num-examples N` works when `HF_TOKEN` and `E1_HF_REPO` are set and the user is approved. ([GitHub][5])
  - `prime env eval sv-env-network-logs -m <model> -n N` works in the same conditions. ([Prime Intellect Docs][7])

- **Make targets** rebuild, push, and smoke‑test Hub loading as documented in README. ([GitHub][1])
- **Docs** explain the full gating/onboarding path and the Auto dataset source behavior. ([GitHub][1])

### Operational & security notes

- Prefer **`token=`** or `DownloadConfig(token=...)` over `use_auth_token` (deprecated). ([Hugging Face][6])
- Keep **raw examples** out of logs/artifacts. Use dataset IDs in metadata only. (Repo already emphasizes contamination prevention and private hosting.) ([GitHub][1])
- Add `HF_TOKEN` to `.env.example` (it already exists) and ensure it’s in `.gitignore`.

---

## Drop‑in snippet pack (ready to paste)

- `sv_shared/hf_datasets.py` — **[above]**
- `scripts/hf/push_dataset.py` — **[above]**
- `LICENSE_EVAL_ONLY.txt` — **[above]**
- Dataset card YAML front‑matter — **[above]**
- Makefile targets — **[above]**
- `scripts/hf/smoke_hub_loading.py` — **[above]**

---

### Why these changes are minimal‑risk

They match the **current v0.2.0 contract** (Auto: local → Hub → synthetic) and the README’s env‑var patterns for E1/E2 HF repos, while swapping in a **robust gated Hub branch** and the **modern HF token usage**. No changes to eval semantics or reward code. The result is a seamless experience for **`vf-eval`** and **`prime env eval`** users once approved for the gate. ([GitHub][1])

---

### Notes on E1/E2 details (for dataset builders)

- E1 (network logs): IoT‑23 primary; CIC‑IDS‑2017 and UNSW‑NB15 for OOD (per Exec Summary / metadata repos). Preserve split/version names and reproducibility metadata.
- E2 (config verification): K8s/Terraform sources; tool‑grounded labels. Keep tool versions pinned as in metadata. ([Hugging Face][3])

---

If you want, I can also generate a one‑shot “PR description checklist” you can paste into GitHub to track the exact file changes and test steps.

[1]: https://github.com/intertwine/security-verifiers "GitHub - intertwine/security-verifiers: Reinforcement Learning Verifiers for Cybersecurity"
[2]: https://huggingface.co/datasets/intertwine-ai/security-verifiers-e1-metadata "intertwine-ai/security-verifiers-e1-metadata · Datasets at Hugging Face"
[3]: https://huggingface.co/datasets/intertwine-ai/security-verifiers-e2-metadata "intertwine-ai/security-verifiers-e2-metadata · Datasets at Hugging Face"
[4]: https://huggingface.co/docs/hub/en/datasets-gated "Gated datasets"
[5]: https://github.com/PrimeIntellect-ai/verifiers?utm_source=chatgpt.com "PrimeIntellect-ai/verifiers: Environments for LLM ..."
[6]: https://huggingface.co/docs/datasets/v2.18.0/en/package_reference/loading_methods?utm_source=chatgpt.com "Loading methods"
[7]: https://docs.primeintellect.ai/tutorials-environments/evaluating?utm_source=chatgpt.com "Evaluating Environments (Closed Beta)"
