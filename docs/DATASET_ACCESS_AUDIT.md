# Dataset Access Audit

This audit checks whether the repository currently has usable local real-data assets, whether its configured download paths still work in the present environment, and whether the previous blanket **"MANUAL ACTION REQUIRED"** conclusion was fully justified.

## Audit commands used

```bash
env | sort | rg '^(HF_|HUGGINGFACE|DATASETS_|TRANSFORMERS_|XDG_CACHE_HOME|HOME|CODEX_HOME)='
find data -maxdepth 5 -type f | sort
rg --files outputs docs . | rg '(scidocs|fiqa|hotpotqa|bright|BRIGHT)'
for base in "$HOME/.cache" "$HOME/.huggingface" "$HOME/.local/share"; do
  if [ -d "$base" ]; then
    rg --files "$base" 2>/dev/null | rg '(scidocs|fiqa|hotpot|bright|BRIGHT|BeIR)'
  fi
done
python - <<'PY'
from huggingface_hub import HfApi
api = HfApi()
for repo in ['BeIR/scidocs','BeIR/scidocs-qrels','BeIR/fiqa','BeIR/fiqa-qrels','hotpot_qa','xlangai/BRIGHT']:
    try:
        info = api.dataset_info(repo)
        print(repo, 'OK', info.id, getattr(info, 'gated', None))
    except Exception as e:
        print(repo, type(e).__name__, e)
PY
python - <<'PY'
from datasets import load_dataset
checks = [
    ('BeIR/scidocs', 'corpus', 'corpus[:1]'),
    ('BeIR/fiqa', 'corpus', 'corpus[:1]'),
    ('hotpot_qa', 'fullwiki', 'validation[:1]'),
    ('xlangai/BRIGHT', 'examples', None),
]
for name, config, split in checks:
    try:
        kwargs = {'name': config, 'cache_dir': '/tmp/hf_dataset_audit'}
        if split is not None:
            kwargs['split'] = split
        print(load_dataset(name, **kwargs))
    except Exception as e:
        print(name, type(e).__name__, e)
PY
python - <<'PY'
import traceback
from datasets import load_dataset
try:
    load_dataset('hotpot_qa', 'fullwiki', split='validation[:1]', cache_dir='/tmp/hf_dataset_audit')
except Exception as e:
    print(type(e))
    print(repr(e))
    traceback.print_exc(limit=3)
PY
git log --all --stat -- data/raw data/processed outputs | head -n 300
```

## 1. Local data presence

### Environment / path assumptions actually used by the code

- The dataset registry hard-codes all raw and processed paths under the repository root; it does **not** read `HF_HOME`, `DATASETS_CACHE`, `XDG_CACHE_HOME`, or other environment-variable-defined dataset locations. In this environment only `HOME=/root` and `CODEX_HOME=/opt/codex` are set among the relevant variables I checked. `HF_*`, `HUGGINGFACE_*`, `DATASETS_*`, and `XDG_CACHE_HOME` are unset. `scripts` and loaders therefore resolve data only through the registry paths plus Hugging Face's default client behavior when contacting the network. 
- The current local filesystem contains only `.gitkeep` placeholders under the repo-managed raw/processed directories. No `queries.jsonl`, `documents.jsonl`, `qrels.jsonl`, or `pairwise/preferences.jsonl` files exist for any real dataset. 
- Default Hugging Face cache locations under `/root/.cache/huggingface`, `/root/.cache/huggingface/datasets`, and `/root/.cache/huggingface/hub` do not exist. A broader scan of `/root/.cache`, `/root/.huggingface`, and `/root/.local/share` found no files containing `scidocs`, `fiqa`, `hotpot`, `bright`, `BRIGHT`, or `BeIR`. 

### Dataset-by-dataset local status

| Dataset | Raw path(s) checked | Processed path(s) checked | Files found | Judgment | Enough to run locally without download? |
|---|---|---|---|---|---|
| SciDocs | `data/raw/beir/scidocs/` | `data/processed/beir/scidocs/`, `data/processed/beir/scidocs/pairwise/` | only `.gitkeep` | placeholder only; no real/proxy JSONL | No |
| FiQA | `data/raw/beir/fiqa/` | `data/processed/beir/fiqa/`, `data/processed/beir/fiqa/pairwise/` | only `.gitkeep` | placeholder only; no real/proxy JSONL | No |
| HotpotQA | `data/raw/hotpotqa/` | `data/processed/hotpotqa/`, `data/processed/hotpotqa/pairwise/` | only `.gitkeep` | placeholder only; no real/proxy JSONL | No |
| BRIGHT | `data/raw/bright/` | `data/processed/bright/`, `data/processed/bright/pairwise/` | only `.gitkeep` | placeholder only; no real/proxy JSONL; no manual README currently present | No |

