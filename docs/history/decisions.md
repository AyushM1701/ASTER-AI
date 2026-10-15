# Decisions — 6 October 2026

- Follow Python/FastAPI/Streamlit baseline. User requested Impeccable dark ambient UI.
- The later approved Figma redesign replaces the default Streamlit presentation
  with a dedicated web UI and bounded FastAPI bridge. This gives direct control
  over the three-column layout and responsive composer while retaining the local
  Python services and requiring no frontend package/runtime installation.
- Use the installed Python 3.13.3 rather than install a second interpreter. Freeze
  measured application dependencies and verify imports/tests on this machine.
- Add explicit lexical/extractive mode to provide usable local reference education
  without a large LLM download. Optional Ollama/MiniLM/Chroma adapters remain separate.
  This mode does not claim model-generated reasoning or dense retrieval quality.
- Start with nine checked, short original source notes rather than scrape 20–40
  pages automatically. Corpus coverage is deliberately narrow and visible.
- Use existing Tesseract 5.5.3 with English/PSM6. Do not enable experimental vision OCR.
- Keep imaging disabled until reliable permitted assets and cached weights exist.
  No synthetic X-ray scores or disguised placeholder findings.
- Keep session state process-local with ownership/revision checks; no database,
  accounts, patient persistence or shared clinical deployment.
- Upgrade the venv's pip after dependency audit identified advisories in the
  bundled old installer. No global environment changes.

Future corpus/model/policy/preprocessing changes require a new manifest and
rerunning applicable evaluation and workflow tests.
