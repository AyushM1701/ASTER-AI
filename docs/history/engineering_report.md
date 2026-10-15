# Engineering evidence — 6 October 2026

The supplied blueprint is an implementation and release guide, not a completed
clinical system. This build delivers the local code, dark ambient interface,
adapters, scripts and engineering workflows. It does not claim all 180 release
steps or scientific gates are complete.

## Observed results

- Final pytest run: 49 passed. Coverage includes ownership, revision conflicts,
  confirmation bypass, expiry/deletion during OCR, invalid uploads, policy routes,
  model timeout/malformed JSON, forged citations and changed corpus content.
- Development routing suite: 40/40 expected statuses, 40/40 citation-ID-valid cases,
  source recall@3 = 1.0 across annotated supported cases. This is a small developer
  development set, not a held-out clinical benchmark. Claim entailment and
  population accuracy were not estimated.
- Real Tesseract printed synthetic fixture: observed character/word error rate
  0; expected medicine name, strength, formulation, route, frequency, instructions
  and absent duration matched. One clear sample does not establish OCR reliability.
- Retrieval-only benchmark: measured timings and process RSS are in the actual
  artifact; it is not a generation/imaging or peak-memory benchmark.
- Browser round-trip: source-backed education; real sample OCR; explicit
  revision-2 confirmation; source-linked document explanation; missing duration
  remained unresolved. Dark ambient UI inspected at desktop and mobile widths.

Reports and reproducibility manifests are under `artifacts/evaluation/`.
The final test count and checks are recorded in `release_checks.txt` after final
verification. An upstream TestClient deprecation warning does not change test
assertions; migration to the new transport remains dependency maintenance.

A separate code review identified unrelated-negation urgency suppression,
pre-allocation upload bounds, applicability-metadata integrity, a long-document
confirmation mismatch, and stale imaging selection results. Each was reproduced
before correction and received a regression test. Negation now scopes to a
symptom clause; uploads reserve capacity and share bounded decode concurrency;
approved hashes cover the complete effective reference record; document text
supports its bounded OCR length; imaging results and errors remain associated
with the requested asset. Follow-up regression cases cover mixed historical and
current symptom clauses and imaging errors without result asset IDs.

## Unfinished external validation and release gates

- The original build had no Ollama evaluation. The single-chat update includes
  four local Qwen3-VL integration demonstrations, recorded in `chat-update.md`;
  there is no clinical or population-level model evaluation. Embedding-model
  evaluation remains unperformed. On 2026-10-06 the specialist checkpoint was
  verified against its publisher SHA-256, two reviewed NIH adult PA demo images
  were registered, and real CPU scoring and browser attachment routing passed.
  See [current setup and evidence](xray_setup.md). This is integration evidence,
  not independent imaging accuracy evaluation.
- No independent clinical evaluation, calibration, thresholds, patient-bootstrap
  intervals, subgroup analysis, medically qualified policy review or dataset
  training-overlap audit is available.
- Source notes have developer review only. Expand to the blueprint's proposed
  20–40 documents and independently review claims before claiming broader coverage.
- A later development probe evaluated 37 English handwritten medicine-word crops
  and seven synthetic scan variants. The experimental local vision reader matched
  only 10/37 handwritten words and did not flag 27 incorrect readings. Full pages,
  handwritten doses and unusual layouts remain unvalidated. See the consolidated
  [evaluation report](../../EVALUATION_REPORT.md), which supersedes the early counts above.
- Clean-machine installation on another machine, packet-capture/offline network
  isolation, crash-spool cleanup/forensic storage audit and full clinical privacy
  review have not been performed. The default code avoids external inference.
- No public deployment, authenticated accounts, qualified real-patient pilot,
  release tag or clinical compliance claim is included.

These dependencies do not justify fabricated scores or expected metrics. The
interface makes unavailable features explicit and keeps supported workflows usable.
