# Aster: simple explanation followed by deeper explanation

Implemented 10 October 2026. Informational chat answers now display two open
sections, **Simple explanation** followed by **Deeper explanation**. Detailed
citations remain in the desktop evidence panel or phone sources drawer.

## What changed

- 43 existing teaching explanations have checked presentation boundaries. Their
  original facts, source bindings and qualifications are preserved. These are
  developer checks; faculty review remains pending.
- Epithelium starts with the covering-and-lining definition, followed by function,
  basement membrane, cell shape and number of layers. Sulcular epithelium keeps
  the distinction between lining the sulcus and attaching to the tooth.
- Research context remains visible before the affected explanation. Original
  complete claims, warnings and citations are retained in exported JSON.
- General conversational generation has separate introduction and deeper-detail
  fields. Both fields receive the existing output policy checks.
- Explicit general questions are routed before medical retrieval. This fixes an
  observed error where “Explain programming” matched immune-cell programming.
- Urgent guidance and confirmation/unsupported/error states stay direct.

## Coverage limits

The format applies automatically to informational answers, but the library does
not yet contain checked plain-language and deeper explanations for every topic.
Raw technical notes are never truncated to manufacture a simpler medical claim.
Missing checked introductions or additional detail receive an explicit notice.
This change does not certify medical correctness, establish curriculum mastery,
or train new model weights.

## Verification

The final Python suite passed **466/466** tests, including 57 presentation and
policy checks. JavaScript syntax validation passed. The first live run passed
**136/136** checks: 9 format/safety examples, 12 epithelium checks and 115 existing
regression cases. The routing correction has a regression test that fails if an
explicit programming question reaches medical teaching retrieval.

After the routing correction and final restart, all **137/137 live checks**
passed: the same 136 cases plus an actual `qwen3-vl:2b-instruct` programming
response with both explanation fields. The model's factual answer quality was
not graded by this format check. All synthetic API test sessions were deleted.

Desktop, normal viewport and phone DOM checks found no horizontal overflow.
The phone sources drawer was exercised through the actual browser interface.
Fresh independent Impeccable finish review passed with no material findings.
The viewport-only mobile capture had a browser scaling defect; the full-page
phone capture renders the complete reading width correctly.

Evidence: `artifacts/evaluation/layered-answers-v1`. Final live results and
delivery manifest are stored there. These are engineering checks; clinical
accuracy and faculty scores are unmeasured.
