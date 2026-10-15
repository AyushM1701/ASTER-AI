# Product scope implementation — 11 October 2026

This implements the remaining local workflow infrastructure in the owner's 10 October scope. It is a development pilot. Independent clinician/faculty review, real-user comprehension and exact-release distribution evidence are not supplied by software implementation.

## What you can use

The same dark conversation and right-hand evidence panel now offer **automatic task selection, Understand, Study & practise, and Research & Write**. Recognized study follow-ups retain their topic/task. Explicit task selection can override presentation; it cannot authorize personal diagnosis, medicine selection or dosing. Generic study follow-ups cannot revive detached document context.

**Study topics & saved work** opens an optional inline workspace. The installed pack exposes 43 source-checked prepared topics and their declared activities, including a ten-topic Oral Pathology pilot. Basic comparisons use both bound reference notes; bounded mechanism activities use admitted notes. Source-based viva activities are ungraded. Answer reviews and fictional-case reflection explicitly return partial completion: Aster supplies a reference/rubric rather than pretending to perform qualified assessment. Curriculum identifiers are shown where source metadata contains a mapping; otherwise mapping remains pending. This topic list is not comprehensive MBBS/MDS operation coverage.

To save a study attempt, enable local saving, choose **Record study attempt** under a student answer, then record your self-assessment and weak concepts. Attempts, the latest weak areas and revisit dates persist independently of the chat session. Revisit intervals are simple reminders (one/seven days), not an evaluated learning algorithm. The last 20 attempt details and a cumulative count are retained per topic. Educational export/delete controls do not include patient images or confirmed prescription text.

**Research & Write** requires a focused public question, population/context, article type and Europe PMC query. The user confirms that no patient identifiers are included before the query leaves the computer. Search is one provider, first relevance-ordered page, 1–20 records, with at most three optional full-text requests. Inclusion/exclusion criteria are recorded for manual screening, not claimed as automatically satisfied. Provider failures produce explicit errors and save no success project.

Each project records UTC search time, exact parameters, hit/received counts, duplicate/conflict handling and response hash. Bibliographic identifiers, title, authors and year are checked against the returned provider record; this is not independent publisher or medical verification. Retractions and corrections reported by the provider are tracked, with retractions preserved when duplicates merge. Conflicting identities and publication notices are excluded from draft evidence. Absence of a provider notice means **notices not reported**, not a guarantee of no retraction.

Abstract access remains distinct from full-text inspection. Copyrighted abstracts retain at most 25 quoted words per paper and mark incomplete fragments. Full text is admitted only after matching article identifiers and a machine-readable CC BY 3.0/4.0 or CC0 licence; unsupported permissions retain abstract/link access. JATS uses a hardened XML parser that does not fetch external DTDs and rejects entity expansion. Only selected full-text paragraphs are retained, not an assertion of comprehensive critical appraisal.

The evidence panel keeps each study separate. Methods/findings/limitations/population fields quote identifiable inspected sections; unavailable fields say so. Applicability, bias and contradictions require appraisal and are not guessed. The editable Markdown review scaffold includes search methods, per-study evidence, passage IDs, bibliography, discussion/conclusion prompts and explicit gaps. BibTeX uses separate structured authors. Original participants, analyses, significance, ethics approval and citations are never generated. Publication, author outreach and submissions are absent.

You can edit and explicitly save a draft, download Markdown/BibTeX/JSON and reopen a project. Edited writing is always **unverified user writing**, separate from exact-bound evidence. Revision checks prevent stale browser saves. Unsaved edits are retained per project while the page is open, with a browser leave warning; saving or exporting is still required for durable retention.

**Plain-text report terminology** is separately bounded/tested: `Explain this report: Hb: 12 g/dL; Glucose: 110 mg/dL`. Only hemoglobin and glucose terms are currently supported, using short inspected MedlinePlus quotations. Values, flags, reference ranges, normality, diagnosis and treatment are not interpreted. Every other supplied line is marked unsupported. Image lab-report ingestion remains future work. Prescription OCR confirmation and X-ray research gates retain their existing requirements.

## Storage, network and limits

- Temporary sessions, prescription fields and images remain in-memory and expire under existing session rules.
- Explicit educational saves use `data/workspaces/education.sqlite3` (git-ignored), maximum 100 records per owner per type, at most 2 MB per stored record. Database creation is lazy; browsing without saving creates no persistent database.
- A random 256-bit capability in this browser's local storage identifies the educational workspace; the database stores its hash. The capability is independent of temporary session tokens, and routes require both an active owned session and the workspace capability. This remains a local single-user design, not multi-user account authentication.
- Saving can be switched off without deleting prior work. Clearing a conversation does not clear educational work. Explicit educational deletion removes its records; downloaded exports remain. Clearing browser storage loses access to its saved capability, so export first. Local database contents are not encrypted; a filesystem administrator can access them. No patient attachment is copied into this database automatically.
- Local inference has no cloud model fallback. Public literature queries are the new optional network use; set `ENABLE_RESEARCH_SEARCH=false` to disable it. Provider URLs/identifiers are fixed and validated; user URLs are not fetched.
- Source freshness checks, qualified review and distribution permission gates remain active. The patient collection's seven-day freshness deadline is a source refresh rule, not expiry of the model or application.