### Local presence conclusion

- I found **no local real dataset files** for any of the four datasets.
- I also found **no local proxy-generated data** and **no local partial JSONL data**; the repo only contains empty placeholder directories.
- There is **no alternate local cache path** currently populated with these datasets, either in repo-defined locations or in standard Hugging Face cache directories.

## 2. Download / preparation pipeline inspection

### What the pipeline uses

| Stage | Script / function | What it checks |
|---|---|---|
| Dataset path definition | `src/consistency_ranker/data/dataset_registry.py` | Hard-coded `raw_path` / `processed_path` for each dataset under `data/raw/...` and `data/processed/...`. |
| Raw download presence check | `scripts/download_datasets.py::_raw_files_exist` | Considers a dataset already downloaded only if `queries.jsonl` **and** `documents.jsonl` exist in the dataset raw path. |
| Raw -> processed preparation | `scripts/prepare_datasets.py` | Requires `queries.jsonl`, `documents.jsonl`, and `qrels.jsonl` in the raw path. |
| Processed data load for experiments | `src/consistency_ranker/data/unified_loader.py::load_dataset_splits` | Requires `queries.jsonl`, `documents.jsonl`, and `qrels.jsonl` under the processed path. |
| Pairwise preference generation | `scripts/prepare_datasets.py::_generate_preferences` | Writes `pairwise/preferences.jsonl` under the processed path if processed `qrels.jsonl` exists. |

### Per-dataset expected files

