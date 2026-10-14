# Curriculum assessment register and human review

The blueprint contains 9,144 written prompts for 3,048 active assessment items.
These are curriculum scope and handling probes, not independently validated clinical
answer keys. All reference agreement and qualified faculty accuracy scores remain null.

| Register | Items | Notes |
|---|---:|---|
| MDS theory | 249 | Named syllabus topics; grouped source bullets split into discrete subjects |
| MDS practical | 44 | Written principles only; observed performance unassessed |
| MDS research | 8 | Actual project execution and research output unassessed |
| MDS communication | 5 | Actual presentation and interaction unassessed |
| MBBS active numbered subject competencies | 2,626 | 19 subjects; deleted PS9.2 retained inactive |
| MBBS programme objectives | 58 | Foundation, early exposure, electives, ethics, integration, clerkship |
| AETCOM Appendix 1 competencies | 54 | 39 core, 15 desirable; directed by 2024 curriculum |
| MBBS malformed-code source entries | 4 | Text preserved separately; no official codes guessed |

The original 89 photographed entries in `configs/mds_syllabus.json` are unchanged
and hash-bound. Proposed links to official scope are stored in
`configs/mds_full_curriculum.json`; these are broad scope mappings awaiting faculty
review, not proof that every detail in a photograph equals an official heading.

## Official scope and provenance

