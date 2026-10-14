# Aster curriculum and answer-quality audit

User intent: thoroughly evaluate and improve the medical AI across the photographed
topics and full Oral Pathology/Oral Microbiology curriculum. The user confirmed
full MBBS and full MDS scope and requested a review pack because no faculty
reviewer is available. The user's request authorizes fixes, local research imports,
evaluation and reversible activation. Human faculty review is a separate external
dependency; no developer or model may be represented as qualified faculty.

## Outcomes

- Verify the official curriculum inventory and keep every theory/practical/research
  requirement visible. Practical performance cannot be scored by text answers.
- Test every photographed topic with multiple meaningful question types, plus the
  official curriculum extensions. Separate response handling, content coverage,
  reference agreement, source integrity and qualified human accuracy.
- Diagnose retrieval failures without loosening source quality, personal-treatment
  boundaries or promoting statistical/experimental papers to clinical guidelines.
- Import independently licensed foundation material for genuine content gaps.
- Preserve immutable release and evaluation history, original MBBS records and
  review holds. Publish a new release only after regression and application checks.
- Generate a blinded faculty review pack, blank scoring sheets, explicit reviewer
  credentials/attestation and a score importer that cannot count pending blanks.
- Report incomplete items candidly; finite automated testing cannot prove all
  possible gaps closed or a model clinically dependable.

## Design

Retain the separate TeachingStore and primary/secondary medicine paths. Prefer
source-specific matching and anchored multi-topic decomposition over lower global
thresholds. Record source-backed partial answers and the subtopics unsupported.
Every additional source retains rights evidence, date/version, jurisdiction and
research context. Source or explanation changes require pinned hashes.

The curriculum inventory, content acquisition and independent source-quality audit
are independent tasks suitable for parallel agents under the dispatching skill.
Root owns runtime fixes, integration, evaluation, activation and final reporting.

## Verification

Meaningful failing tests precede runtime fixes. Fresh benchmarks bind release,
index, notes, question set and code hashes. All-topic probes measure handling only;
fact/coverage rubrics require independently inspected reference evidence. Clinical
accuracy remains null until a qualified reviewer supplies completed assessments.
Existing medicine/OCR/X-ray limitations remain explicit and are evaluated using
available labelled assets, without fabricated clinical or handwriting scores.
