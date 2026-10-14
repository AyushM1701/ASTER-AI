# F21 — Patient answer relevance remediation

Implementation date: 10 October 2026. Severity: P1. Status: **scoped engineering remediation implemented; independent medical correctness unmeasured**. F03 remains open. No faculty review was performed, invented or substituted with an automated score.

## What changed

Aster now distinguishes symptom information from medical teaching before searching postgraduate material. Five supported symptom families use a separate patient collection: toothache, headache, fever, sore throat and abdominal pain. A shared terminal validator checks the subject, operation, audience, required components, population and citation bindings. Missing evidence cannot fall through to a related teaching passage or pretrained model memory.

This is a bounded local patient-information pilot. It does not establish diagnosis, select antibiotics, calculate personal doses, or promise coverage of every medical question. The existing MBBS/MDS collections, reference integrity restrictions and imaging gates remain in place.

## Recorded failure and root cause

The original question was reproduced against the actual browser bridge before implementing the fix:

`What does it mean if a tooth aches?`

The recorded result was `ok`, `task_completion: true`, `answer_method: source_backed_teaching`. It contained a long tooth-eruption passage and no checked simple explanation. The selected source was Open Oregon / Laird C Sheldahl's tooth-development chapter, section “Tooth eruption”, chunk `chunk_6955e6e9a7a5219ed1ac8772`.

Evidence:

- [Original live capture](../artifacts/evaluation/f21/before/live-api-20261010T174609124369Z.json).
- [Regression fixture copied from that capture](../tests/fixtures/f21/toothache_before.json).
- [Initial failing patient regressions](../artifacts/evaluation/f21/red.txt).

The investigation found a chain of failures, rather than one bad ranking score:

| Boundary | Actual behavior before F21 | Why that mattered |
| --- | --- | --- |
| `api/chat.py` | Ordinary text entered `AnswerService`; no typed symptom intent | A benign symptom question was not inherently a diagnosis request, but had no dedicated patient operation |
| `question_plan.py` v1 | Audience `understand`, task `explain`, raw question as topic, `simple_then_deeper` | “Understand” did not impose patient suitability, symptom coverage or warning signs |
| `answers.py` | Teaching ran before primary references for non-medicine questions | The large postgraduate collection could substitute for a missing patient reference |
| `teaching_query.py` | Terms included `tooth`, `mean`, `aches`, `if`, `it` | Question scaffolding was counted as topic evidence |
| Teaching applicability | The eruption passage contained tooth/mean/if/it but did not need to address aches | Four of five counted entities could meet the existing entity overlap gate; this was not medical task relevance |
| Prepared pathway | No prepared toothache patient explanation or symptom collection | The existing 43 prepared teaching notes did not cover this patient task |
| Teaching fallback | Returned the intact retrieved section as `source_backed_teaching` | No model generation was needed to produce the failure; a stronger model alone would not fix it |
| Final validator | Checked citation/text support and treatment instructions | It did not test whether the passage answered the question or covered symptom safety |
| Completion assignment | Supported-looking output defaulted to completed | Citation validity was incorrectly standing in for task completion |
| Presentation | Unprepared long excerpt became the deeper layer, with an empty simple-layer notice | The patient received a postgraduate source dump and no useful symptom explanation |

The actual selected chunk is recorded. The original request did not log its complete ordered candidate list or numerical retrieval scores; those are not fabricated here. The token overlap explanation comes from inspecting the actual query and applicability code, not an invented semantic-confidence percentage.

Before F21, urgent-language policy existed, but ordinary symptom information had no dedicated evidence or response contract. Missing patient references were therefore an architectural gap as well as a coverage gap.

## Typed question understanding

`QuestionPlan` version 2 retains existing API audience/task fields and adds:

| Field | Meaning |
| --- | --- |
| `medical_audience` | Patient, student or research |
| `intent` | Symptom information, concept explanation, mechanism, comparison, practice or research assistance |
| `primary_subject` | Bounded symptom family when recognized |
| `requested_information` | Explicit qualifiers such as cold-triggered dental pain, biting pain or gum context |
| `patient_context` | Explicit statements, age wording, population and specified history/pregnancy; missing information is not invented |
| `safety_qualifiers` | Reported safety-related wording |
| `individualized_advice_requested` | Whether diagnosis/treatment selection is being sought; policy remains separate |
| `required_response_elements` | Meaning, possible causes, uncertainty, professional follow-up and warning signs, plus specific context where requested |

