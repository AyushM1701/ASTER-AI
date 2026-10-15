# Aster implementation prompt: broad answers and one-click distribution

Paste the following into the coding agent working in this repository.

```text
Complete the existing ASTER-AI project as a distributable, local-first medical information and education application. Implement the work, verify the actual packaged application, and produce release artifacts. A plan, another source collection, a UI mockup, or passing source tests alone does not satisfy this task.

The required experience: an ordinary Windows user downloads the project from GitHub, opens a clearly named launcher, and gets a working application. Setup supplies every required runtime, model, OCR component, medical reference pack, and search index automatically. Users must never hunt for medical sources, assemble a library, edit .env, enter terminal commands, install Python/Docker/Ollama/Tesseract, register for a model service, or supply API keys for the default experience. First installation may require internet and time to download assets; explain this in the launcher. Subsequent core use must work offline.

Interpret “answer any question” as broad medical and general conversational coverage, including postgraduate questions across every MDS specialty, useful follow-ups, and honest handling of uncertainty. Never promise universal correctness. Interpret X-ray reading as assistance within measured supported imaging scope, with professional confirmation of findings. Distinguish software readiness from clinical validation; don't claim autonomous diagnosis or treatment readiness based on engineering tests.

1. Inspect and finish the existing project.

Read repository instructions, current code, README.md, docs/PUBLISHED_REFERENCE_LIBRARY.md, docs/WINDOWS_RELEASE.md, docs/WINDOWS_RELEASE_EVALUATION.md, packaging/release-profile.json, packaging/asset-rights.csv, current patient/teaching reports, and the latest implementation ledger. Verify historical claims against current code and assets. Preserve unrelated changes, existing working workflows, session ownership, and source attribution.

Reuse the FastAPI backend, existing web frontend, local inference adapters, and Windows packaging wherever practical. Focus on backend/app/services/answers.py, question planning/retrieval, patient_information.py, documents.py, uploads.py, xray.py, the OCR/vision adapters, frontend/web, packaging, aster_release, and release CI. Avoid an unrelated rewrite or speculative model training.

Known issues to investigate: a checkout lacks configured runtime assets; the frozen profile is ValidationOnly and disables handwriting and X-ray scoring; general chat recognition is narrowly enumerated; specialist X-ray analysis requires registered image hashes; prepared teaching coverage is incomplete; the bounded patient pack has a short expiry. Historical candidates and old package tests do not establish readiness of the final release.

Write a short implementation plan and an acceptance ledger, then execute all dependency-ready engineering work. Use reasonable defaults. Record actual external blockers without repeatedly asking the owner to perform routine setup or find sources.

2. Make setup and launch a complete product feature.

Ship AsterSetup-Windows-x64.exe, a portable distribution, a desktop/Start Menu icon, and a clearly named Start Aster launcher in the GitHub source ZIP. The source-ZIP launcher must bootstrap a pinned, verified release automatically, without assuming a developer runtime. A release installer alone does not satisfy the source-ZIP requirement. Keep development installation separate in the README.

Install per user without administrator privileges where possible. Bundle or automatically acquire required runtime binaries, text/vision weights, embeddings, OCR language data, imaging weights, references, and compatible indexes. Use authenticated version manifests and verified downloads; an untrusted checksum fetched beside an untrusted binary is insufficient. Preserve license notices.

Provide a native progress window showing download size, free-space requirements, stage, progress, retry/cancel, and useful errors. Support interrupted-download resume, checksums, safe archive extraction, atomic installation, repair, rollback, and uninstall. Handle paths with spaces/non-ASCII characters, duplicate launches, occupied ports, antivirus interruptions, and failed model warm-up. Stop only owned processes. Show Ready only after real text inference, retrieval, OCR, and supported imaging capability checks succeed.

Detect hardware. Choose an evaluated CPU-capable default with no mandatory GPU; enable better measured profiles where resources permit. Measure actual RAM, disk, cold-start time, and response latency. Don't invent hardware requirements or claim acceptable performance on untested machines. Provide a fully downloaded offline installation option.

3. Ship and maintain the medical library automatically.

Build a useful rights-cleared reference release during development/release CI. Include the pack and matching indexes in release assets, so first use does not depend on live publishers being available. Users should receive the library automatically with the application.

Implement source-specific acquisition, parsing, normalization, deduplication, metadata, attribution, incremental updates, and index generation. Use provider-approved APIs/bulk downloads, reasonable rate limits, retries, and caches. Each source record must retain publisher, URL, document identity, jurisdiction, version/date, acquisition date, applicable reuse terms, checksum, and evidence location. Build pack/source/index compatibility checks and rollback.

Start with MedlinePlus health-topic XML summaries and other explicitly reusable patient/test information; licensed open educational texts for foundational medicine and dentistry; permitted public-health guidance; appropriate drug-label sources such as DailyMed; and license-filtered PMC Open Access literature for teaching/research. Verify current terms per source. MedlinePlus's third-party drug monographs and encyclopedia content are not automatically reusable. PMC availability does not imply redistribution permission. Don't bulk scrape arbitrary publisher pages or assume a dataset uploader owns retailer content.

US labels must not silently identify Indian brands or establish local prescribing guidance. Keep drug jurisdiction, ingredient, strength, route, and formulation explicit; acquire permitted regional information or report uncertainty. Brand similarity is not an identity match.

Separate patient guidance, professional/student explanations, drug/product information, and research evidence. Retailer descriptions and isolated research papers must not replace authoritative symptom guidance. Preserve legitimate existing MBBS/MDS coverage. Select distribution-compatible content for the default edition; isolate restricted/noncommercial packs according to their terms. Replace unresolved sources with permitted alternatives where feasible instead of declaring the entire task blocked.

Add automatic versioned library maintenance with integrity checks and a last-known-good offline pack. Define freshness rules appropriate to content risk; don't present obsolete patient/drug guidance as current. Failed updates must leave intact packs usable within their supported freshness policy. Don't disable the whole application because one small symptom pack expires. New content must pass quality/rights checks before activation; automated checks cannot stand in for medical review.

3a. Automatically discover and collect medical and dental knowledge from the web.

Source discovery and acquisition are required implementation work. The developer must not ask the owner or students to find sources, provide a reading list, download papers, or manually build the reference library. Build and run an automated collection pipeline spanning all nine MDS specialties, shared basic sciences, patient information, medicines, and the other supported medical domains. Continue beyond existing source lists and arbitrary small demonstration collections.

Systematically seek relevant studies, research papers, review articles, systematic reviews, meta-analyses, clinical guidelines, consensus statements, case reports, educational articles, permitted book chapters, clinical trial records, and research datasets. Include foundational literature and recent advances. Define explicit specialty/topic queries, synonyms and MeSH terms where appropriate, date ranges, providers, inclusion/exclusion rules, and coverage targets. Track what was searched and collected; don't claim “all web data” or exhaustive coverage of sources that were not searched or could not be accessed.

Use PubMed/NCBI discovery services, permitted PMC and Europe PMC full-text services, and other suitable official scholarly metadata providers, institutional repositories, public-health/regulator sites, professional organizations, and publisher open-access feeds. Verify current provider interfaces and reuse terms. Use approved APIs, bulk feeds, and expressly permitted crawling instead of bypassing rate limits, CAPTCHAs, paywalls, authentication, or technical access controls. Prefer no-key public services for default operation; optional developer credentials must not become an end-user requirement.

Automatically resolve identifiers and discover permitted full-text versions. Normalize DOI, PMID, PMCID, titles, authors, publication dates, journals, article type, specialty/topic, and version relationships. Deduplicate the same work across providers; distinguish preprints, accepted manuscripts, published versions, corrections, and retractions. Record the acquisition endpoint and provenance chain. Keep metadata-only, abstract-only, and full-text records distinct. If full text is unavailable or reuse is restricted, retain only permitted metadata/content and an original-source link, and report the access limit; never invent the unavailable contents or present an abstract as a full-paper appraisal.

Parse permitted HTML, XML/JATS, and PDFs into evidence units with headings, page/section references, tables, captions, references, and usable provenance. Evaluate PDF reading order and table/numeric extraction; mark unreliable extraction rather than silently treating it as valid evidence. Process supplementary files and datasets only where scope, file safety, deidentification, and reuse terms permit. Access, redistribution, adaptation, and model-training rights are separate decisions. Collection for retrieval must not silently become model training.

Screen source quality and study type. Preserve evidence limitations, sample/population context, publication status, conflicting results, and jurisdiction. Label preprints and case reports clearly; they must not be represented as established clinical recommendations. Check correction/retraction notices during updates and remove superseded evidence from active recommendation pathways while retaining an audit trail. Automated quality screening is not a claim of clinician appraisal.

Implement durable acquisition checkpoints, pagination, retries/backoff, provider-specific rate limits, resumable downloads, bounded resource usage, exclusion logs, and incremental update tracking. Run initial acquisition during development/release preparation, inspect output quality, build tested reference packs/indexes, and include the usable baseline in installation. A list of URLs, staged files, or collection scripts that were never run is not delivery. Automatically discover new material and refresh versioned packs through an opt-in network/update policy. Supplementary expansion must respect local storage limits; a useful baseline across every MDS specialty must work without waiting for an unbounded web crawl.

Produce a collection and coverage report per specialty/topic: queried providers, date ranges, discovered/eligible/downloaded/indexed counts, deduplications, unavailable full texts, exclusions and reasons, rights decisions, parse failures, evidence gaps, and latest update dates. Evaluate whether the acquired evidence actually supports representative postgraduate questions. The goal is broad usable knowledge with traceable coverage, not a large file count. Patient uploads and personal questions must never enter a shared web collection; external searches must follow the disclosure/opt-in rules in section 7.

4. Make answers broad, useful, and evidence-aware.

Replace exact-question lists and prepared-answer dependence with general intent/topic planning, hybrid retrieval, query expansion, and contextual follow-up handling. Support paraphrases, typos, unfamiliar wording, multipart questions, and comparisons. Maintain the distinction between patient explanations and exam-level teaching. Existing prepared material may improve answers but must not define the entire supported vocabulary.

Use an evaluated local model for synthesis. Medical assertions need applicable retrieved evidence; citations must support the attached claims rather than merely mention the topic. Distinguish evidence-derived content from general conversation. Avoid fabricated references, invented drug identities, and confident model-memory medical answers when evidence is inadequate.

Give the supported portion of an answer when evidence is partial, identify the gap precisely, and ask a focused clarifying question when needed. Ordinary explanatory questions should receive actual explanations, not blanket refusals or raw excerpts. Keep necessary safety controls while fixing false positives. Test unsupported-claim detection; exact-string equality with a source passage is not an adequate general solution for validating paraphrases.

Cover symptoms, conditions, tests/report terminology, medicines, prevention, anatomy, physiology, pathology, dental topics, MBBS/MDS study, and research explanation. Handle ordinary nonmedical questions without a small hardcoded whitelist. Explain uncertainty and appropriate next steps for patient questions; use relevant evidence-based urgent guidance when warranted. Don't diagnose conclusively, prescribe, or change a person's treatment. Clearly distinguish explaining a clinician's written dose from recommending a new dose.

4a. Make every MDS specialty an explicit acceptance requirement.

An MDS student in any of these nine specialties must be able to ask open-ended questions in ordinary language and receive relevant postgraduate-level explanations:

- Oral and Maxillofacial Pathology and Oral Microbiology, including forensic odontology.
- Oral Medicine and Radiology.
- Oral and Maxillofacial Surgery.
- Conservative Dentistry and Endodontics.
- Prosthodontics and Crown & Bridge.
- Periodontology.
- Orthodontics and Dentofacial Orthopaedics.
- Pediatric/Pedodontics and Preventive Dentistry.
- Public Health Dentistry.

Include shared applied basic sciences, dental materials, pharmacology, relevant medicine, research methodology, biostatistics, evidence appraisal, and interdisciplinary topics. Verify the applicable national curriculum and amendments against current official regulator publications; preserve syllabus versions and reconcile existing incomplete mappings. Support institution-specific syllabus overlays when legitimately available, while keeping a complete national baseline that needs no student-supplied files.

Support definitions, mechanisms, classifications, clinical and histopathological features, radiological principles, differential-diagnosis reasoning, investigations, treatment principles for educational cases, complications, prognosis, comparisons, long/short exam answers, MCQs with explanations, viva and follow-up questioning, case discussions, seminar outlines, thesis methodology, and appraisal of recent research. Match the requested depth and format. Use reproducible checked calculations for applicable statistics and label assumptions. Educational discussion of procedures or treatment must stay distinct from personal clinical instructions and from proof of practical competence.

Do not limit the product to oral pathology, selected prepared topics, the owner's supplied questions, or a small bank of memorized answers. A student must be able to ask a new question, combine concepts across specialties, request an explanation of the reasoning, and ask progressively deeper follow-ups. The retrieval and synthesis system must generalize beyond exact wording and registered topic IDs. Where classifications or recommendations differ by edition/date, identify the applicable source version and disagreement.

Automatically acquire and install permitted postgraduate references for each specialty. A curriculum name or topic registry entry does not establish answer coverage, and general patient summaries cannot by themselves support specialist depth. Map each major syllabus domain to usable evidence and representative tasks; audit gaps in actual content and supported reasoning operations. Optional student-uploaded papers or books may supplement permitted private-session workflows but must not be prerequisites for baseline MDS support.

Create a specialty-by-topic-by-task acceptance matrix, with fixed representative questions and separate holdout questions covering foundational and advanced material in every specialty. Measure substantive completion, depth, relevance, factual/source support, correct uncertainty, and follow-up consistency per specialty. Report coverage holes per specialty rather than hiding them in an aggregate score. Require documented MDS faculty review for claims of educational validation; don't fabricate it. Don't declare all-MDS readiness based on a few successful oral-pathology examples, source counts, or listed curriculum names. Actual analysis of dental radiographs or histology uploads still requires separately evaluated image capabilities; explaining their textbook features does not establish that image-analysis capability.

5. Finish prescription and document reading.

Support common printed and handwritten prescription photos and scanned PDFs through the same attachment workflow. Implement safe decoding, rotation/crop handling, image quality feedback, PDF limits, and OCR/vision extraction. Preserve original text and structured fields: medicine, ingredient if verified, strength, dosage form, written dose, route, frequency, duration, and instructions.

Show editable fields beside their source image/crop. Mark ambiguous/missing content explicitly. Never guess a medicine, strength, decimal, unit, or dose from plausible handwriting. Use confidence/quality indicators with honest semantics. Require review of medication-critical transcription before explanation; editing invalidates earlier confirmation. Explain confirmed content in plain language using applicable references. Avoid unsupported interaction checks or reassurance about a regimen. Keep difficult handwriting as an explicit limitation until independently evaluated.

6. Finish real uploaded X-ray assistance.

Create a separate user-upload pathway rather than forcing users to pre-register patient images in the curated benchmark manifest. Retain curated registration for dataset provenance/evaluation. Preserve upload ownership, privacy, quality checks, and model/weight integrity.

Begin with adult frontal chest X-rays if that is the existing model's validated input domain. Detect unsupported modality, body region/view, pediatric images, unreadable photos, and out-of-distribution inputs as far as evaluated methods allow; disclose detection limits. Reject unsupported input without invented findings. Don't pretend a chest model reads dental, limb, lateral, CT, or MRI images. Additional imaging types need their own suitable models, preprocessing, permissions, and evaluations.

Bundle or automatically install the permitted specialist weights and dependencies. Use preprocessing required by the actual checkpoint. Provide image observations/model findings, source-linked explanations, quality limits, and explicit clinician/radiologist review. Research scores must not be described as calibrated probabilities. A low score must not establish a normal image or rule out disease; a heatmap must not be presented as a verified lesion location.

Demonstrate the shipped workflow on supported uploads outside the two registered demos. Use legitimate deidentified evaluation data with clear provenance and patient-level separation. A single plausible output or generic vision-model description is not proof of radiological accuracy. Keep the feature labeled according to its actual evaluation status.

7. Protect patient material and make failures recoverable.

Default to local processing, temporary patient sessions, explicit saving, and deletion. No patient content in shared reference packs, telemetry, training data, logs, Git commits, or release artifacts. Defend against unsafe uploads, PDF/archive bombs, path traversal, cross-session access, and document prompt injection. Bind services to loopback by default. Keep secrets out of source.

Automatic asset downloads must not transmit patient content. Any optional external research/model service requires clear disclosure and opt-in for the content being transmitted. Provide user-facing recovery for missing/corrupt packs, model errors, low disk, and service failure rather than exposing stack traces or asking patients to debug configuration.

8. Verify the exact deliverable and report honestly.

Run relevant source regressions and actual end-to-end tests. Create a fixed evaluation set before tuning, with several hundred varied medical/student/general questions, prescription cases, supported/unsupported X-rays, ambiguous inputs, and safety cases. Report coverage, useful-answer completion, citation support, unsupported claims, critical-field transcription errors, imaging metrics where legitimate labels exist, and performance. Keep tuning cases separate from the final holdout; label AI-authored/developer-reviewed cases honestly. Don't manufacture clinician labels or independent review.

Test the final installer and source-ZIP launcher on a clean supported Windows machine/VM with no developer tools, model cache, references, or private .env. Verify automatic setup, real inference, patient Q&A, teaching, prescription extraction/review/explanation, and supported X-ray assistance. Repeat after restart with networking disabled. Test interrupted downloads, repair, corrupt assets, paths with spaces/non-ASCII characters, low disk, and uninstall. Test every OS/hardware profile you claim to support. Record evidence against the exact commit and release manifest.

Deliver the working implementation, source bootstrap, installer/portable artifacts, versioned library/model manifests, notices, release build workflow, ordinary-user README, and acceptance report. Every promised workflow must work in the actual package; disabled flags, local-only assets, mocks, and developer-machine success are insufficient. If required clinical review, code signing, release credentials, clean-machine access, or another external prerequisite is unavailable, finish all possible engineering work and name the exact remaining gate. Don't mark the project fully ready while mandatory gates remain.

Prepare a concrete GitHub release candidate; publishing is a separate authorized action. Never publish restricted assets or claim clinical validation without evidence. Conclude with what works, what was measured, the downloadable artifact locations, and any remaining limitation affecting the requested experience.
```

Source starting points verified on 14 October 2026:

- [MedlinePlus XML](https://medlineplus.gov/xml.html)
- [MedlinePlus content reuse](https://www.medlineplus.gov/about/using/usingcontent/)
- [DailyMed web services](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm)
- [PMC Open Access Subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/)
- [NCBI E-utilities guidance](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [Europe PMC literature API](https://europepmc.org/RestfulWebService) and [open-access reuse/download guidance](https://europepmc.org/downloads/openaccess)
- [Official MDS curriculum regulations](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf) and [regulations/amendment listing](https://dciindia.gov.in/GazetteList.aspx)

Provider terms and interfaces must be checked again during implementation.
