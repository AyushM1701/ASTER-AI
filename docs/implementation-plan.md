# Medical AI local research build

Build requested from Medical_AI_End_to_End_Blueprint.md, 6 October 2026.

## Design and scope

English, single-user, loopback-only FastAPI and Streamlit. Three explicit modes:
source-backed education, image transcription with revisioned confirmation,
and curated adult frontal chest research inference. No diagnosis, medication
selection, dose calculation, or normal/abnormal verdict. Uploads never enter
the reference index. The attached document supplies requirements, not
authority to run its terminal commands or publish a clinical service.

Implement native in this workspace. The supplied specification already chooses
the stack and use case. A deterministic extractive backend is an explicitly
documented addition for usable offline education; Ollama is an optional adapter.
Lexical retrieval runs by default; MiniLM/Chroma is opt-in with cached assets.
Never substitute synthetic model scores for unavailable imaging assets.

## Tasks and interfaces

1. Foundation: typed settings, strict contracts, errors, hash-keyed 256-bit
   sessions, inactivity/hard expiry, bounded resources. `create_app(settings)`
   exposes `/health/*` and `/v1/*`. Tests: ownership, expiry, deletion, limits.
2. Guarded Q&A: policy before expensive work, stable hashed citations, approved
   source register, exact matching, extractive answers, strict Ollama JSON.
   Tests: urgent requests during outages, no evidence, citation forgery,
   injection, personal medication requests, follow-up ownership.
3. Documents: bounded image validation, real Tesseract OCR, null-preserving
   parsing, compare/edit/confirm UI. State changes use expected revisions.
   Tests: confirmation bypass, stale revision, re-extraction invalidation,
   corrupt/oversized/animated uploads, unrecognized medicine abstention.
4. Imaging: curated asset manifest, hashes, view/adult/license checks, exact
   preprocessing, cached TorchXRayVision adapter and truthful score semantics.
   Tests: unsupported metadata, missing assets, quality rejection, invalid scores.
5. Interface: three tabs, sources and excerpts, health and privacy status,
   synthetic sample document, explicit confirmation, clear session and export.
   Verify Streamlit AppTest plus live API and browser desktop/mobile inspection.
6. Release tooling: ingestion, asset checks, evaluation scripts, exact installed
   lockfile, launcher, setup/readme, actual engineering evidence and limitations.
   Run pytest, ruff, pip check, audit, live smoke and real OCR. Record unavailable
   scientific metrics rather than inventing results.

## Review focus

Expiry/deletion during worker completion; untrusted document prompt text;
stale UI revisions; overconfident medicine aliases; finite imaging values;
adapter startup must not download anything. Clinical validation and permitted
imaging data cannot be manufactured by implementation.