The exact toothache question resolves to patient/symptom information/toothache, with no inferred age, pregnancy, severity or medical history. Technical wording such as tooth eruption, BMPs, ligament development and odontogenic mechanisms remains educational. Personal symptom statements retain their patient operation even when technical detail is requested.

Recognizable but uncovered pain questions fail closed. Co-occurring symptom relationships and pregnancy/history-specific needs are not treated as answered by a generic card: supported general information can be `partial`, with unmet context named and `task_completion: false`. Semicolon/question-form multipart requests retain separate component contracts. This rule-based planner has bounded coverage; it is not a universal clinical language classifier.

## Task-aware evidence and shared validation

`PatientInformationStore` admits only source-bound explanation units matching the resolved subject, symptom operation, patient audience, population, requested qualifier and clear recorded conflict status. It verifies the manifest, paths, file hashes, stable reference identity, permission records, original snapshot hashes and explanation-to-source hashes. It checks currency at request time, including long-running processes.

The patient collection is small enough for deterministic applicability filtering. No arbitrary similarity/confidence cutoff was added. Existing hybrid teaching search remains available for legitimate study questions. `TeachingStore._question_groups` independently rejects symptom requests, providing another boundary against accidental direct teacher use.

`output_validation.finalize` applies the patient contract to prepared, generated, extracted and fallback output. A supported-looking eruption excerpt fails even if its citation is genuine. The guard checks:

- Subject, operation, audience and applicable population/facets.
- The exact trusted explanation unit and its role/claim-index mapping.
- Original citation identity, metadata and excerpt against the loaded source binding.
- Coverage of required elements, including mandatory uncertainty and warning signs.
- Honest partial/completion status and unaddressed patient context.
- Existing treatment/dosage restrictions and unsupported added wording.
- Absence of the postgraduate explanation-layer format on patient responses.

After a patient-contract rejection, `AnswerService` makes **one** recovery lookup in the applicable patient collection and runs the same terminal guard again. It never recursively retries the teacher/model or weakens source rules. If recovery lacks sufficient evidence, it returns `insufficient_evidence`. Critical missing meaning/uncertainty/warnings cannot produce a completed answer; missing noncritical components produce an explicit partial response.

Source integrity and a developer-approved text binding are engineering properties. They do not independently prove medical entailment, completeness, or truth. Recorded conflict flags prevent known disputed units from being used; unrecorded disagreement is not solved by this implementation.

Confirmed-document chat retains ownership/revision checks. A symptom question attached to a prescription uses its own patient evidence, rather than silently receiving the prescription's medicine explanation. Unconfirmed/stale document revisions still require confirmation. Symptom context is not inferred from an attachment.

## Patient sources, dates and permission

Release: `data/references/patient/releases/aster-patient-v1-2026-10-10`.

It contains **28 adapted explanation units, eight source records and eight original page snapshots**, plus source terms, exclusion and licence snapshots. Only selected complete text sections enter the knowledge records; headings, lists and qualifications are preserved. Third-party media, images, logos and linked material are not imported as patient teaching content.

Copied date: **2026-10-10**. Request-time expiry: **2026-10-17 UTC**. Expiry disables this collection, while urgent-language policy continues without the model or patient collection.

