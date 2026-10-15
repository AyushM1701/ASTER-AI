# Changelog

## 0.2.0-rc.2 — release candidate (draft)

Builds on 0.2.0-rc.1 with the same reference library (2026.10.15) and models.

- **My Library.** Add your own articles, notes, study material and whole textbooks (PDF, including scanned pages read
  with OCR, .docx, .txt, .md; up to 100 MB / 2,000 pages). They are indexed on this computer and searched with the
  reference library, so later answers can draw on them and cite them by page. Ask “according to my notes…” to answer
  from your documents only. The original files are not kept, and Aster does not review their content.
- **Security.** The local API now refuses requests addressed to any host other than this computer, closing a
  DNS-rebinding route by which a web page could have read or removed My Library documents.
- **Reliability.** My Library indexes one document at a time; uploads no longer block other requests; a damaged
  scanned page no longer stops OCR of its neighbours; library updates no longer interrupt answers in progress;
  everyday phrases such as “I added salt…” no longer restrict answers to My Library.
- **Installer.** My Library is stored with your other saved work, outside the versioned app folder, so updates and
  repairs keep it.
- **Interface.** My Library and Study topics are primary navigation items; a “Study from your own notes” starter;
  distinct starter icons; drag-and-drop file zones; inline confirmation when removing a document; size check before
  upload; corrected counts and source dates.

## 0.2.0-rc.1 — release candidate (draft)

- **One-click start.** `Start Aster.cmd` in the source ZIP downloads a pinned, hash-verified setup that installs the
  model runtime, models, OCR, the X-ray checker and the signed library. CPU only: no graphics card is needed or used, and no NVIDIA libraries are distributed.
- **Grounded answers.**
  - Hybrid retrieval and MedCPT reranking.
  - NLI claim verification with number, code, negation and drug-name checks.
  - Routing without a fixed question list.
  - Follow-up rewriting.
  - Deterministic statistics.
- **New reference library (2026.10.15).**
  - Licence-checked open sources, Ed25519-signed packs, freshness rules and opt-in signed updates.
  - 4,527 core and 2,206 optional noncommercial documents.
- **Prescriptions.** PDF scans, automatic rotation, photo-quality feedback, fields beside source crops, written dose and
  verified-ingredient fields.
- **X-ray.** Torch-free ONNX models behind evaluated input checks, with adult attestation.
- **Installer.**
  - Per-user setup with hardware profiles and resumable downloads.
  - Repair, rollback, uninstall, portable and offline modes.
  - Ready shown only after real startup self-tests.
- **Repository clean-up.**
  - Historical reports moved to `docs/reports/`, and earlier notes and plans to `docs/history/`.
  - Source-checkout helpers moved to `tools/dev/`, and unused v1 build scripts removed.
- Measurements and remaining gates: `docs/release-readiness/ACCEPTANCE_REPORT.md`.

## 0.1.0-beta.1 — unreleased

- Added Windows release infrastructure: immutable asset manifests, relocatable runtime configuration, native launcher, owned Windows Job Object services, frozen API/web entrypoints, authenticated segmented-archive bootstrapper and atomic versioned installation/rollback.
- Added public/private redistribution gates and a non-distributable local validation edition.
- Preserved source grounding, simple/deeper explanation boundaries, single-worker sessions and the existing same-origin web workspace.
- Packaged profile disables X-ray scores and experimental handwriting by default.
- Added MIT license for Aster's own code with owner authorization. Third-party rights and clean-machine acceptance remain separate release gates.
