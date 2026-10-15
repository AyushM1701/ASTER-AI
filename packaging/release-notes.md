# Aster 0.2.0-rc.2 (release candidate)

**Release candidate for testing.** This is not a clinically validated product. Aster is for education and information;
it does not diagnose, prescribe or calculate personal doses. X-ray outputs are research scores for professional review.

## Install

- Easiest: download the repository's **source ZIP**, extract it, and double-click **`Start Aster.cmd`**.
- Or download **`AsterSetup-Windows-x64.exe`** below and run it. No administrator rights are needed.
- Offline install: download every file of this release into one folder and run
  `AsterSetup-Windows-x64.exe --offline-dir <folder>`.

Setup downloads about 2.9 GB for the standard profile. Aster runs on the CPU, and no graphics card is needed. It checks
every file against the SHA-256 values in the signed `release-lock.json` that is compiled into setup. Afterwards
Aster works offline.

## What's new since 0.2.0-rc.1

- **My Library.** Add your own notes, articles or whole textbooks (PDF, including scanned pages read with OCR, Word,
  text or Markdown; up to 100 MB / 2,000 pages). Aster indexes them on your PC and cites them by page in later answers;
  ask "according to my notes…" to answer from your documents only. Aster does not review what you add and says so on
  every answer that uses it. Your library is kept with your saved work, so updates and repairs keep it.
- **Security.** The local service refuses requests addressed to any host other than this computer (DNS-rebinding
  protection).
- **Reliability and interface.** One document indexed at a time; library updates no longer interrupt answers in
  progress; My Library and Study topics in the main navigation; drag-and-drop file zones.

The reference library (2026.10.15), models and measurements below are unchanged from rc.1.

## What's new since 0.1.0-beta

- **Grounded answers.** Answers are drawn from a newly built, licence-checked medical library of
  4,527 core documents and 2,206 optional noncommercial documents. Every statement is checked against its cited passage, and
  unsupported statements are removed and reported as gaps. Everyday questions are handled conversationally,
  with no fixed list of allowed questions.
- Covers MBBS and all nine MDS specialties at postgraduate depth, including exam formats, MCQs and viva practice.
  Statistics are calculated with checked formulas.
- **Prescriptions.** Photos and scanned PDFs; automatic rotation; photo-quality warnings; editable fields beside source crops;
  written dose and a verified-ingredient field; cited explanations. Handwriting reading is experimental.
- **X-ray uploads.** Adult frontal chest X-rays only, behind evaluated input checks. Research scores via ONNX, with no torch.
- **Installer and launcher.**
  - Per-user installer with hardware-profile selection, resumable verified downloads, Start menu and desktop shortcuts,
    an uninstall entry, repair, rollback and a portable mode.
  - Opt-in signed library updates.
  - Free-port selection and duplicate-launch handling.
  - "Ready" is shown only after real retrieval, claim-checking, OCR, X-ray and model checks pass.

## Known limitations

- No independent clinical or faculty review. Evaluation questions and key points were written by AI, not by faculty.
- **Held-out evaluation (151 questions).** Labels are AI-written, not clinician-reviewed.
  - Standard profile (2B model, CPU): 93% behaved as intended (median 32 s, 90% within 57 s).
  - The larger 4B model, which the manual Quality CPU profile uses, reached 98%. It was measured on a GPU for evaluation
    only, and Aster ships no GPU support.
  - Many answers are partial: Aster names the part its library does not cover instead of guessing.
  - One wrong sentence (an aspirin warning attributed to ibuprofen) passed the automatic checker in the 4B run. The
    checker now requires the named drug to be in the supporting sentence.
- **Handwriting** was measured only on 72 synthetic handwriting-font images: no wrong strength, frequency or duration was
  read, but 2 medicine names were misspelled. Real handwriting is untested.
- X-ray input checks were evaluated on small public test sets.
- Measured on one laptop only (i5-13450HX, 24 GB RAM, RTX 4050).
- Not code-signed, so Windows SmartScreen may warn on first run.
- Portable mode and returning to a previous version (`--rollback`) have not been tested yet.

See `docs/release-readiness/ACCEPTANCE_REPORT.md` in the source for the measurements behind these notes.