## Verification and honest completion

Artifacts: `artifacts/evaluation/product-scope-2026-10-11/`. `scripts/evaluate_product_scope.py` reproduces the narrow oral-leukoplakia search; `--journeys` probes the running local API. These are development cases with known design context, not a locked independent medical holdout.

The initial journey probe exercised ten patient questions, ten student definitions, ten viva activities and five study operations: 35 HTTP successes; 32 `ok`, two deliberately partial reference/rubric activities and one appropriate medicine-reference refusal. The installed medicine library did not contain an applicable clinical monograph for the exact metformin formulation query; no unsupported instructions were substituted. This remains a visible patient-pilot content gap.

The public Oral Pathology search returned ten records with three admitted permitted full texts. Exact passage bindings and bibliographic structure were checked; medical synthesis, consensus, manual screening and qualified accuracy were not evaluated. Project `task_completion` remains false while these stages are incomplete, with stage-level progress recorded separately.

The fresh implementation review identified missing passage exports, unsaved-draft loss, malformed multi-author BibTeX and retraction downgrade on duplicate merging. All were repaired; new regression cases cover backend defects. Browser verification covers the draft restoration journey separately.

The full source suite passed **664 tests in 58.96 seconds**. After the final local-date revisit repair, all **31 affected workflow tests passed in 7.77 seconds**. Whole-repository Ruff checks and the final JavaScript syntax check passed. The suite reports one existing Starlette/httpx deprecation warning. These totals measure engineering regression checks, not medical accuracy.

The real browser journey verified public search, a ten-record/three-full-text evidence panel, a downloaded Markdown scaffold containing all ten supporting-passage sections, unsaved draft restoration, explicit draft saving, and study self-assessment. Saved projects and study attempts reopened after an application restart and a page reload. A revisit saved on 11 October uses the computer's local date and displays 12 October. Reopening a research project restores the Research & Write selector. A startup-only workspace notice clears once the session is ready. The mobile evidence drawer at 390 × 844 has a 390-pixel document width, no horizontal overflow, focus on its close control, and no captured console errors.

Browser proof: [desktop research](../../artifacts/evaluation/product-scope-2026-10-11/research-desktop.jpg), [mobile evidence](../../artifacts/evaluation/product-scope-2026-10-11/research-mobile.jpg), [saved-work workspace](../../artifacts/evaluation/product-scope-2026-10-11/saved-workspace-desktop.jpg), and [downloaded review scaffold](../../artifacts/evaluation/product-scope-2026-10-11/browser-review-export.md). Synthetic pilot records remain in the tested browser workspace; they contain no patient data. The temporary test tab was closed and the original user tab preserved. Reload the original application page to load the new interface/session.

The Impeccable static detector's asset-path and hidden-upload warnings were not treated as a clean automated visual result; actual DOM, computed sizing and screenshots supply the visual evidence above. Its stale design sidecar was reported and left unchanged.

## Scope requirements still requiring evidence or further work

| Requirement | Current state |
|---|---|
| Common answer checks, mixed-question coverage, task honesty | Existing foundation retained; structured presentation binding checks added. Arbitrary semantic applicability/contradictions are not solved. |
| Approximately ten patient and ten student pilot topics | Defined/probed; exact medicine-monograph gap recorded. Real patient/student usability testing pending. |
| Fully mapped curriculum operation packs | 43 prepared topics with declared activities and available source mappings; full competency-level coverage remains incomplete. |
| Reviewed practice/medical correctness | Developer source comparison and ungraded rubrics available. Independent faculty/clinician review (F03) remains open. |
| Every kind of meaningful follow-up | Topic/task continuity and safe extra-detail abstention available; unsupported new depth remains explicit. |
| Research search, bibliography, evidence, outline, draft and export | Bounded pilot implemented. Critical appraisal, contradictions, faithful synthesis and manual screening remain unmeasured/pending. |
| Original research data analysis | No fabricated results; reproducible statistical analysis of supplied datasets is a future, separately tested feature. |
| Sanitized diagnostics, new OCR/imaging accuracy evaluation | Existing safe route/status logging and earlier gates retained; no new clinical or handwriting accuracy claim. |
| Asset rights and clean-machine one-click distribution | Outstanding exact-release review/installation gates. Prior ValidationOnly bundle does not include these changes. |

Authoritative implementation references: [Europe PMC API](https://europepmc.org/RestfulWebService), [reuse restrictions](https://europepmc.org/help), [hemoglobin terminology](https://medlineplus.gov/lab-tests/hemoglobin-test/), [glucose terminology](https://medlineplus.gov/lab-tests/blood-glucose-test/). Free access is not unrestricted reuse.
