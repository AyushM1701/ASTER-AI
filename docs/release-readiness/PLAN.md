# Aster release-readiness plan — 14 October 2026

Input: `docs/implementation/inputs/ASTER_One_Click_Readiness_Implementation_Prompt_2026-10-14.md`.
Acceptance tracking: [ACCEPTANCE_LEDGER.md](ACCEPTANCE_LEDGER.md). Final evidence: [ACCEPTANCE_REPORT.md](ACCEPTANCE_REPORT.md).

## Starting point (verified against code and assets, 14 Oct 2026)

- Chat is a layered extractive pipeline (`answers.py`, `question_plan.py`, `retrieval.py`). Nonmedical chat is a regex whitelist (`explicit_nonmedical`). The frozen candidate-v5 pilot gives 20 substantive and 5 complete answers in 111 turns.
- `packaging/release-profile.json` is `ValidationOnly`; handwriting and X-ray scoring are off. Every rights row in `packaging/asset-rights.csv` except Aster's own code is `pending`.
- X-ray analysis accepts only two hash-registered NIH demo images. There is no upload pathway.
- Ollama calls use `keep_alive: 0`, so each request reloads the model.
- No GitHub release exists, no source-ZIP launcher exists, and setup has no shortcuts, uninstall entry, or hardware profile selection.
- Machine: i5-13450HX, 24 GB RAM, RTX 4050 Laptop; Windows 11 Home. Windows Home has no Hyper-V or Windows Sandbox, so a clean VM cannot run here. That is an external gate.

## Approach

Reuse the FastAPI backend, web frontend, Ollama/Tesseract adapters, `aster_release` installer/launcher and PyInstaller specs. Do not rewrite unrelated workflows. The new answer path sits alongside the existing MDS/viva/document/paper routes and becomes the default chat route.

1. **Library pipeline (`aster_library/`).** Use source-specific providers: MedlinePlus health-topic XML; MedlinePlus lab-test pages; DailyMed SPL (US labels, explicit jurisdiction); Europe PMC/PMC open-access full text filtered to CC0/CC BY/CC BY-SA, with CC BY-NC* isolated in a non-default pack; OpenStax CNXML (CC BY 4.0) from the official GitHub repositories; plus the rights-reviewed subset of the existing candidate-v5 pack. Specialty query plans cover all nine MDS specialties and shared sciences. The pipeline uses checkpoints, rate limits, retries, deduplication across DOI/PMID/PMCID, retraction and correction checks, parsed evidence units, a coverage report, and a signed versioned pack with freshness rules.
2. **Index.** SQLite FTS5 (BM25) plus a MiniLM float16 dense matrix, rank-fused. Built at release time, shipped with the pack, and checked for compatibility by pack hash.
3. **Grounded answer engine (`answer_engine.py`).** Steps: (a) a general router (LLM classification with heuristic fallback) replaces the whitelist; (b) query expansion and contextual follow-up rewriting; (c) hybrid retrieval with audience-appropriate source classes; (d) local-LLM synthesis with numbered citations; (e) per-sentence support verification (lexical content-term coverage plus dense similarity against the cited passage, which tolerates paraphrase); (f) unsupported sentences are dropped and reported as gaps; (g) policy and safety guards are kept. General conversation is labelled as model knowledge.
4. **Evaluation.** Freeze a several-hundred-item set (patient, student, MDS × 9, general, safety, ambiguous, follow-up) **before tuning**, with a separate holdout. Report completion, citation support, unsupported-claim rate and latency per specialty.
5. **X-ray upload pathway.** Run user uploads through gates: decoding/quality; the TorchXRayVision autoencoder OOD check; a frontal/lateral view model; an age-estimate pediatric screen. Only then score with DenseNet. Keep curated registration for evaluation. Evaluate on legitimate public deidentified data with contamination disclosed.
6. **Prescriptions.** Use the same attachment workflow for images and PDFs. Show editable fields beside source crops, with explicit ambiguity and confirmation invalidated on edit. Handwriting is enabled through the vision model, labelled as a limitation, and evaluated on synthetic handwriting only, labelled as such.
7. **Distribution.** A pinned release lock (`release/release-lock.json`) committed in source is the trust root. `Start Aster.cmd` (source ZIP) downloads and verifies the pinned `AsterSetup-Windows-x64.exe` (or runs an installed copy offline). Setup is per-user and handles: hardware-profile selection, free-space checks, resumable verified downloads from GitHub release assets and pinned upstream origins, safe extraction, atomic install, Start Menu and desktop shortcuts, an HKCU uninstall entry, repair, rollback, an offline-folder install, and a portable bundle. The controller reports Ready only after real text inference, retrieval, OCR and the X-ray gate check.
8. **CI.** A release workflow builds the library, indexes, frozen app, setup and portable bundle; it verifies them and creates a **draft** release. Publication stays a separate authorized action.

## External gates (cannot be completed by engineering here)

These gates are: clean Windows VM/second machine; Authenticode signing certificate; publishing the GitHub release; independent MDS faculty and clinician review; radiologist-labelled held-out imaging data; and independent handwriting evaluation with real prescriptions.
