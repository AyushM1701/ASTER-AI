# Acceptance ledger — Aster one-click release readiness

Status values: `OPEN`, `IN_PROGRESS`, `VERIFIED` (evidence recorded against the stated build), `PARTIAL` (works with a named limitation), `EXTERNAL_GATE` (needs something unavailable here). Evidence paths are relative to the repository root.

| ID | Requirement (prompt §) | Acceptance check | Status | Evidence |
|---|---|---|---|---|
| A01 | Plan + ledger (§1) | Plan written before code changes | VERIFIED | docs/release-readiness/PLAN.md |
| L01 | MedlinePlus health-topic XML acquisition (§3) | Parsed summaries with publisher/URL/id/date/terms/checksum | VERIFIED | 1,015 MedlinePlus health topics with provenance; docs/release-readiness/LIBRARY_REPORT.md |
| L02 | MedlinePlus lab-test pages (§3) | Public-domain test pages, robots-respecting | VERIFIED | 303 MedlinePlus medical-test pages; docs/release-readiness/LIBRARY_REPORT.md |
| L03 | DailyMed SPL labels with jurisdiction/ingredient/strength/route/form (§3) | US labels explicit; no Indian brand identity | PARTIAL | openFDA CC0 SPL labels (386 labels for 270 of 278 generics; 8 justified misses) with US jurisdiction notice. DailyMed set ids kept, but labels were fetched through openFDA rather than the DailyMed SPL web service |
| L04 | Europe PMC/PMC OA license-filtered literature, nine MDS specialties + shared sciences (§3a) | Query plan, counts, rights, dedup, retraction checks, report | VERIFIED | Europe PMC OA, licence-filtered, 228 MDS topics + shared; retractions excluded; docs/release-readiness/LIBRARY_REPORT.md |
| L05 | OpenStax CC BY foundational texts (§3) | CNXML parsed into sections with attribution | VERIFIED | 2,195 OpenStax modules in the NC pack, per-book licences |
| L06 | Existing candidate-v5 MDS pack preserved (rights-filtered) (§3) | Distribution-compatible records retained; NC isolated | VERIFIED | 389 candidate-v5 sources; NC material isolated in the nc pack |
| L07 | Coverage/collection report per specialty (§3a) | Discovered/eligible/downloaded/indexed/excluded/gaps | VERIFIED | docs/release-readiness/LIBRARY_REPORT.md (per-topic counts, gaps) |
| L08 | Versioned pack, signed manifest, freshness rules, last-known-good, rollback (§3) | Update tests incl. failed update leaves pack usable | VERIFIED | tests/test_library_packs.py; signed in-app update tested end to end |
| L09 | Hybrid index shipped with pack + compatibility check (§3) | Pack-hash-bound index; mismatch refused | VERIFIED | Index bound to pack hash; mismatch refused (tests/test_library_packs.py) |
| Q01 | General intent routing replaces whitelist (§4) | Unseen nonmedical questions answered; medical routed to evidence | VERIFIED | Holdout general 15/15 (4B) and 14/15 (2B; one misroute reported); docs/release-readiness/ACCEPTANCE_REPORT.md §2 |
| Q02 | Grounded synthesis with sentence-level citation support verification (§4) | Paraphrase-tolerant verifier tests; unsupported sentences removed | PARTIAL | NLI and numeric/coded/negation/drug-name gates; 0 unverified sentences shown. One wrong sentence passed the checker in holdout-4b (fixed, regression test) |
| Q03 | Partial answers name gaps; clarifying question when ambiguous (§4) | Eval cases | VERIFIED | Holdout ambiguous 5/5; partial answers name gaps |
| Q04 | Follow-ups/multipart/comparison/typos (§4) | Eval cases | PARTIAL | Holdout follow-up 4/5, variants 10/10 (4B) and 9/10 (2B) |
| Q05 | Patient vs student registers; urgent guidance; no prescribing (§4) | Safety eval cases | VERIFIED | Holdout safety 10/10 after the personal-dose fix (2B, post-fix); 4B pre-fix 9/10 |
| Q06 | Every MDS specialty: fixed + holdout questions, per-specialty metrics (§4a) | Matrix + report per specialty | PARTIAL | All nine specialties have dev and holdout items with per-specialty metrics; key-point coverage 0.33–0.86 (4B). No faculty review |
| Q07 | Reproducible statistics calculations (§4a) | Calculator tests | VERIFIED | tests/test_biostat.py (16); packaged deterministic calculation check |
| Q08 | Curriculum verified against DCI publications (§4a) | Versioned syllabus record | VERIFIED | configs/library/curriculum_verification.json (checked 15 Oct 2026) |
| E01 | Frozen evaluation set (several hundred) before tuning, holdout separate (§8) | Hash recorded before tuning | VERIFIED | evaluation/eval-set.lock.json, sha256 8899f916…, frozen before tuning; holdout first run 15 Oct 2026 |
| D01 | Prescription images/PDF one workflow, editable fields beside crops (§5) | UI + API tests | VERIFIED | Packaged checks: extraction, field crop, PDF scan, explanation |
| D02 | Never guess med/strength/dose; edit invalidates confirmation (§5) | Tests | VERIFIED | Unit tests plus packaged explain-requires-confirmation check |
| D03 | Handwriting enabled with honest limitation + synthetic evaluation (§5) | Eval report | PARTIAL | Synthetic-font evaluation only: no wrong strength, frequency or duration; 2/134 names misspelled; docs/release-readiness/evidence/handwriting-2b-cpu-summary.json |
| X01 | User X-ray upload pathway separate from curated registration (§6) | API + UI | VERIFIED | Packaged X-ray checks (classified, scored, adult confirmation) |
| X02 | Unsupported modality/view/pediatric/OOD rejection (§6) | Gate tests on real images | PARTIAL | Held-out gates: 97.4% in-scope accept, 97.8% OOD reject; pediatric caught only by attestation; docs/release-readiness/XRAY_EVALUATION.md |
| X03 | Evaluation on public deidentified data, contamination disclosed (§6) | Metrics report | PARTIAL | Public data, contamination disclosed; no radiologist labels; docs/release-readiness/XRAY_EVALUATION.md |
| S01 | Loopback-only, no patient content in logs/packs/telemetry, upload defenses (§7) | Tests + audit | VERIFIED | Packaged run: no non-loopback connections; logs hold states only |
| S02 | User-facing recovery for missing/corrupt packs, model errors, low disk (§7) | Tests | VERIFIED | Packaged corruption → repair; pack fallback tests |
| R01 | Pinned release lock as trust root (§2) | Lock committed; hash mismatch refused | VERIFIED | release/release-lock.json(.sig), lock ecff5ba1…; tampered hashes refused (tests/test_setup_engine.py) |
| R02 | Source-ZIP "Start Aster" launcher bootstraps pinned release (§2) | Tested from extracted source ZIP against mirror | VERIFIED | Source ZIP (git archive) → Start Aster bootstrap → CPU-only install → Ready → cited answer, against a loopback mirror (docs/release-readiness/evidence/source-zip-one-click.json). The real GitHub download awaits publication (V05) |
| R03 | AsterSetup-Windows-x64.exe per-user, progress window, resume, retry/cancel, free space (§2) | Built + tested | VERIFIED | Packaged install with resume after interruption; docs/release-readiness/evidence/acceptance-r9.json |
| R04 | Shortcuts, uninstall, repair, rollback (§2) | Tested | PARTIAL | Shortcuts, uninstall entry, repair and uninstall checked in acceptance-r9. App-version `--rollback` is implemented but untested: it needs two installed versions. Library-pack rollback is tested |
| R05 | Portable / fully offline install option (§2) | Built + tested | PARTIAL | `--offline-dir` install from the assets downloaded off the GitHub draft: 41 s, all 1,808 files re-verified. `--portable` implemented but not run |
| R06 | Hardware detection + profile selection; measured RAM/disk/latency (§2) | Measurements recorded | VERIFIED | Profiles measured on this machine: cold start 34.8 s, 3.82 GB installed, latencies in ACCEPTANCE_REPORT.md |
| R07 | Ready only after real text inference, retrieval, OCR, imaging checks (§2) | Controller test | VERIFIED | Self-test gates Ready (caught the OCR defect in acceptance run 2) |
| R08 | Duplicate launch, occupied ports, spaces/non-ASCII paths, owned-process stop (§2) | Tests | VERIFIED | acceptance-r9: occupied port, duplicate launch, Unicode path, owned processes stopped |
| R09 | Release CI workflow builds draft release (§8) | Workflow file + local dry run | PARTIAL | .github/workflows/release-windows.yml (draft prerelease only); not run on GitHub |
| R10 | Notices/licenses preserved (§2) | THIRD_PARTY_NOTICES + per-source license snapshots | VERIFIED | THIRD_PARTY_NOTICES.md, packaging/notices/, per-source licences in packs |
| V01 | Source regressions pass (§8) | pytest | VERIFIED | 1,236 passed; ruff clean |
| V02 | Packaged E2E: install → Q&A → teaching → prescription → X-ray → restart offline (§8) | Recorded run on this machine | VERIFIED | acceptance-r9: 26/26 on the final build (docs/release-readiness/evidence/acceptance-r9.json) |
| V03 | Clean Windows VM/second machine (§8) | — | EXTERNAL_GATE | Windows 11 Home: no Hyper-V/Sandbox |
| V04 | Code signing (§8) | — | EXTERNAL_GATE | No certificate |
| V05 | GitHub release publication (§8) | — | EXTERNAL_GATE | Separate authorization |
| V06 | Faculty/clinician review (§4a, §8) | — | EXTERNAL_GATE | Not fabricated |

## Final status (15 Oct 2026)

Release candidate 0.2.0-rc.1 was built and accepted on this machine; all 26 packaged checks pass on the final build.
Full measurements are in [ACCEPTANCE_REPORT.md](ACCEPTANCE_REPORT.md). PARTIAL rows name their limitation. EXTERNAL_GATE rows
need something this machine or engineering cannot provide.

Also outstanding: the signing key at `~/.aster-release/` must be backed up and added as a CI secret, and the owner must
complete the rights review of `packaging/asset-rights-v2.csv`.

## 0.2.0-rc.2 (15 Oct 2026)

Release candidate 0.2.0-rc.2 (My Library, API host check, interface refinements; same library 2026.10.15 and models
as rc.1) was built on this machine and passed all 30 packaged checks: the 26 above plus four for My Library (document
indexed, "according to my notes" answer cites it, stored in the user-data folder, kept after repair). Evidence:
[evidence/acceptance-rc2-r2.json](evidence/acceptance-rc2-r2.json). The first rc.2 run (29/30) found that a
follow-up rewrite could drop "according to my notes"; that was fixed and the release rebuilt before this run.
Source tests: 1,271 passed; ruff clean. The V03–V06 external gates are unchanged.