| Dataset | Download script/function | Raw files expected by prepare step | Processed files expected by experiment step | How "available" is decided |
|---|---|---|---|---|
| SciDocs | `scripts/download_datasets.py::download_beir('scidocs')` → `beir_loader.download_beir_dataset` | `data/raw/beir/scidocs/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | `data/processed/beir/scidocs/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | download step skips if `queries.jsonl` and `documents.jsonl` exist; experiment still requires processed JSONL |
| FiQA | `scripts/download_datasets.py::download_beir('fiqa')` → `beir_loader.download_beir_dataset` | `data/raw/beir/fiqa/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | `data/processed/beir/fiqa/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | same as SciDocs |
| HotpotQA | `scripts/download_datasets.py::download_hotpotqa` → `hotpotqa_loader.download_hotpotqa` | `data/raw/hotpotqa/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | `data/processed/hotpotqa/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | same raw/processed logic |
| BRIGHT | `scripts/download_datasets.py::download_bright` → `bright_loader.download_bright` | `data/raw/bright/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | `data/processed/bright/queries.jsonl`, `documents.jsonl`, `qrels.jsonl` | same raw/processed logic, but loader explicitly falls back to manual instructions when download fails |

### Could the previous conclusion have missed another valid path?

- I found **no code path** that points to an alternate repo location beyond the registry-defined `data/raw/...` and `data/processed/...` directories. 
- I found **no environment-variable override** for dataset storage paths. 
- I found **no populated Hugging Face cache** in the current environment. 
- Therefore, for the current checkout/environment, the earlier conclusion did **not** miss a second valid local path.

## 3. Remote / internet access verification

### Remote sources used by the repository

| Dataset | Remote source used by code |
|---|---|
| SciDocs | Hugging Face datasets: `BeIR/scidocs` and `BeIR/scidocs-qrels` |
| FiQA | Hugging Face datasets: `BeIR/fiqa` and `BeIR/fiqa-qrels` |
| HotpotQA | Hugging Face dataset: `hotpot_qa` with config `fullwiki` |
| BRIGHT | Hugging Face dataset: `xlangai/BRIGHT` |

### Verified remote-access results in this environment

| Dataset | Metadata check (`HfApi().dataset_info`) | Minimal data access check (`datasets.load_dataset`) | Result |
|---|---|---|---|
| SciDocs | `ProxyError 403 Forbidden` | `ProxyError 403 Forbidden` | remote download fails |
| FiQA | `ProxyError 403 Forbidden` | `ProxyError 403 Forbidden` | remote download fails |
| HotpotQA | `ProxyError 403 Forbidden` | `ProxyError 403 Forbidden` | remote download fails |
| BRIGHT | `ProxyError 403 Forbidden` | `ProxyError 403 Forbidden` | remote download fails |

### Exact error evidence

- `requests.get("https://huggingface.co")` failed with: `ProxyError(MaxRetryError("HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: / (Caused by ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403 Forbidden')))"))`.
- `datasets.load_dataset('hotpot_qa', 'fullwiki', split='validation[:1]')` failed with:

```text
httpx.ProxyError: 403 Forbidden
TYPE: <class 'httpx.ProxyError'>
REPR: ProxyError('403 Forbidden')
```

### Failure cause assessment

- **Current failure cause:** proxy/network restriction in the present environment.
- **What I did not observe:** authentication prompts, gated-access acceptance errors, 404s, or incorrect dataset IDs.
- **Nuance for BRIGHT:** the code still explicitly anticipates that BRIGHT may require manual download even in a healthy networked environment, because access terms or dataset gating may apply.

## 4. Evidence of previous working access / artifacts

### What I searched for

- checked `outputs/` for real-data results such as `*_per_query.csv`, `*_summary.csv`, real-data timing files, and `outputs/real_signal/...`;
- checked `data/raw/...` and `data/processed/...` for actual JSONL content;
- checked standard local cache directories;
- checked `git log --all --stat -- data/raw data/processed outputs`;
- checked repo docs and README for prior successful commands or result references.

### Findings

| Dataset | Evidence it worked before? | Exact evidence | Why it may not work now |
|---|---|---|---|
| SciDocs | No direct success evidence | README and docs describe intended commands; no local files, no real outputs, no cached downloads, no committed per-query/summary results | current environment cannot reach Hugging Face because proxy tunnel returns 403 |
| FiQA | No direct success evidence | same as SciDocs | same |
| HotpotQA | No direct success evidence; one direct failure record exists | `docs/tables/bootstrap_results.csv` records a blocked HotpotQA download attempt with `httpx.ProxyError` / `403 Forbidden` | same proxy restriction |
| BRIGHT | No direct success evidence | code/tests cover loader behavior and manual fallback, but there are no local BRIGHT JSONL files or result artifacts | proxy restriction blocks even metadata access; BRIGHT may also require gated/manual steps outside this environment |

### Git-history evidence

- The repository history shows that real-data support was **added in code** and placeholder raw/processed directories were created, but I found **no commit adding actual real datasets** and **no commit adding real-data experiment outputs**.
- The strongest prior evidence is therefore **implementation readiness**, not proof of prior successful dataset availability in this checkout.

## 5. True status by dataset

| Dataset | Exact classification | Why |
|---|---|---|
| SciDocs | MANUAL ACTION REQUIRED | no local real/proxy/partial data; remote metadata and minimal download checks both fail with `ProxyError 403 Forbidden` |
| FiQA | MANUAL ACTION REQUIRED | no local real/proxy/partial data; remote metadata and minimal download checks both fail with `ProxyError 403 Forbidden` |
| HotpotQA | MANUAL ACTION REQUIRED | no local real/proxy/partial data; remote metadata and minimal download checks both fail with `ProxyError 403 Forbidden` |
| BRIGHT | MANUAL ACTION REQUIRED | no local real/proxy/partial data; remote metadata and minimal download checks both fail with `ProxyError 403 Forbidden`; code also explicitly supports manual fallback for BRIGHT |

## 6. Final verdict

### A. Which datasets definitely do **not** need manual help

- **None, in the current checkout/environment.**

### B. Which datasets definitely **do** need manual help

- **SciDocs**
- **FiQA**
- **HotpotQA**
- **BRIGHT**

For the first three, the manual help may simply be "run the downloads from a machine/network that can actually reach Hugging Face, then prepare the data and copy it here." For BRIGHT, manual help may also include accepting access terms and/or exporting JSONL manually.

### C. Which datasets are ambiguous and why

- **None are ambiguous in the current environment.**
- The only nuance is **scope**: the repository codebase itself supports automatic download paths for SciDocs, FiQA, and HotpotQA, so manual help is not necessarily a permanent property of the project; it is a property of the **current checkout + current network environment**.

### D. Was the previous **"MANUAL ACTION REQUIRED"** conclusion fully correct?

- **Partially correct.**
- It was **correct for the current checkout/environment**, because there is no local real data and remote access is currently blocked by a proxy returning `403 Forbidden`.
- It was **too broad if interpreted as a repository-wide permanent fact**, because the code clearly implements automatic download/prepare flows for SciDocs, FiQA, and HotpotQA; those flows are simply not usable from this environment right now.
