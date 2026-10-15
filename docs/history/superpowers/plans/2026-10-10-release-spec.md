# Aster Medical Research — End-to-End One-Click GitHub Release Blueprint

**Basis:** User-supplied `README(2).md`, project snapshot **10 October 2026**  
**Target:** Windows x64, single-user, loopback-only application  
**Primary outcome:** A new user downloads Aster, launches it, and can use the included AI without installing Python, Ollama, Tesseract, Qwen, MiniLM, TorchXRayVision, or running a model pull manually.  
**Document status:** Engineering implementation plan. The README was reviewed; the entire source repository and on-disk assets have **not** been audited. Code snippets and new filenames below are *proposals*, not claims that these files already exist.

---

## 0. Executive decision

Ship **two editions from one reproducible release build**:

1. **Aster Windows Offline (portable):** full, verified offline bundle, including permitted AI and data assets. Extract into a user-writable directory and launch `Aster.exe`. No initial network required. Because the bundle is larger than one GitHub Release asset limit, distribute a complete single archive through suitably sized artifact hosting, or offer a GitHub-only segmented archive with a guided extractor.
2. **Aster Windows Installer (recommended GitHub UX):** small signed (when feasible) installer or bootstrapper in GitHub Releases. It downloads a fixed, signed/checksummed version manifest and corresponding prepackaged assets, assembles the application automatically, verifies them, and launches Aster. **No model installation commands**; internet is required only for first-time installation and optional upgrades. The application subsequently runs offline.

These editions must use the **same pinned model revision and same allowed data/profile**. Do not silently substitute model tags or download a newer revision.

**Not the design:** a public multi-user web server, a cloud-model API, an LLM bundled *inside* the EXE as one giant monolith, running `pip install` on each user machine, or automatic `ollama pull` during a medical question.

### Definition of complete

On a clean supported Windows machine, `Aster.exe` must:

- start the bundled local inference service, the FastAPI API and the frontend;
- validate required model/index/source/teaching-note compatibility;
- expose the UI with a clear `Starting → Loading data → Loading AI → Ready` indicator;
- answer an eligible educational question with correct format, full citations, Simple/Deeper presentation where supported, and correct fallbacks;
- classify a permitted synthetic image and run printed OCR where enabled;
- work without network access after setup;
- cleanly close its **own** child processes, without touching unrelated local servers;
- keep all medical use limits and truthful feature-readiness indicators.

The product is **medical education and local research**, not clinical diagnosis, prescribing or X-ray reassurance. Model inclusion does not establish medical reliability.

---

## 1. Inventory: preserve what the 10 October README says is actually installed

| Layer | Active development snapshot / essential behavior | Release treatment |
|---|---|---|
| User interface | `frontend.webserver` on `127.0.0.1:8501`; static HTML/CSS/JS, local fonts/icons, server-side fixed bridge | Package unchanged where possible; no Node runtime required |
| Research API | `backend.app.main:app` on `127.0.0.1:8000`, **one worker** | Package separate service entrypoint; preserve one-worker session ownership |
| Inference | Project-local Ollama on `127.0.0.1:11434` | Include pinned Ollama standalone executable/libraries and isolated model store |
| Vision/text model | `qwen3-vl:2b-instruct`; configured `ANSWER_MODE=ollama` | Include full immutable Ollama model store and exact model digest; verify before use |
| Primary release | `aster-v2-netmeds-r2-2026-10-07` (266,870 sections) | Bundle *only* content cleared for redistribution; freeze source, index, manifest as matched set |
| Secondary release | `aster-secondary-v1-r2-2026-10-07` (6,670 notes) | Optional, explicitly unverified and rights-reviewed; never silently treat as prescribing data |
| Teaching release | `aster-teaching-epithelium-v1-2026-10-09` (2,916 sections, 43 checked explanations, 117 holds) | Bundle its selected release, explanation/hold records and explanation layouts as one profile |
| Teaching index | `data/indexes/comprehensive-audit-v1-2026-10-09` | Keep index manifest compatibility; **do not** infer from differing names |
| Dense encoder | `all-MiniLM-L6-v2` pinned revision; exact NumPy indexes | Include model revision/files, compatible CPU dependencies and required indexes |
| OCR | Tesseract, English; optional experimental Qwen vision transcription | Bundle runtime/DLLs/`eng.traineddata`; default experimental handwriting **off** for public safety |
| X-ray | TorchXRayVision `densenet121-res224-all` CPU; checkpoint 28,382,008 bytes; 2 registered NIH demos | Only bundle when weights and each image have documented redistribution permission; keep strict asset hash gating |
| Web/session security | Self-only CSP, loopback bindings, bridge allowlist/Origin/header checks, in-memory sessions | Preserve; no public listener, network tunneling, extra workers or account claims |
| Evidence | 466 Python tests; 137 live checks (on dev machine) | Establish *new* frozen-release test results; do not advertise as packaged acceptance |