| Original NHS source | Publisher review | Next review due |
| --- | --- | --- |
| [Toothache](https://www.nhs.uk/symptoms/toothache/) | 2024-07-01 | 2027-07-01 |
| [Tooth decay](https://www.nhs.uk/conditions/tooth-decay/) | 2025-08-13 | 2028-08-13 |
| [Headaches](https://www.nhs.uk/symptoms/headaches/) | 2024-04-17 | 2027-04-17 |
| [Adult fever](https://www.nhs.uk/symptoms/fever-in-adults/) | 2023-05-24 | **2026-05-24, overdue** |
| [Child fever](https://www.nhs.uk/symptoms/fever-in-children/) | 2024-01-03 | 2027-01-03 |
| [Sore throat](https://www.nhs.uk/symptoms/sore-throat/) | 2024-04-08 | 2027-04-08 |
| [Stomach ache](https://www.nhs.uk/symptoms/stomach-ache/) | 2023-05-26 | **2026-05-26, overdue** |
| [Shortness of breath](https://www.nhs.uk/symptoms/shortness-of-breath/) | 2024-01-30 | 2027-01-30 |

The two overdue publisher-review dates are shown in source metadata and produce a warning in affected answers. A freshly copied page is not labelled freshly medically reviewed. This pilot retains the currently published material with that explicit qualification; independent assessment of currency is pending.

Source permissions were checked against the [NHS terms](https://www.nhs.uk/our-policies/terms-and-conditions/), [excluded content register](https://www.nhs.uk/our-policies/terms-and-conditions/content-not-licensed-for-re-use/) and [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Original unchanged passages receive NHS attribution, original-page links and copied dates. Adapted Aster explanations receive the prescribed generic public-sector reuse notice and a licence link; they are not presented as NHS-approved advice. Source jurisdiction remains UK. Local emergency-service wording does not assume UK telephone numbers for users in India.

The eight snapshots and adaptations have developer source comparison and separate licence metadata. **They are not clinically/faculty reviewed.** The licence excludes endorsement and does not turn reused material into a clinically validated product. The code's MIT licence does not replace these source terms. No third-party release was published in this task.

Additional urgent-language criteria were compared with the symptom pages above and [NHS meningitis guidance](https://www.nhs.uk/conditions/meningitis/). The latter was consulted as a safety-policy reference, not ingested into the eight-page collection. Swelling with swallowing/breathing difficulty, neck/eye swelling with toothache, sudden extremely painful headache, severe/sudden abdominal pain, inability to swallow and fever with stiff neck have tested escalation paths. Clause negation, history and educational context have regression checks. This remains a language heuristic, not validated medical triage or an exhaustive emergency detector.

### Refresh procedure

Use a **new directory/version**; do not overwrite an existing release:

```powershell
.venv/Scripts/python.exe -m scripts.prepare_patient_library --output data/references/patient/releases/aster-patient-v1-2026-10-16 --version aster-patient-v1-2026-10-16
```

The acquisition script compares intact selected text, publisher dates and permission-page text with `configs/patient_source_bindings.json`. Changed wording stops acquisition for manual source/permission reappraisal and paired-note review. `--initialize-bindings` is for the initial baseline only and cannot silently reset an existing register. A partially acquired directory is not a usable release without its validated manifest. Failure does not change the active collection.

After successful source comparison, load the candidate with `PatientInformationStore`, run the patient regression/evaluation checks using its explicit path, set `PATIENT_RELEASE_PATH` to the new version in the local environment, and restart Aster. Reuse permissions and clinical currency still need scrutiny. Keep the previous immutable directory for rollback; do not roll back to stale evidence. `ENABLE_PATIENT_INFORMATION=false` disables this pilot explicitly.

## Presentation and representative outputs

Before: no checked simple explanation, then a long BMP/root/ligament tooth-eruption passage, status `ok`, task completed.

After: the same question begins with a short meaning of toothache, followed by possible causes, uncertainty, dental assessment criteria and relevant urgent warning signs. It does not infer an abscess or choose treatment. The two supporting source passages remain in the evidence panel. Patient responses do not use student Simple/Deeper headings.

Questions about cold-triggered pain, biting pain and gum causes add the applicable context unit. Missing context coverage is named. `Tell me more` retains the preceding symptom topic; where no additional checked detail exists it says so rather than substituting a postgraduate excerpt. An explicit tooth-eruption question still enters teaching. In the live contrast set, four teaching questions returned source-backed material, while the unsupported pulpitis/periodontitis comparison and odontogenic-mechanism request returned limitations. Those four successes are availability observations, not correctness/completeness scores.

Multipart rendering preserves each response type and shows missing components. The existing dark ambient interface and source drawer are preserved. A browser check exposed bottom-of-answer scrolling; answers now open at the beginning using visible element geometry, with focus restored without scrolling the transcript away.

Screenshots:

- [Desktop patient answer](../artifacts/evaluation/f21/patient-desktop-final.jpg).
- [Phone patient answer](../artifacts/evaluation/f21/patient-mobile-final.jpg).
- [Phone evidence drawer](../artifacts/evaluation/f21/patient-mobile-sources.jpg).

## Executed evaluation and limits

The development cases have manually assigned task/intent labels. They were used to find and fix gaps, including the “aching” paraphrase and unwanted qualifier candidates. They are **not a held-out clinical benchmark**. Synthetic evidence fixtures are explicitly synthetic and separate from the installed source collection.

The engineering evaluator separates patient/student intent, retrieval applicability, completion, safety, abstention and citation checks. It does not award medical correctness, probabilities, faculty agreement or clinically validated accuracy. The four counterfactual output-mode checks use the same recorded failing passage; they are not four independent model generations. Model-outage tests demonstrate that symptom paths avoid model/fallback use, rather than fault-injecting a live Ollama outage.

Live testing uses the same-origin browser bridge, real installed sources and actual session creation/deletion. Status expectations for student queries allow supported output **or** an honest evidence limitation; this is not a student task-completion score. Browser interactions separately verified the exact failure, source placement, phone drawer, follow-up limitation and legitimate eruption query. The phone DOM reported no horizontal document overflow. The Impeccable detector reported no findings for the changed JS; it is not an accessibility certification.

### Modified modules and function boundaries

Measured results (developer evaluation, not clinical accuracy):

| Measure | Numerator / denominator | Exact scope |
| --- | --- | --- |
| Patient intent/subject labels | 26 / 26 | Five symptom families, uncovered pain, combined symptoms and pregnancy context |
| Student intent preservation | 6 / 6 | Dental teaching contrasts; does not score their answers |
| Relevant-unit precision | 123 / 123 | Eligible patient units across the labelled queries; metadata applicability |
| Relevant-unit recall | 123 / 123 | Eligible bound units in this finite release; not recall across the web or medical literature |
| Complete patient tasks | 22 / 22 | Meaning, causes, uncertainty, follow-up, warnings and requested supported dental qualifier |
| Expected patient status | 26 / 26 | 22 complete, two partial, two insufficient-evidence outcomes |
| Irrelevant-output rejection | 4 / 4 | One actual failure fixture relabelled as four output methods |
| Unsupported accepted output rate | 0 / 4 | Same four negative output-mode probes only |
| Appropriate abstention | 2 / 2 | Uncovered finger/ear pain |
| Partial completion honesty | 2 / 2 | Interacting headache/fever and pregnancy-specific abdominal context |
| Safety policy labels | 10 / 10 | Five urgent, two treatment-blocked and three benign/educational probes |
| Citation IDs bound to returned references | 123 / 123 | Patient claim/reference links, not independent claim entailment |
| Live expected-status checks | 42 / 42 | 26 patient, six student and ten safety requests through the real browser bridge |
| Full source regression suite | **633 passed, zero failed** | Includes 64 patient-relevance and four JS renderer/scroll tests; one existing Starlette/httpx deprecation warning |
| Medical factual accuracy / faculty scores | **Not measured** | No qualified independent review |

The first evaluation run found one unrecognized “aching” paraphrase and surplus qualifier candidates. That evidence is retained rather than replaced: [initial engineering run](../artifacts/evaluation/f21/engineering-20261010T181533564884Z.json). The later passing set is a development/regression set, not unseen evidence of generalization.

Final artifacts:

- [Engineering metrics and complete responses](../artifacts/evaluation/f21/engineering-20261010T182050987421Z.json).
- [Actual live requests, health, source responses and session deletion](../artifacts/evaluation/f21/after/live-api-20261010T182120350537Z.json).
- [Full final pytest output](../artifacts/evaluation/f21/final-verification.txt).
- [Browser symptom DOM](../artifacts/evaluation/f21/patient-desktop-dom.txt), [follow-up DOM](../artifacts/evaluation/f21/browser-followup-dom.txt), [student DOM](../artifacts/evaluation/f21/browser-student-dom.txt).
- [Phone width measurements](../artifacts/evaluation/f21/browser-mobile.json), [final Impeccable detector](../artifacts/evaluation/f21/impeccable-detect-final.json), and [final ready-state check](../artifacts/evaluation/f21/final-health.json).

Patient-store initialization took **16.16 ms** in the measured process. Traced retained Python allocations were **164,356 bytes**, with **316,808 bytes** peak during initialization. Warm offline patient requests had **0.441 ms median**, **5.598 ms maximum** across the 26 questions. These figures exclude models, the teaching index, network and process RSS. The live bridge's corresponding patient requests had **8 ms median**, **15 ms maximum**, with times rounded to milliseconds. This is one local run, not a load/capacity benchmark. The complete API still loads large reference and teaching indexes; F21 does not claim to fix their startup/memory footprint.

Reproduce the focused engineering evaluation with `.venv/Scripts/python.exe -m scripts.evaluate_f21` while its explicitly selected release is current. For a newly appraised candidate, change the explicit candidate path in the evaluation configuration before comparing results; never silently reset a stale date to make a score pass. Run `.venv/Scripts/python.exe -m pytest -q` for source regressions.

| Module | Change |
| --- | --- |
| `api/chat.py: chat` | Keeps document confirmation, routes symptom requests to their own answer contract |
| `services/question_plan.py: QuestionPlan, understand_question, plan_question` | Typed patient/student intent, subject, context, qualifiers and required elements |
| `services/patient_information.py` | Versioned permission/integrity/currency admission, applicable evidence, response assembly, patient terminal validation |
| `services/answers.py: AnswerService.answer, _answer` | Patient route before teacher/model, shared finalization, one bounded recovery, multipart contracts |
| `services/teaching.py: _question_groups` | Rejects patient symptom requests at direct teaching boundary |
| `services/explanation_layers.py: present_answer` | Preserves patient and multipart presentations without student layering |
| `services/output_validation.py: finalize` | Patient relevance/completion checks alongside existing source and treatment checks |
| `services/policy.py: check_policy` | Additional source-informed urgent wording and contextual regression handling |
| `config.py, main.py` | Patient feature/path settings and readiness metadata |
| `frontend/web/app.js` | Patient sections, evidence attribution, multipart rendering and answer-start scrolling |
| `scripts/prepare_patient_library.py` | Immutable source acquisition, section extraction and permission/source change detection |
| `scripts/evaluate_f21.py` | Explicit engineering labels, denominators, artifacts and bounded overhead measurements |
| `tests/test_patient_relevance.py, tests/patient_fixtures.py, tests/test_patient_rendering.py` | Actual failing fixture, applicability, completeness, outage, safety, recovery, document and renderer regressions |

`teaching_query.py` and general hybrid ranking were inspected but not globally weakened or given an invented relevance threshold. The bounded patient admission path removes their authority to answer symptom requests. The existing missing-library regression in `test_knowledge_v2.py` now explicitly disables patient information: adding real stomach-pain coverage must not turn a missing-library test into a different scenario.

### Remaining requirements

- **F03 remains open:** no independent qualified reviewer, factual-correctness score, clinical validation or release certification.
- Broader symptom/source coverage, Indian patient guidance and jurisdiction-specific pathways need separate source and permission work.
- Rule-based intent and emergency language need larger independently labelled benchmarks, including misspellings, multilingual wording, negation and complex histories.
- Generic cards cannot resolve interacting symptoms, pregnancy/history-specific assessment, differential diagnosis or treatment. They mark unsupported context rather than completing those tasks.
- Publisher-overdue sources require currency review; seven-day snapshot refresh does not provide that review.
- Source-bound paraphrases need independent medical entailment/completeness review; recorded conflict flags do not discover all contradictions.
- Existing student source-excerpt verbosity, unsupported comparisons/mechanisms and broad F20 task validation remain separate gaps. A preserved teaching answer is not automatically a faculty-quality explanation.
- This task did not rebuild/test the frozen Windows installer or publish a new release. Packaged patient-source redistribution remains subject to its own manifest and rights review.

Within the stated five-family scope, the original failure, relevant evidence routing, source-dump rejection, patient structure, dental follow-up/warnings, missing-source limitations, shared validation, safety regressions and browser-to-backend behavior are verified. Universal semantic relevance and medical accuracy remain unverified.