The [current dental publisher gazette listing](https://dciindia.gov.in/GazetteList.aspx)
lists the 2017 MDS regulations and first/second 2018 and third 2019 amendments.
The third amendment adds Regulation 24(x), Schedule IX detailed specialty syllabi.
The Oral and Maxillofacial Pathology and Oral Microbiology English section is on
PDF/printed pages 194–200 of that 224-page amendment, and pages 110–117 of the
[2017 regulations](https://dciindia.gov.in/Rule_Regulation/MDS_Course_Regulations_2017.pdf).
Pages 108–109 of the latter concern orthodontics. The 2018 amendments inspected
change admission eligibility provisions. General pharmacology, particularly
drug-induced oral mucosal lesions, is explicitly included by the examination scope.
Both specialty outlines are preserved; the register uses the later detailed syllabus.

The [current NMC regulations listing](https://nmc.org.in/page/rules-regulations-rules-regulations-nmc)
points to the same September 2024 CBME and October clarification PDFs already
pinned by this project. Both were downloaded again on 2026-10-09 and their SHA-256
hashes exactly match the pinned snapshots. The listing also contains a 2026 UGMSR
amendment. This inspection is not an exhaustive legal-currency or university-specific
curriculum review. The [official AETCOM booklet](https://oldnmc.nmc.org.in/wp-content/uploads/2020/01/AETCOM_book.pdf)
was retrieved and pinned; its Appendix 1 is on PDF pages 87–91, printed pages 78–82.
The 2024 CBME text directs longitudinal use of the earlier MCI AETCOM module.

Downloaded official sources, listing snapshots and page extractions are under
`data/references/mds/raw/curriculum-audit/`. All official documents used by the CLI
are hash checked, as are the existing MBBS table extraction, competency register and
original photographs register. Copyright protected curriculum text is used only for
this local assessment register; no open license is asserted and nothing was imported
into the medical answer library. Do not redistribute complete syllabus text as course
content without obtaining the necessary rights.

## Unresolved scope and assessment issues

The official statistical bullet says “indicative statistics”; the photograph's
handwritten term is uncertain. Both observations remain explicit. Broad headings
such as oral microbiology, recent molecular techniques and developmental disorders
do not enumerate every possible disease or technique. Current concepts require dated
independent references. Historical bleeding/clotting-time examination requirements
are not endorsed as current diagnostic practice.

The MBBS detailed pediatric tables contain 253 numeric competencies (PE1–PE32)
while the published summary reports 406 competencies and 35 topics. This remains
unresolved. Other summary/table discrepancies remain in `curriculum-audit-report.json`.
The General Surgery table omits SU26.2; no text is invented for it. Malformed entries
14.1, MI 8., OR2. 2.9 and ASS.4 have their actual scope included as separate unresolved
records. GM11.5 has a blank original domain cell; no observed skill is inferred from it.
Code matching, count matching or keyword presence cannot prove completeness.

The register covers the pinned subject competencies and programme objectives. Local
elective choices, university additions, all future amendments and CRMI internship
performance require further institutional assessment. Written AI output cannot prove
laboratory skill, observed communication, patient examination, research execution or
clinical mastery.

## CLI

From the repository root in PowerShell:

```powershell
.venv/Scripts/python.exe scripts/curriculum_audit.py inventory --output artifacts/evaluation/comprehensive-v1/curriculum-inventory.json
.venv/Scripts/python.exe scripts/curriculum_audit.py blueprint --output artifacts/evaluation/comprehensive-v1/curriculum-blueprint.json
```

Both commands accept `--programme MDS`, `--programme MBBS`, or `--programme all`.
The default is `all`. The blueprint has a `cases` list with `case_id`, `question`,
scope `expected_facets`, official source page/section, programme, subject, variant
and blank correctness fields. Every active item has explain/apply/critique prompts.
`expected_facets` are scope descriptors, not factual correctness tests.

Evaluated answers must be a JSON list or `{ "cases": [...] }`, with each row holding
the exact `case_id` and textual `answer` or `response`. If supplied, `question` must
exactly match the blueprint. Missing, duplicate and unknown answer identities fail.
Textual answers remain unchanged; metadata such as model identity, release labels,
prior accuracy values and patient names in separate fields is not copied.
Only synthetic evaluations may be packed. The operator must ensure answer text
contains no actual patient information. A row marked `contains_real_patient_data`
is rejected; metadata filtering cannot de-identify patient information embedded in text.

```powershell
.venv/Scripts/python.exe scripts/curriculum_audit.py faculty-pack --blueprint artifacts/evaluation/comprehensive-v1/curriculum-blueprint.json --answers PATH_TO_EVALUATED_ANSWERS.json --output-dir artifacts/evaluation/comprehensive-v1/curriculum-faculty-pack
```

Create a new output directory for each pack. Share only `blinded-cases.json`,
`scores-blank.csv` and `rubric.md` with the reviewer. Keep `private-case-key.json`
and the provenance manifest with the evaluation owner. Presentation is randomized
and each answer is hash-bound. Blank scoring fields are pending, never zero.

The CSV requests real reviewer name, qualification, institution, registration/faculty
record, credential evidence, review date, independent reference source/locator,
answer hash, rationale and personal attestation. The rubric defines four ordinal
0–4 dimensions: accuracy, coverage, independent reference agreement and safety.
The reviewer must personally assess the answers; neither a model nor a developer
may impersonate qualified faculty.

```powershell
.venv/Scripts/python.exe scripts/curriculum_audit.py import-scores --pack artifacts/evaluation/comprehensive-v1/curriculum-faculty-pack --scores PATH_TO_HUMAN_COMPLETED_SCORES.csv --output artifacts/evaluation/comprehensive-v1/curriculum-human-attested-scores.json
```

Import only completed rows: pending/blank rows, invalid/nonfinite scores, duplicate
reviews, altered answers, unknown identities, model-origin assessments, explicit
self-claimed/simulated identities and absent personal attestations are rejected.
An incomplete pack may be imported using a CSV containing only the personally
completed rows; remaining cases stay unreviewed and the denominator is explicit.
Pack and CSV hashes bind the imported result. A CSV cannot establish credential
authenticity. The importer reports descriptive human-attested means while leaving
`qualified_human_accuracy` null and `credential_verification` pending external
verification. No clinical-reliability percentage is inferred from ordinal scores.

## Software verification

Eight meaningful curriculum workflow tests passed after their failures were
observed before implementation. Tests cover active/deleted scope, practical limits,
pending scores, blinding, duplicate and unknown answer identities, human attestation,
answer tampering, invalid scores, original photograph integrity and null spacer
columns in extracted MBBS tables. A full project run at this point reported
331 passed and one failure in the concurrently developed foundation source filter:
`tests/test_audit_foundations.py::test_blood_group_source_errors_excluded_as_complete_paragraphs`.
The integration owner must rerun the complete suite after that work is finished.