**Important nuances from the updated README:**

- Base `setup.ps1` **does not** reconstruct the active full research installation. A Git checkout is not a complete install.
- Source/index manifests, embedding revision, note hashes, and presentation layouts are coupled.
- `.env` overrides `configs/teaching.env`; the copied example can set `ENABLE_TEACHING=false`, silently disabling teaching if not handled.
- **Only** the 250 curated reference sections use the primary dense index; retailer products use exact identity and lexical ranking. Teaching uses its own dense index. Do not regenerate a giant global embedding index unnecessarily.
- The default browser frontend is **not** the legacy Streamlit app. Do not package Streamlit or Node merely because legacy/development code exists.
- Uploads and sessions are intentionally not persisted. A restart or page reload cannot be represented as restoring earlier uploads.

---

## 2. Public-distribution rights gate — a release blocker

The README expressly states **there is no root `LICENSE` file granting an application-code license**. Before publishing the source and an executable:

1. Establish ownership and grant or reserve application code rights deliberately. Choose a root license if appropriate; never assume a dependency's Apache/MIT license licenses Aster's own code.
2. Create `packaging/asset-rights.csv` with: `asset_id`, `path/glob`, `origin`, `publisher`, `license/permission_basis`, `redistribution_allowed`, `modification_allowed`, `attribution`, `privacy_status`, `reviewer`, `review_date`, `decision`.
3. Separately assess the Qwen model *and exact weights*, standalone Ollama build, MiniLM revision, TorchXRayVision checkpoint, Tesseract Windows distribution + DLLs/English data, fonts, icons, all datasets, local source snapshots, and licensed article/chapter excerpts.
4. Verify the retailer dataset and second-hand datasets' rights per pinned versions. A developer authorization to acquire content is **not** necessarily permission to redistribute it.
5. Exclude private evaluation cases, private backups, real patient documents, questionable source copies, API keys, unlicensed images, and user-specific workstation files.
6. Build a `THIRD_PARTY_NOTICES.md` plus `licenses/` tree for every cleared third-party component; preserve source/jurisdiction/edition/attribution and relevant notices in the app.
7. Fail the public build when a required public asset has `redistribution_allowed != true`. There must be no `--ignore-license` shortcut in publish workflows.

**Use two content profiles if needed:**

- **Public Standard:** all proven-redistributable content; transparent feature flags for missing secondary, imaging, or restricted references; no misleading claims of 266,870-section coverage unless the full licensed corpus really ships.
- **Private/Authorized Research:** full exact development profile deployed only to recipients with rights to each asset. Do not assume that a publicly downloadable binary may ship restricted material.

The **prepackaged AI model** can be included while particular third-party datasets remain unavailable. This is preferable to silently publishing unlicensed data.

---

## 3. Choose packaging technology and process boundaries

### 3.1 Recommended build: multiple frozen executables + external data

Use a Windows-specific PyInstaller `--onedir` build (or an equivalent tested freezer). Create **three entrypoints**:

- `Aster.exe`: visible UI-less or small native launcher/controller; owns services and browser lifecycle.
- `aster-api.exe`: imports `backend.app.main:app` and calls `uvicorn.run(..., workers=1, host="127.0.0.1", port=8000)` *programmatically*.
- `aster-web.exe`: imports `frontend.webserver:app` and calls `uvicorn.run(..., workers=1, host="127.0.0.1", port=8501)` programmatically.

Include a separately packaged `runtime/ollama/ollama.exe`, executable dependencies and `runtime/tesseract/tesseract.exe` + supported DLLs and language data.

**Do not** attempt `sys.executable -m uvicorn ...` from a frozen `Aster.exe`: under PyInstaller `sys.executable` points to the bootloader executable, **not** a general-purpose Python interpreter. Distinct frozen service entrypoints avoid this trap.

PyInstaller module hooks/data inclusion for FastAPI/Pydantic/torch/transformers/NumPy/etc. will require testing against real source. Avoid building from `requirements*.txt` all together; the README says the optional model/teaching/X-ray locks have different measured profiles.

### 3.2 Example user-facing installed layout

