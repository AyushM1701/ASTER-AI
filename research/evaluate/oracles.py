"""Four-arm fault localization using supplied, separately authored labels.

Candidate injection never replaces applicability checks or the terminal guard.
Not mounted in the public API. Caller-supplied provenance is not credential
verification and does not constitute independent medical evaluation.
"""

import copy

from backend.app.services.question_plan import QuestionPlan


class CandidateOracle:
    def __init__(self, teacher, known_rows):
        self.teacher, self.known_rows = teacher, known_rows

    def __getattr__(self, name):
        return getattr(self.teacher, name)

    def search(self, query, limit=8):
        rows = [*self.known_rows, *self.teacher.search(query, limit=limit)]
        unique = {row.chunk_id: row for row in reversed(rows)}
        return [unique[identity] for identity in dict.fromkeys(row.chunk_id for row in rows)][:limit]


def run_case(service, question, labels):
    if (labels.get("independent") is not True or not labels.get("author")
            or labels.get("label_origin") not in {"independent_author", "synthetic_mechanics"}):
        raise ValueError("independent labelled example and explicit provenance required")
    plan = QuestionPlan.model_validate(labels["question_plan"])
    if plan.original_question != question:
        raise ValueError("oracle plan must preserve the original question")
    rows = []
    for identity, digest in labels.get("passage_hashes", {}).items():
        row = service.teaching.references.id_records.get(identity)
        if row is None or row.content_hash() != digest:
            raise ValueError("oracle evidence must resolve to exact admitted source identities")
        rows.append(row)
    arms = {}
    for name, corrected_plan, candidate_oracle in (
        ("baseline", False, False), ("oracle_plan", True, False),
        ("oracle_evidence", False, True), ("both", True, True),
    ):
        experiment = copy.copy(service)
        if candidate_oracle:
            experiment.teaching = CandidateOracle(service.teaching, rows)
        arms[name] = experiment.answer(question, audience="study",
                                      question_plan=plan if corrected_plan else None)
    return {"arms": arms, "label_origin": labels["label_origin"],
            "independence_verified": False, "label_provenance": "supplied; externally unverified",
            "clinical_accuracy": None, "qualified_review": "pending",
            "interpretation": "Candidate/plan substitution only; all source/support/final guard checks preserved."}
