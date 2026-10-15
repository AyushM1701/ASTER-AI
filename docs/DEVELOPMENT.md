# Developing Aster

This guide is for contributors. Ordinary users should follow the README's
**Install and start** section instead; they never need Python, Ollama or a terminal.

## Source environment (Windows)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`tools/dev/setup.ps1` does the same. `tools/dev/setup-chat.ps1` downloads a portable Ollama runtime into
`data/models/ollama-runtime/`. Serve it with the repository's model store:

```powershell
$env:OLLAMA_MODELS="$PWD\data\models\ollama-store"; .\data\models\ollama-runtime\ollama.exe serve
```

Local assets used by the grounded engine (not committed; produced by the library and model steps below):

| Path | Contents |
|---|---|
| `data/library/installed/` | installed signed packs (`active.json`, `packs/<id>/index/`) |
| `data/models/minilm/` | all-MiniLM-L6-v2 tokenizer + `onnx/model.onnx` |
| `data/models/nli-deberta-v3-xsmall/` | NLI cross-encoder (int8 ONNX) for claim verification |
| `data/models/medcpt-cross-encoder/` | MedCPT reranker (int8 ONNX export) |
| `data/models/xray/onnx/` | ONNX exports of the TorchXRayVision models (`packaging/export_xray_onnx.py`) |
| Ollama models | `qwen3-vl:2b-instruct`, optionally `qwen3:4b-q4_K_M` |
| Tesseract | `C:\Program Files\Tesseract-OCR` or `TESSERACT_CMD` |

Run the API with the grounded engine against a local Ollama:

```powershell
$env:ANSWER_ENGINE='grounded'; $env:ANSWER_MODE='ollama'; $env:TEXT_MODEL='qwen3:4b-q4_K_M'
$env:ENABLE_GENERAL_CHAT='true'; $env:ENABLE_XRAY_UPLOADS='true'; $env:ENABLE_HANDWRITING_OCR='true'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m uvicorn frontend.webserver:app --host 127.0.0.1 --port 8501
```

`GET /health/selftest` exercises retrieval, the claim verifier, OCR and the X-ray gates.
The legacy extractive pipeline remains available with `ANSWER_ENGINE=legacy`
(earlier instructions: [docs/history/README-2026-10-11.md](history/README-2026-10-11.md)).

## Reference library

```powershell
python -m aster_library.build acquire --provider all          # Europe PMC, MedlinePlus, openFDA, OpenStax, legacy pack
python -m aster_library.build acquire --provider europepmc-gapfill
python -m aster_library.build pack --version 2026.10.15
python -m aster_library.build index --pack data/library/packs/aster-library-core-2026.10.15   # GPU via onnxruntime-directml if present
python -m aster_library.build report --pack data/library/packs/aster-library-core-2026.10.15
```

Acquisition is resumable (HTTP cache and per-document checkpoints in `data/library-work`) and
rate-limited per provider. `--refresh` searches for material published since the last run. The query
plan is `configs/library/query_plan.json`; the drug list is `configs/library/drug_list.json`.
Packs are signed with the Ed25519 key at `~/.aster-release/aster-signing-ed25519.pem` (or
`ASTER_SIGNING_KEY`); its public key is `configs/release/signing-public-key.pem`.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend aster_library aster_release packaging evaluation
node --check frontend/web/app.js
python evaluation/run_eval.py --api http://127.0.0.1:8000 --split dev --out evaluation/runs/<name>
python evaluation/score_eval.py --run evaluation/runs/<name>
```

The evaluation set (`evaluation/eval_set_v1.jsonl`) was frozen before tuning; the runner refuses a
modified file. Only the `dev` split may be inspected while tuning; `holdout` is for final reports.
X-ray gate calibration: `evaluation/xray/*.py`. Handwriting: `evaluation/handwriting/*.py`.

## Release candidate

```powershell
python packaging/build_release.py --version 0.2.0-rc.1 --library-version 2026.10.15 --out D:/aster-release
python -m aster_release.acceptance_v2 --assets D:/aster-release/0.2.0-rc.1/assets --report D:/aster-release/0.2.0-rc.1/acceptance.json
```

The builder freezes the launcher/API/web bridge (no torch), stages components, splits large
assets below GitHub's 2 GiB limit, writes and signs `release-lock.json`, builds
`AsterSetup-Windows-x64.exe` with the lock compiled in, and updates `release/bootstrap-pin.json`
(the pinned setup hash used by `Start Aster.cmd`). Commit both release files with the tag.
`.github/workflows/release-windows.yml` performs the same steps on the protected release runner
and creates a draft prerelease only. Upload the exact assets that passed acceptance: a rebuilt
setup or lock has different fingerprints from the ones pinned in `release/`.

## Repository layout

| Path | Purpose |
|---|---|
| `backend/app/` | FastAPI service: grounded engine (`services/grounded.py`), claim verification (`services/claim_support.py`), library store, prescriptions, X-ray, policy |
| `frontend/web/`, `frontend/webserver.py` | Workspace UI and its allow-listed same-origin bridge |
| `aster_library/` | Library acquisition providers, pack building, signing, indexing, install/update |
| `aster_release/` | Setup engine, launcher/controller, packaged acceptance runner |
| `packaging/` | PyInstaller specs, `build_release.py`, notices, `asset-rights-v2.csv` |
| `evaluation/` | Frozen evaluation set, runners and scorers; `runs/` is local only |
| `scripts/`, `research/` | Earlier curriculum, reference-pack and evaluation tooling, still exercised by tests |
| `docs/release-readiness/` | Acceptance report, ledger, library and X-ray evaluations, evidence |
| `docs/history/`, `docs/reports/` | Earlier plans, notes and generated reports, kept for the record |