```text
Aster/
├── Aster.exe                       # user's single launch target
├── bin/
│   ├── aster-api.exe
│   ├── aster-web.exe
│   └── _internal/                  # frozen Python shared/runtime dependencies
├── app/
│   ├── frontend/web/              # HTML/CSS/JS/fonts/icons
│   ├── configs/                   # release configs, manifests, presentation layouts
│   └── notices/                   # user-facing intended use, licenses
├── runtime/
│   ├── ollama/                    # pinned standalone CLI and GPU library dependencies
│   └── tesseract/                 # executable, DLLs, tessdata/eng.traineddata
├── assets/
│   ├── models/ollama-store/       # complete blobs + manifests for exact Qwen digest
│   ├── models/minilm/             # immutable MiniLM files/revision manifest
│   ├── models/xray/               # only if rights-cleared and enabled
│   ├── references/               # allowed release snapshots and registers
│   ├── indexes/                  # prebuilt, compatible primary+teaching indexes
│   ├── secondary/                # only if allowed in selected edition
│   ├── samples/                  # synthetic and permission-cleared demos only
│   └── xray/                     # only permission-cleared registered original files
├── release-manifest.json          # hash-locked package inventory + flags
└── THIRD_PARTY_NOTICES.md
```

All folder and executable names are **proposed**. The exact final layout is chosen only after testing import/resource path behavior.

Writable cache/log/report files belong under `%LOCALAPPDATA%\Aster\` (or a deliberate, documented portable writable directory), **not** in frozen `_internal/`. If portable assets must be updated, use a verified staging directory and atomic replacement. Do not require administrative rights.

**Windows version:** target Windows 10/11 x64 for the first release, but publish only the OS/GPU/CPU/RAM matrix actually verified. The README states ~23.7 GiB dev RAM, not a minimum requirement.

---

## 4. Package immutable assets, not ad hoc downloads

### 4.1 Build the immutable full-profile snapshot on your development PC

1. Create a clean staging build with pinned Python (README recorded 3.13.3) and a selected compatible dependency set.
2. Start from the **working profile** and run `scripts/verify_assets.py`.
3. Record checksums and sizes of every included model file, Ollama blobs/manifests, MiniLM encoder, CPU XRV checkpoint (if selected), source snapshots, source registers, normalized records, index manifests/vector files, teaching notes/holds and `configs/explanation_layouts.json`.
4. Preserve the **exact** `qwen3-vl:2b-instruct` content digest from `configs/models.yaml` and cross-check against the local Ollama store. Do not re-pull just to assemble the release: the tag may resolve to updated bytes.
5. Preserve primary reference release with its compatible **same-named** index; preserve teaching release with compatible `comprehensive-audit-v1-2026-10-09` index despite different directory names.
6. Include hash-bound teaching notes and all supported Simple/Deeper explanation-layout records. Their existence is a separate requirement from inclusion of the raw teaching records.
7. Include secondary index/manifests only if the selected public/private edition is permitted and it is explicitly enabled.
8. Remove temp caches/unnecessary duplicate old releases *from the distribution*, but maintain original archives in build storage for rollback.

### 4.2 Model bundle rules

- **Qwen/Ollama:** copy model manifests and all referenced blobs, not merely a visible model name or one `.gguf` file. Set `OLLAMA_MODELS` to the shipped store. Verify model load on an offline machine.
- **MiniLM:** bundle the exact pinned encoder revision; set the backend's local `EMBEDDING_PATH`, enable offline library loading and verify index/encoder compatibility.
- **TorchXRayVision:** include CPU-compatible torch + torchvision binaries/weights *only* in the imaging edition, unless one complete edition with explicit rights is desired. The README says imaging runs on CPU. No checkpoint fetching from the internet during inference.
- **Tesseract:** package legal redistribution of the chosen Windows build, dynamic DLLs, and `eng.traineddata`; explicitly point `TESSERACT_CMD` and tessdata resolution to packaged paths.
- **No runtime download fallback:** if a required asset is absent or corrupt, show an actionable `Repair installation` state. Do not quietly switch to a different model, remote endpoint, or incompatible references.

### 4.3 Example release manifest structure (proposed)

```json
{
  "schema_version": 1,
  "product": "Aster Medical Research",
  "app_version": "1.0.0",
  "edition": "windows-public-standard",
  "os": "windows-x64",
  "model": {
    "tag": "qwen3-vl:2b-instruct",
    "expected_digest": "REPLACE_WITH_VERIFIED_DIGEST",
    "store_path": "assets/models/ollama-store"
  },
  "reference": {
    "release": "aster-v2-netmeds-r2-2026-10-07",
    "included": false,
    "reason": "Example only: set true only after redistribution audit"
  },
  "teaching": {
    "release": "aster-teaching-epithelium-v1-2026-10-09",
    "index": "comprehensive-audit-v1-2026-10-09",
    "included": false
  },
  "features": {
    "general_chat": true,
    "teaching": false,
    "secondary_references": false,
    "handwriting_ocr": false,
    "xray_research": false
  },
  "files": [
    {"path": "assets/EXAMPLE", "size": 0,
     "sha256": "REPLACE_WITH_ACTUAL_FILE_SHA256"}
  ]
}
```

The example intentionally marks unreviewed corpus permissions and optional features **off**. Build scripts must generate the real hashes and accurate flags, never ship placeholders. Bind release-asset downloads to a trusted manifest whose integrity is authenticated, not merely checksums downloaded from the same untrusted location.

---

## 5. Explicit runtime configuration — avoid the documented `.env` trap

A normal checkout loads developer-facing defaults. The bundle must instead supply a deterministic **release profile**.

**Critical precedence from README:** explicit `Settings(...)` args, then process environment, then `.env`, then `configs/teaching.env`, then defaults. `.env.example` sets `ENABLE_TEACHING=false`.

### 5.1 Production approach

- **Never** run `setup.ps1` on end-user machines; don't copy a development `.env` into the installer.
- The launcher reads only trusted, packaged `release-manifest.json`/`release-profile.json`, verifies them, and sets **all relevant process environment variables** before spawning API and UI.
- Process environment must override any stray `.env`, including `ENABLE_TEACHING`, `TEACHING_BACKEND`, `ANSWER_MODE`, `TEXT_MODEL`, `VISION_MODEL`, `RETRIEVAL_BACKEND`, path variables and feature flags.
- Sanitize inherited environment variables: prevent an external `OLLAMA_BASE_URL`, `OLLAMA_MODELS`, `TESSERACT_CMD`, `PYTHONPATH`, model/cache settings or arbitrary release flag from overriding the chosen package. Preserve only required safe OS environment.
- Keep `STRICT_SOURCE_GROUNDING=true` and all policy/limits in place. No fallback to unrestricted medical generation.
- In the ready screen, display actual effective config and available components, *not* aspirational feature labels.
- Test a release with a deliberately hostile `.env`/environment value to prove the bundled profile wins or the app rejects the mismatch.

### 5.2 Full private/authorized example (only when all rights are cleared)

```dotenv
ANSWER_MODE=ollama
TEXT_MODEL=qwen3-vl:2b-instruct
VISION_MODEL=qwen3-vl:2b-instruct
STRICT_SOURCE_GROUNDING=true
ENABLE_GENERAL_CHAT=true
RETRIEVAL_BACKEND=hybrid
ENABLE_TEACHING=true
TEACHING_BACKEND=hybrid
ENABLE_SECONDARY_REFERENCES=true
ENABLE_HANDWRITING_OCR=false
ENABLE_XRAY=false
```

The final path settings `CORPUS_PATH`, `SOURCE_REGISTER`, `CHROMA_PATH`, `EMBEDDING_PATH`, `REFERENCE_COLLECTION`, `TEACHING_RELEASE_PATH`, `TEACHING_INDEX_PATH`, `TEACHING_EXPLANATIONS_PATH`, `TEACHING_EXPLANATIONS_SHA256`, `SECONDARY_REFERENCE_PATH`, `SECONDARY_MANIFEST_SHA256`, and X-ray manifests **must** be filled with verified paths/values from the source repository. Do not invent these hashes. `ENABLE_XRAY=true` is allowed only after verified weights, registered permitted original images and the safety/rights gate.

**Note:** Use a dedicated package-owned Ollama loopback port such as `127.0.0.1:11435` instead of assuming the common `11434` belongs to this app; set both `OLLAMA_HOST` and `OLLAMA_BASE_URL` consistently. This is a proposed isolation improvement requiring an integration test. The 8000/8501 frontend/bridge addresses may remain fixed initially because the existing web bridge has a fixed upstream.

---

## 6. Launcher lifecycle: precise responsibilities

Add `packaging/launcher.py` (or a suitable compiled host launcher). Implement the lifecycle as a state machine:

```text
NOT_STARTED
   |
   v
