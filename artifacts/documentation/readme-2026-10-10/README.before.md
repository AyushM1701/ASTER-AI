<p align="center">
  <img src="docs/banner.jpg" alt="Aster Medical Research" width="100%">
</p>

<h1 align="center">Aster Medical Research</h1>

<p align="center">
  <strong>A dark ambient, source-backed medical education workspace — fully local, fully traceable.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%E2%80%933.13-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11–3.13">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Qwen3--VL_2B-7de0cb?style=flat-square" alt="Qwen3-VL 2B">
  <img src="https://img.shields.io/badge/Tesseract_OCR-5.5.3-4285F4?style=flat-square" alt="Tesseract OCR">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Platform: Windows">
  <img src="https://img.shields.io/badge/license-local_research-e9bf7e?style=flat-square" alt="Local Research Only">
</p>

---

> [!CAUTION]
> **Education and local research only.** No autonomous diagnosis, medication selection, personal dose
> calculation, treatment changes, or assurance that an X-ray is normal. English first. Use synthetic
> documents and permitted de-identified images. Engineering checks are not clinical validation.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Datasets & Knowledge Library](#-datasets--knowledge-library)
- [Quick Start](#-quick-start)
- [Shared Vision & Chat Model](#-shared-vision--chat-model)
- [OCR Setup](#-ocr-setup)
- [Optional Local Models](#-optional-local-models)
- [Configuration](#%EF%B8%8F-configuration)
- [Verification & Evidence](#-verification--evidence)
- [Curriculum Teaching Library](#-curriculum-teaching-library)
- [Privacy & Deployment Limits](#-privacy--deployment-limits)
- [Sources & Attribution](#-sources--attribution)
- [Troubleshooting](#-troubleshooting)

---

## 🔭 Overview

Aster is a dark ambient local workspace built from `Medical_AI_End_to_End_Blueprint.md`.
Python + FastAPI backend with a dedicated HTML/CSS/JavaScript frontend, featuring real
Tesseract OCR, explicit transcription confirmation, traceable source notes, and optional
local model adapters. One chat holds questions, attachments, classifications, transcription
review and results.

The interface implements the approved dark ambient Figma redesign with locally hosted fonts,
responsive navigation and a persistent composer. See [design implementation](docs/web-redesign.md).
The earlier Streamlit UI remains in source as a legacy fallback.

Use the **link icon beside Message Aster** to attach a PNG/JPEG prescription or X-ray.
The configured vision model examines the pixels and classifies: prescription, X-ray, other,
or uncertain. Prescriptions are transcribed automatically, then require **Confirm and explain**.
X-ray routing checks reviewed registration before any specialist research scores. Unclear
images stay unresolved, and a missing classifier has an explicit retry state.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🩺 Medical Education
Nine developer-curated note sets covering asthma, blood pressure, sleep apnea,
diabetes, pneumonia, anemia, COPD, pleural disorders, and a metformin label.
Every reference statement has a stable citation, source note, snapshot and primary URL.
Unsupported questions abstain. Urgent-language checks run without a model.

</td>
<td width="50%">

### 📄 Document Reader
One PNG/JPEG at a time, actual local OCR, editable fields, explicit user acknowledgement,
backend ownership and current-revision checks. Blank fields stay unresolved. Changes
invalidate confirmation and explanations. Use **Try a sample prescription**, compare
fields, then **Confirm and explain**.

</td>
</tr>
<tr>
<td width="50%">

### 🫁 Chest X-ray Research
Manifest validation, file hashes, view/adult/provenance gates, technical checks,
exact preprocessing, and inference against cached TorchXRayVision weights.
**Scoring is enabled** for two reviewed NIH adult PA research samples. The checkpoint
matches the publisher's SHA-256. See [current X-ray setup](docs/xray_setup.md).

</td>
<td width="50%">

### 🔒 Sessions & Security
Random 256-bit tokens, server-side hash lookup, ownership checks, inactivity/hard
expiry, bounded state, deletion and no automatic chat exports. Services bound to
`127.0.0.1` only.

</td>
</tr>
</table>

---

## 🏗 Architecture

```
Browser ──► Same-origin FastAPI web bridge ──► Server-side httpx ──► Research API
                                                     │
                          ┌──────────────────────────┤
                          ▼                          ▼                    ▼
                     Policy Engine         Retrieval / OCR        Curated Imaging
                          │                     │                    Adapters
                          ▼                     ▼                       │
                    Owned State          Source Store /             TorchXRayVision
                    + Sessions          Vector Index (NumPy)        (CPU-only)
```

The browser never calls Ollama directly. The web bridge has a fixed loopback upstream,
a route allowlist, an 11 MiB body limit, same-origin request checks, and no CORS permission.
A self-only Content Security Policy covers scripts, fonts and styles.

---

## 📊 Datasets & Knowledge Library

Aster runs **Knowledge Library v2**, extended with the user-approved Indian retailer dataset.

| Dataset | Documents | Sections | Source |
|:--------|----------:|---------:|:-------|
| **Curated medical education** | 92 | 250 | MedlinePlus, NHLBI, DailyMed, ICMR, GSK India, NLEM 2022 |
| **Indian retailer medicines** (Netmeds) | 23,939 | 266,620 | `drowsyng/medicines-dataset` (Kaggle, Apache 2.0) |
| **Combined primary library** | **24,031** | **266,870** | Hybrid MiniLM/NumPy + lexical search |
| **Secondary medicine layer** | 3,408 linked products | 6,670 notes | A-Z + HF Indian datasets (user-authorized, unverified) |
| **Kaggle candidate catalogue** | — | 253,973 rows | Unverified, separate from clinical retrieval |
| **Teaching curriculum** (MBBS + MDS) | 201 units | 2,916 sections | 41 explanations, 112 source-review holds |

The original 250 curated sections retain hybrid MiniLM/NumPy search; retailer medicines use
exact identity and lexical section ranking. Local Qwen answers are checked against complete
source sections.

**Secondary layer** — both Indian medicine datasets contribute 6,670 notes linked to 3,408
Netmeds products. Answers that cite these notes show a caution caption and retain dataset
provenance. See [secondary data behavior](SECONDARY_MEDICINE_DATA.md) and
[secondary evaluation](SECONDARY_MEDICINE_DATA_EVALUATION.md).

> [!NOTE]
> This is retrieval expansion, not medical fine-tuning or qualified clinical validation.
> Read the [retailer integration guide](NETMEDS_CLINICAL_LIBRARY.md),
> [library guide](KNOWLEDGE_LIBRARY_V2.md) and
> [measured evaluation](KNOWLEDGE_LIBRARY_V2_EVALUATION.md).

---

## 🚀 Quick Start

> **Requires:** Python 3.11–3.13 (verified with 3.13.3). The project has its own `.venv`;
> no global package modifications needed.

### Windows

```powershell
cd 'C:\Users\AYUSH\Documents\AI doctor'
.\setup.ps1
.\start.ps1
```

Open the workspace at [`http://127.0.0.1:8501`](http://127.0.0.1:8501) and optionally
the [API documentation](http://127.0.0.1:8000/docs).

`start.ps1` starts one API worker and the UI on loopback, opens a browser, and stops
both children when you press <kbd>Ctrl</kbd>+<kbd>C</kbd>. It refuses occupied ports
rather than killing an existing service. Use `-NoBrowser` to suppress opening a browser.

<details>
<summary><strong>Manual startup (if PowerShell script execution is restricted)</strong></summary>

```powershell
# Terminal 1 — API
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log

# Terminal 2 — UI (from the project root)
.\.venv\Scripts\python.exe -m uvicorn frontend.webserver:app --host 127.0.0.1 --port 8501 --workers 1 --no-access-log
```

</details>

### Linux / macOS

Create `.venv` with `python3 -m venv .venv`, install `requirements.lock.txt`, and replace
`.venv\Scripts\python.exe` with `.venv/bin/python`. The exact lock was measured on Windows;
other operating systems and Python versions still require a fresh compatibility check.

---

## 🤖 Shared Vision & Chat Model

The chat supports one locally running pretrained model for text and image routing:
[**Qwen3-VL 2B Instruct**](https://ollama.com/library/qwen3-vl:2b-instruct).
This is inference with pretrained weights — not medical fine-tuning or a guarantee
of answering every question.

| Resource | Size |
|:---------|-----:|
| Pinned Windows runtime | ~1.5 GB |
| Model weights | ~1.9 GB |

### Setup

```powershell
.\setup-chat.ps1
```

Set these entries in `.env`, then restart with `start.ps1`:

```dotenv
ANSWER_MODE=ollama
TEXT_MODEL=qwen3-vl:2b-instruct
VISION_MODEL=qwen3-vl:2b-instruct
ENABLE_GENERAL_CHAT=true
```

The launcher runs the project-local standalone Ollama on loopback with cloud features
disabled and models under `data/models/ollama-store`. It stops the inference server it
started when the launcher exits and never kills an existing server.

<details>
<summary><strong>How the model is used</strong></summary>

- Supported local reference topics retain structured source-backed answers
- Unsupported medical requests receive insufficient evidence
- General chat is limited to explicitly recognized nonmedical requests and uses
  pretrained model knowledge without local medical citations
- Urgency, personal dosing and diagnosis gates still run first
- Previous turns and confirmed transcription are bounded context; unconfirmed OCR
  is never silently used as conversation context

The downloaded model digest is recorded in `configs/models.yaml`. Four small live
integration demonstrations passed. That is not clinical validation or broad classifier
accuracy.

</details>

---

## 📋 OCR Setup

Install Tesseract and English language data using the
[Tesseract platform instructions](https://tesseract-ocr.github.io/tessdoc/Installation.html).
This machine has **Tesseract 5.5.3** at `C:\Program Files\Tesseract-OCR\tesseract.exe`;
the app detects that path or PATH automatically. Set `TESSERACT_CMD` in `.env` for a
different location.

This installation enables experimental local English handwriting transcription with
`ENABLE_HANDWRITING_OCR=true` and the existing vision model.

> [!WARNING]
> The measured handwriting probe read only **10/37** medicine words exactly and failed
> to flag **27 wrong readings**. It is not reliable for unattended prescription reading.
> Obtain prescriber/pharmacist clarification for unclear names or doses.
> See [all evaluation scores and handwriting limitations](EVALUATION_REPORT.md).

---

## 🔧 Optional Local Models

### Ollama

Install from [Ollama](https://ollama.com/download), keep its server on loopback,
and explicitly acquire the text model:

```powershell
ollama pull llama3:8b
ollama list
```

Set `ANSWER_MODE=ollama` in `.env`, restart the API and run `scripts/verify_assets.py`.
The [chat adapter](https://docs.ollama.com/api/chat) uses structured JSON, bounded
timeouts, one shared client, no tools and no cloud fallback. Run the evaluation again
after a model change and record the exact installed digest in `configs/models.yaml`.

### MiniLM & Offline Vector Index

Install a compatible matched PyTorch/torchvision pair using the
[official selector](https://pytorch.org/get-started/locally/), then install
`requirements-models.txt`. The installed immutable revision is recorded with file
hashes in `data/models/minilm/aster-model-manifest.json`; the official source is the
[MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-models.txt
.\.venv\Scripts\python.exe scripts/install_embeddings.py
.\.venv\Scripts\python.exe scripts/ingest.py \
  --sources data/references/releases/aster-v2-2026-10-07/sources.yaml \
  --corpus data/references/releases/aster-v2-2026-10-07/records.jsonl \
  --output data/indexes/NEW_INDEX \
  --backend hybrid \
  --collection medical_reference_v2
```

The active v2 profile uses `RETRIEVAL_BACKEND=hybrid` with MiniLM and an exact offline
NumPy vector index. See [Knowledge Library v2](KNOWLEDGE_LIBRARY_V2.md) for current
install, rebuild, review, evaluation and rollback commands. Chroma was benchmarked and
removed after the 2026-10-07 dependency audit.

### Chest X-ray Research

> [!IMPORTANT]
> Read [the model card](docs/xray_model_card.md) before acquiring images or weights.

After installing optional model dependencies:

```powershell
.\.venv\Scripts\python.exe scripts/setup_assets.py xray
.\.venv\Scripts\python.exe scripts/register_xray.py \
  --asset-id your-reviewed-id \
  --path 'C:\permitted-data\image.png' \
  --source 'Verified provenance' \
  --license 'Verified permission or license' \
  --view PA --patient-group opaque-group \
  --partition demo --reviewed-adult-deidentified
```

The review flag is an operator attestation, not an image classifier. Supply reliable
metadata and actual permission; do not infer adult status, AP/PA, or de-identification
from the image's appearance. Set `ENABLE_XRAY=true`, restart, then select a registered
image. The model is CPU-only in this implementation. Labels stay in model order; selected
outputs are operating-point-normalized **research scores**, never diagnostic confidence.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` if needed. Paths resolve against the repository.

| Setting | Default | Purpose |
|:--------|:--------|:--------|
| `ANSWER_MODE` | `extractive` | Explicit extractive or local Ollama generation |
| `RETRIEVAL_BACKEND` | `lexical` | Base default; this workspace uses hybrid lexical + cached MiniLM/NumPy |
| `OLLAMA_BASE_URL` | loopback :11434 | Remote or credential-bearing URLs rejected |
| `TEXT_MODEL` | `llama3:8b` | Exact tag required when generation is enabled |
| `VISION_MODEL` | `qwen3-vl:2b-instruct` | Shared vision and routing model |
| `TESSERACT_CMD` | auto detection | Local OCR executable |
| `ENABLE_HANDWRITING_OCR` | `false` | Experimental English transcription using the local vision model |
| `ENABLE_GENERAL_CHAT` | `false` | Allow nonmedical pretrained-model responses |
| `MAX_UPLOAD_BYTES` | 10 MB | Checked while reading, with bounded request framing |
| `MAX_IMAGE_PIXELS` | 20 million | Decoded image limit; session memory budget also applies |
| `MAX_SESSION_BYTES` | 30 MB | Reserves decoded image/preview memory before expansion |
| `MAX_DOCUMENTS_PER_SESSION` | 5 | Bounds retained uploads |
| `SESSION_TTL_SECONDS` | 1800 | Inactivity lifetime |
| `SESSION_HARD_TTL_SECONDS` | 7200 | Lifetime regardless of activity |
| `MAX_ACTIVE_SESSIONS` | 20 | Single-process capacity |
| `MAX_QUEUE_SIZE` | 4 | Bounded waiting for one expensive computation |
| `INFERENCE_TIMEOUT_SECONDS` | 180 | Generation and compute queue bound |
| `OCR_TIMEOUT_SECONDS` | 30 | Tesseract subprocess timeout |
| `ENABLE_XRAY` | `false` | Requires optional dependencies, weights and curated assets |

---

## 🧪 Verification & Evidence

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend frontend scripts tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit
.\.venv\Scripts\python.exe scripts/verify_assets.py
.\.venv\Scripts\python.exe scripts/ingest.py --sources configs/sources.yaml --output data/indexes/reference_v1 --dry-run
.\.venv\Scripts\python.exe scripts/evaluate_rag.py --dataset data/evaluation/rag_dev.jsonl --output artifacts/evaluation/rag-dev
.\.venv\Scripts\python.exe scripts/evaluate_ocr.py --output artifacts/evaluation/ocr
```

Actual reports live in `artifacts/evaluation/`. The initial fixed development suite
routed 40/40 cases as annotated and returned valid citation IDs. The one printed
synthetic OCR sample had exact transcription and all seven expected fields.

> [!NOTE]
> These are engineering observations only — not held-out clinical accuracy, prescription
> reliability or triage validation. See [release evidence](docs/engineering_report.md).

<details>
<summary><strong>X-ray evaluation details</strong></summary>

`evaluate_xray.py` requires a reviewed image manifest and a versioned protocol bound
to the checkpoint and exact manifest hashes. It rejects duplicate images, patient
partition leakage and unresolved training overlap for independent runs. It computes
per-finding AUROC, average precision, sensitivity, specificity and precision at
predeclared thresholds, with patient-bootstrap intervals when defined.

Real CPU inference passed on two installed NIH demo images using `--integration-only`;
diagnostic metrics were withheld. The CheXpert metadata audit found zero shared patient
IDs in its checked tables, but complete training exclusion and provider-authorized test
images are still pending. See the [PCOM research report](PCOM_RESEARCH_IMPROVEMENTS.md).

</details>

---

## 📚 Curriculum Teaching Library

The combined **MBBS and MDS** teaching expansion is active through `configs/teaching.env`,
which loads before `.env`. The current hybrid collection contains:

| Component | Count |
|:----------|------:|
| Sections | 2,916 |
| Publisher pages / chapter / article units | 201 |
| Source-bound plain-language explanations | 41 |
| Source-review holds | 112 |

The precision-improved chat preserves medical qualifiers, marks missing topics, and prevents
unsupported teaching questions from falling back to unrelated primary notes. All **392 software
tests** and **115 live routing/context checks** pass. The fixed 66-question developer challenge
has **68/68** citation contexts matching relevance patterns (vs 47/68 before).

See [precision improvements](ASTER_PRECISION_IMPROVEMENTS.md) ·
[comprehensive audit](ASTER_COMPREHENSIVE_AUDIT_v2.md) ·
[MBBS evaluation](MBBS_LIBRARY_EVALUATION.md) ·
[MDS study materials](MDS_STUDY_MATERIALS.md)

<details>
<summary><strong>Build scripts for teaching library</strong></summary>

Use `requirements-teaching.txt` for optional preparation dependencies after the existing
local model setup.

| Script | Purpose |
|:-------|:--------|
| `scripts/build_mbbs_library.py` | Creates new immutable source release from permitted pinned snapshots |
| `scripts/build_teaching_index.py` | Builds matching semantic index |
| `scripts/build_teaching_explanations.py` | Binds manually authored notes to exact source hashes |
| `scripts/evaluate_mbbs.py` | Records fresh evaluation artifacts |
| `scripts/activate_teaching.py` | Validates pinned final profile before `--activate` |
| `scripts/smoke_mbbs.py` | Exercises actual browser bridge with synthetic questions |

For MDS expansion, use the pinned `configs/mds_*_sources.json` acquisition configurations
with `scripts/build_mds_dental.py`, `scripts/build_mds_research.py` and
`scripts/build_mds_statistics.py`. `scripts/build_mds_notes.py` binds the bounded
explanations and holds; `scripts/compose_mds_library.py` preserves the existing MBBS
release while composing a fresh immutable combined version.

</details>

---

## 🔐 Privacy & Deployment Limits

The local app sends inputs to its loopback API and, only when configured, loopback Ollama.
It **never** fetches user-provided URLs or sends inputs to a cloud fallback.

| Aspect | Behavior |
|:-------|:---------|
| **Reference data** | Persists locally |
| **Uploads, OCR, confirmations** | Process/session state only |
| **Browser data** | Page memory only — no localStorage, no automatic exports |
| **Logs** | Route templates, status, request IDs — no question text or tokens |
| **Telemetry** | None; fonts and icons served locally |
| **Session lifecycle** | Reloading starts a new session; abandoned sessions expire |
| **Temp files** | Multipart handling may spool to OS temp; files closed after requests |

> [!WARNING]
> Full network-isolation/packet capture and OS temporary-storage audits have not been
> performed. No shared/public deployment, clinical authentication system, regulatory
> approval or medical-policy review is included. Keep services bound to `127.0.0.1`
> and use one worker.

---

## 📖 Sources & Attribution

The linked primary pages were checked during this build. Notes are short original
paraphrases with a developer review record and content checksum; they are not complete
guideline or label copies.

**NHLBI source attribution:** National Heart, Lung, and Blood Institute; National
Institutes of Health; U.S. Department of Health and Human Services. No NIH endorsement
is implied. See the [NHLBI use policy](https://www.nhlbi.nih.gov/about/contact/trademark-branding-and-logo).

The US metformin label is a reference for its exact formulation; it is not an Indian
product instruction. The source register and normalized notes are in
`configs/sources.yaml` and `data/references/normalized/seed.jsonl`.

---

## 🛠 Troubleshooting

| Problem | Solution |
|:--------|:---------|
| API unavailable | Start both services; refresh status. `/health/live` tests the process, `/health/ready` reports component availability |
| Session expired | Start a new session. Old upload/result IDs cannot be recovered |
| OCR unavailable | Check executable and English language pack; never use guessed text |
| Confirmation conflict | Reload the current revision and compare again |
| No matching medicine reference | Check exact name, strength, formulation and route; unresolved fields or unsupported products require professional clarification |
| Missing imaging model | Run explicit asset setup, verify the manifest, and register permitted images. Missing resources never trigger runtime downloads |
| Dependency/model upgrade changes results | Retain the previous lock and corpus, build a new index if needed, and rerun the fixed suite before switching versions |

---

<p align="center">
  <sub>Built with 🩺 for local medical education research · Not for clinical use</sub>
</p>