VERIFY_PACKAGE  --bad or missing file--> ERROR / REPAIR
   |
   v
CHECK_OS_ARCH_AND_RESOURCES --> ERROR with truthful requirement
   |
   v
CHECK_PRIVATE_LOOPBACK_PORTS --> ERROR (never kill unrelated process)
   |
   v
START_OLLAMA (project executable, project model store, cloud disabled)
   |
   v
VERIFY_OLLAMA_READY + EXACT MODEL DIGEST --> ERROR / REPAIR
   |
   v
START_FASTAPI_API (single frozen worker)
   |
   v
WAIT /health/live THEN /health/ready + manifest/profile checks
   |
   v
START_FRONTEND_BRIDGE
   |
   v
VERIFY_UI_AND_BRIDGE --> OPEN http://127.0.0.1:8501/
   |
   v
READY / MONITOR OWNED PROCESS CHILDREN
   |
   v
EXIT: GRACEFULLY STOP OWNED SERVICES; FLUSH LOGS; LEAVE UNRELATED SERVERS ALONE
```

Implementation requirements:

1. Derive the install root using the directory of `sys.executable` in the frozen launcher; do not use `__file__` to guess the external asset root. In the backend/resource modules, make `asset_root` explicit and handle PyInstaller `_internal/` separately.
2. Use absolute paths for every executable and static/index/model file. Test install paths with spaces, apostrophes and Unicode characters.
3. Launch child processes with `subprocess.Popen([...], cwd=..., env=..., creationflags=...)`; store PIDs and process handles, and terminate **only children started by this launcher**. For robust Windows cleanup, a Job Object or equivalent owned-process-tree management is preferable.
4. Do not trust `HTTP 200` from `/` as AI readiness. Follow API `/health/live` and `/health/ready`, model existence, digest and source/index checks. UI can become visible before backend initialization finishes.
5. Keep loading states responsive. Heavy model warm-up must not freeze the visible UI. Do not promise instant first inference; measured load times must come from tests.
6. Bind all services to `127.0.0.1`, not `0.0.0.0`. Preserve fixed bridge allowlist, `X-Aster-Client`, Origin, CSP, upload/body limits, and session tokens.
7. Leave all clinical-policy/identity gates active, including urgent language, no personal medicine selection, exact medicine formulation matching and prescription revision checks.
8. On model failure, show `Model unavailable` with repair instructions; do not silently use system Ollama (different model/revision), cloud APIs, or arbitrary remote servers.
9. Logs under `%LOCALAPPDATA%\Aster\logs\`, with rotation and no question/prescription contents. Provide `Export diagnostics` that excludes secret tokens, uploads and private source snapshots.
10. No admin privileges, system-wide service, startup-at-login persistence, firewall opening or unsolicited telemetry.

**Suggested final executables:** `Aster.exe`, `bin/aster-api.exe`, `bin/aster-web.exe`, `runtime/ollama/ollama.exe`.

---

## 7. Release edition details and the medical feature contract

### 7.1 Core Standard edition (public)

Always available **when their underlying redistributable assets are actually packaged**:

- Medical educational source retrieval (scope constrained by included library), with retained citations and explicit insufficient-evidence statuses.
- Structured `qwen3-vl:2b-instruct` general chat only for the existing recognized nonmedical intents; source-bound medical generation + extractive fallback.
- **Simple explanation** and **Deeper explanation** only where checked layouts/notes exist; do not generate unsourced new medical paraphrases to fill coverage gaps.
- Image routing via Qwen vision; printed prescription OCR if Tesseract is packaged; mandatory user field confirmation and revision invalidation.
- Session controls, source panel/drawer, JSON exports and the existing consistent dark ambient responsive UI.

Do **not** promise the user's complete current medicine/teaching collections when you have excluded any source on legal grounds. Display an edition-level `About → Included data versions` screen with actual counts and coverage.

### 7.2 Optional/authorized add-on packs

- **Teaching pack:** exact teaching release, compatible index, explanations/holds and explanation layouts. Enable `ENABLE_TEACHING=true` only after exact manifest validation.
- **Secondary medicine pack:** exact permitted 6,670 notes/3,408 product links. Keep unverified-data captions and prohibit its use for dosing, contraindications, warnings or interactions.
- **X-ray research pack:** only permitted adult frontal AP/PA registered images, exact original bytes/hashes, TorchXRayVision weights, CPU dependencies and model card. Preserve research-score semantics: no diagnostic confidence, no `normal X-ray` assurance. Do not treat any arbitrary upload as eligible for specialist scores.
- **Experimental handwriting:** retain **off by default**. The README records 10/37 exact medicine-word crops and 27 incorrect unflagged readings; explicit user confirmation remains compulsory even if turned on in an authorized research profile.

**Optional pack install rule:** A prepacked, preverified optional pack is an automated install/update operation (not an LLM question-time download). The user must see what data/functions it adds, disk usage, licensing and experimental status.

---

## 8. Distribution on GitHub: make the UX truly one-click

As checked on **10 October 2026**, GitHub's official Release documentation allows **up to 1,000 release assets**, with **each file under 2 GiB**; there is no total release-size cap. Source-code archives are **not** the finished application. See https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases .

The prior README estimates Ollama runtime ~1.5 GB plus Qwen weights ~1.9 GB *before* app data and dependencies. Compression and actual build sizes must be measured; do not promise one under-2-GiB monolithic release file.

### Preferred: one small GitHub setup program + immutable asset parts

- Publish `AsterSetup-1.0.0-Windows-x64.exe` (bootstrapper), a release metadata manifest and several **sub-2-GiB** assets (target ~1.5–1.8 GiB or smaller to leave margin).
- Setup offers a simple install directory, disk-space validation, accurate component/download sizes and progress/error states.
- Fetch **exact pinned release assets**, verify manifest trust + SHA-256 per downloaded file, and support interrupted-download resume or clean retry.
- Extract to a temporary directory, verify all resulting hashes, then atomically install/swap versioned asset sets. Never leave a half-installed app claiming `Ready`.
- Offer `Launch Aster` as final action. The first startup must not call `ollama pull`, `pip`, a Hugging Face registry or dataset acquisition tools.
- If download fails/offline, show `Setup incomplete: network required to acquire the prepackaged application`—not `model installation required`.

### Alternate: fully offline portable package

Host a complete archive where large individual files are supported, link that archive from the GitHub release, and include a checksum/signature and version manifest. If **GitHub-only** is mandatory, publish segmented parts with an officially provided assembler/extractor; it requires retrieving multiple parts, so it is less convenient than the bootstrapper.

**Security for auto-downloaded assets:** use HTTPS and an authenticated release manifest or signed assets; checksum validation alone does not authenticate a manifest obtained from the same compromised location. Pin permitted download domains; prohibit arbitrary URLs and path traversal while extracting; never execute unsigned arbitrary scripts from assets.

---

## 9. Files and source changes to implement

```text
AI doctor/
├── packaging/
│   ├── launcher.py                 # Aster controller and readiness state machine
│   ├── api_entry.py                # uvicorn.run(backend.app.main:app)
│   ├── web_entry.py                # uvicorn.run(frontend.webserver:app)
│   ├── aster-launcher.spec         # PyInstaller spec(s)
│   ├── aster-api.spec
│   ├── aster-web.spec
│   ├── build-windows.ps1           # clean build with selected pinned lock/profile
│   ├── stage-assets.py             # permission-filtered model/data staging
│   ├── generate-manifest.py        # immutable hashes/digests
│   ├── verify-package.py           # offline integrity + compatible release checks
│   ├── asset-rights.csv            # reviewed redistribution inventory
│   ├── release-profile.json        # flags and absolute-on-startup path mapping
│   ├── create-release-assets.py    # split/archive safely below GitHub limits
│   └── installer/                  # bootstrapper/installer sources
├── tests/
│   ├── test_frozen_config.py
│   ├── test_release_manifest.py
│   ├── test_launcher_lifecycle.py
│   ├── test_release_asset_compatibility.py
│   └── test_clean_machine_smoke.py
├── .github/workflows/
│   ├── windows-ci.yml
│   └── release-windows.yml
├── LICENSE                         # only after rights/owner decision
├── THIRD_PARTY_NOTICES.md
├── SECURITY.md
├── CHANGELOG.md
└── README.md                      # updated one-click download instructions
```

Expected existing-file changes (confirm in actual source):

- `backend/app/config.py`: explicit immutable release root/config, effective config status, validated paths; no current-working-directory assumptions.
- `backend/app/main.py`: graceful termination, startup readiness and complete asset-validation reporting, one-worker behavior.
- `backend/app/adapters/*`: absolute packaged Ollama/Tesseract/MiniLM/XRV paths and no implicit network acquisition.
- `frontend/webserver.py`: keep bridge upstream and Origin/host restrictions consistent with frozen service binding; no new public CORS.
- `frontend/web/app.js`: user-facing startup/loading/repair statuses, exact included-feature display, missing-model explanation; keep existing UI and source panel.
- `scripts/verify_assets.py`: add `--release-manifest`/`--offline` modes that verify package bytes and matching asset/index/model versions.
- `start.ps1`, `setup.ps1`, `setup-chat.ps1`: **keep as developer setup tools**, not end-user requirements. Clearly distinguish source/dev versus Releases download in the README.

Avoid modifying retrieval/clinical inference logic solely to make packaging easier. Maintain the behavior guaranteed by existing tests.

---

## 10. Exact build and publishing workflow

### Phase A — Baseline capture

1. Tag and back up the known-good 10 October development revision.
2. Capture effective environment/profile, model digest and full file inventory (including private files that **must not** ship).
3. Run and record the current tests, live checks and asset verification as baseline.
4. Measure **actual** compressed/uncompressed asset sizes, disk usage, first run and CPU/GPU resource behavior.
5. Decide public vs rights-cleared private edition and verify every redistributable asset.

**Exit gate:** a written source/profile/permission manifest accounts for every feature and file.

### Phase B — Relocatability and asset consistency

6. Introduce `ASTER_INSTALL_ROOT` / explicit asset-root resolver for frozen executables.
7. Change hardcoded `C:\Users\...` Tesseract/source/cache paths to safe manifest-derived paths.
8. Introduce a trusted release profile and override `.env` precedence deterministically.
9. Validate primary, teaching, MiniLM, explanation layout and optional secondary/X-ray compatibility at startup.
10. Add `offline mode` and make missing/corrupt assets explicit—not a request-triggered download.

**Exit gate:** the full developer app works from multiple folders, offline, using the captured profile.

### Phase C — Freeze components

11. Create separate launcher/API/web entrypoints and pinned PyInstaller specs.
12. Freeze Python into tested Windows onedir packages; collect static web assets and optional native libraries.
13. Bundle standalone Ollama, English Tesseract and permission-cleared checkpoints/libraries.
14. Assemble data assets, release profile, legal notices and integrity manifest.
15. Run the frozen components manually, then via the launcher.

**Exit gate:** no global Python, Ollama, Tesseract or Node install is required to run the package.

### Phase D — Install/launch UX

16. Build launcher state machine, progress UI, diagnostics and safe teardown.
17. Add occupied-port checks and dedicated instance ownership; never kill unrelated processes.
18. Add startup source/data checks and clear feature-readiness status.
19. Build installer bootstrapper with pinned parts, authenticated manifest, resume/retry and atomic staging.
20. Build offline full archive; provide checksum/signature and exact version labels.

**Exit gate:** clean installation and ready-state verification are repeatable.

### Phase E — Verification and medical-policy regression

21. Run `pytest -q`, `pip check`, `scripts/verify_assets.py`, selected `ruff`/audit checks and `node --check frontend/web/app.js` in build source environment.
22. Run source-policy, teaching, medicine identity, scope, extraction, revision/confirmation, response-format, emergency-language and unsupported-input regressions against the **frozen app**.
23. Run live model tests on included Qwen tag/digest, including a nonmedical query, general tissue concept and specific *sulcular epithelium* question, with source panel and Simple/Deeper/hold behavior.
24. Test synthetic printed prescription real OCR; preserve the incomplete handwriting warnings and mandatory confirmation.
25. If imaging is included, test exact-byte registered permitted demos, changed-hash rejection, unsupported/unregistered images, CPU preprocessing, and nondiagnostic score labels.
26. Run air-gapped tests with no model registry access; assert **zero unsolicited network calls** during question, upload, lookup and startup after completed install.
27. Run clean Windows VM matrix, including no GPU, missing VC runtime, non-admin accounts, Unicode/space paths, insufficient RAM/disk, port conflicts, partial/corrupt assets and antivirus/SmartScreen behavior.
28. Measure time-to-first-ready and answer latency; document observed figures rather than invented minimum requirements.

**Exit gate:** all advertised features pass the frozen-install tests, with no private or network dependency, and documented medical boundaries.

### Phase F — GitHub release

29. Publish a reviewed `LICENSE`, `THIRD_PARTY_NOTICES.md`, `SECURITY.md`, changelog, model cards and public intended-use/limitations.
30. Set up a tagged reproducible release workflow. Only trusted tags from protected main branch can publish; pin CI action dependencies and release permissions.
31. Build immutable release parts (`<2 GiB` each), checksums, installer and complete offline archive/segments.
32. Create GitHub Release notes showing model digest, included data releases/counts, known limitations, CPU/OS compatibility, total size, install/repair instructions and lack of clinical validation.
33. Install from **publicly downloaded assets**, not local staging output; recheck hashes, version and fully offline operation.
34. Mark release final only after smoke test and rights gate.

**Exit gate:** a user can follow `Releases → Download installer → Run → Launch` and use the exact included model without manual setup.

### Phase G — Updates, rollback and support

35. Treat code/model/data as **versioned independent artifacts** with a signed compatibility manifest; never auto-update model tags blindly.
36. Install updates into a new staging directory, verify before switching and retain previous known-good version for rollback.
37. Respect immutable index/record/teaching-note source hashes on update; when notes change, rebuild `configs/explanation_layouts.json` and rerun `tests/test_explanation_layers.py`.
38. Update private medical datasets only after rights, source quality and independent review; do not claim new clinical accuracy from software tests.
39. Publish downloadable offline diagnostic bundle with logs, versions/hashes and test results, scrubbed of chat, tokens and uploaded images.
40. Add a clear migration/uninstall path for `%LOCALAPPDATA%\Aster\`; explain what persists (assets) and what does not (in-memory chats/uploads).

---

## 11. Acceptance matrix (must all pass)

| Test | Expected result |
|---|---|
| New Windows machine has no Python/Ollama/Tesseract/Node | Installer/full archive launches and model loads |
| Disable network after install | Source-backed answer + vision routing + permitted OCR continue working |
| Move portable folder to path with spaces/Unicode | Application and every index/model/static asset still resolves |
| No existing `.env`; `.env.example` defaults originally disabled teaching | Release teaching flag equals verified edition profile, not accidental default |
| Contradictory user `.env` or process variables | Launcher overrides safely or fails with explicit mismatch; no silent feature drift |
| Qwen digest differs from packaged manifest | Refuse incompatible model/repair; never pull a new model automatically |
| Teaching release and index mismatch | Hard fail feature validation, no fabricated fallback |
| Teaching note hash/layout mismatch | Hide stale layers, show source-safe fallback, flag repair |
| Model loading slow | Frontend status says loading, not falsely ready |
| Occupied port used by another application | No unrelated process killed or hijacked |
| Print-style synthetic prescription | Actual OCR + editable fields + mandatory revision confirmation |
| Handwriting difficult/uncertain | Experimental limitation and unresolved fields retained; never guess dose/name |
| Unregistered X-ray | No specialist inference scores |
| Altered registered X-ray bytes | Hash mismatch blocks specialist scoring |
| Unsupported medical or dosing request | Policy/insufficient-evidence behavior preserved |
| API crash / model process crash | User sees actionable failed state; owned subprocesses shut down or restart safely |
| Pause/interrupt installer download | Resume or clean retry; never run partial data set |
| `netstat`/packet capture on offline runtime | Services bound only to loopback; no unsolicited outbound inference |
| Exit `Aster.exe` | Child processes created by that launcher terminate; unrelated local services unaffected |
| Public artifact rights scan | No patient data, unlicensed snapshots, keys, or private backups in archive |

**Hardware:** define support by actual clean-machine measurements, including CPU-only usability and tested integrated/NVIDIA GPU configurations. README hardware is **not** evidence for a minimum RAM or VRAM guarantee.

---

## 12. Recommended milestones (implement in this order)

**M1 — Legal/data and manifest gate:** inventory all assets, establish permissions, capture exact releases/digests and actual sizes. Stop publication if ownership/permission is unresolved.

**M2 — Verified portable development build:** run the full Aster stack from a different folder with no global model path and no internet. Resolve config precedence and hash compatibility.

**M3 — Frozen onedir application:** produce `Aster.exe` + frozen API/web + bundled Ollama/Tesseract and selected redistributable assets. Make one-click launch and shutdown reliable.

**M4 — User-facing installer:** split distribution assets to GitHub limits, implement trusted download manifest, installation, resume/repair and offline-first behavior.

**M5 — QA, security, release:** run clean VM/CPU tests, source and medical-policy regressions, and rights scan; publish a clearly labeled beta first, then stable only after actual install testing.

Prioritize an accurate **core offline edition** over promising the entire research development folder before redistributability and hardware validation are complete.

---

## 13. README changes for end users

Change the top of README to present **two distinct paths**:

> **Want to use Aster?** Go to **GitHub Releases**, download **AsterSetup-Windows-x64.exe**, install and launch. No Python/Ollama/model setup commands are needed. First-time installation downloads the included model once; the installed app runs locally/offline. For no first-run network, use the complete **Offline Portable** package. This is medical education software, not a clinical tool.
>
> **Want to develop Aster?** Clone source, run the existing `setup.ps1`, acquire pinned models where permitted and configure `.env` using the developer instructions.

Add sections for: supported Windows versions and measured RAM/disk, offline behavior, data/model size, installer vs portable, release verification (SHA/signature), first-launch loading, bundled data coverage, disabled/experimental features, licence acknowledgements, privacy, local-service ports, repair, uninstall, rollback and a clear technical diagnostics path.

Do not retain machine-specific `<repo>/` commands as the main installation pathway for users.

---

## 14. Technical references checked for this plan

- GitHub Release asset limits: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- Ollama Windows standalone CLI embedding/installation: https://github.com/ollama/ollama/blob/main/docs/windows.mdx
- PyInstaller frozen runtime path behavior: https://pyinstaller.org/en/stable/runtime-information.html

These explain distribution and packaging behaviors; they do **not** certify the full Aster codebase or confer permission to redistribute third-party medical/reference materials.

---

## 15. Final implementation recommendation

**Best practical result:** GitHub `AsterSetup.exe` automatically installs an immutable, offline-capable Aster application with bundled Qwen3-VL 2B, Ollama, MiniLM, Tesseract and only cleared references. Provide a larger complete offline archive for users who cannot use an installer or have no installation-time network. Keep optional X-ray, experimental handwriting and legally restricted medicine/teaching packs out of default public builds unless explicitly cleared and fully tested. Reuse Aster's existing FastAPI + web frontend, strict source validation, in-memory session design and single-worker architecture; do **not** rewrite clinical logic to simplify distribution.

**Success criterion:** *No user runs `pip install`, `ollama pull`, `setup-chat.ps1`, or a model installer. The released binary selects and verifies the exact included model and source-backed knowledge profile, and all advertised features work offline after install.*
